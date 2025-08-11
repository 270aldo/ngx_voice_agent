"""
ML Model Updater - Manages model retraining and deployment.

Responsible for:
- Automated model retraining
- Version management
- Safe deployment
- Rollback capabilities
"""

import logging
import os
import shutil
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import joblib
import uuid

from src.services.training.ml_model_trainer import MLModelTrainer
from src.services.training.training_data_generator import TrainingDataGenerator
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

logger = logging.getLogger(__name__)


class MLModelUpdater:
    """
    Manages automated model updates and deployments.
    """
    
    def __init__(self, models_dir: str = "models"):
        """Initialize the model updater.
        
        Args:
            models_dir: Directory for model storage
        """
        self.models_dir = models_dir
        self.trainer = MLModelTrainer(models_dir)
        self.data_generator = TrainingDataGenerator()
        self.supabase = supabase_client
        
        # Update configuration
        self.update_config = {
            "min_training_samples": 1000,
            "validation_split": 0.2,
            "performance_threshold": 0.05,  # 5% improvement required
            "max_training_time_hours": 2,
            "backup_retention_days": 30
        }
        
        # Model version tracking
        self.current_versions = self._load_version_info()
        self.update_queue = []
        
        # Ensure directories exist
        os.makedirs(models_dir, exist_ok=True)
        os.makedirs(os.path.join(models_dir, "backups"), exist_ok=True)
    
    async def queue_update(
        self,
        model_type: str,
        reason: str,
        data: Optional[Any] = None,
        priority: str = "normal"
    ) -> str:
        """
        Queue a model update request.
        
        Args:
            model_type: Type of model to update (objection, needs, conversion, all)
            reason: Reason for update
            data: Optional training data or improvement suggestions
            priority: Update priority (low, normal, high)
            
        Returns:
            Update request ID
        """
        try:
            update_id = str(uuid.uuid4())
            
            update_request = {
                "id": update_id,
                "model_type": model_type,
                "reason": reason,
                "data": data,
                "priority": priority,
                "status": "queued",
                "created_at": datetime.now().isoformat()
            }
            
            # Add to queue based on priority
            if priority == "high":
                self.update_queue.insert(0, update_request)
            else:
                self.update_queue.append(update_request)
            
            # Store in database
            await self._store_update_request(update_request)
            
            logger.info(f"Queued model update {update_id} for {model_type} (reason: {reason})")
            
            return update_id
            
        except Exception as e:
            logger.error(f"Error queuing update: {e}")
            return ""
    
    async def process_update_queue(
        self,
        max_updates: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Process queued model updates.
        
        Args:
            max_updates: Maximum number of updates to process
            
        Returns:
            List of update results
        """
        results = []
        
        while self.update_queue and len(results) < max_updates:
            update_request = self.update_queue.pop(0)
            
            try:
                # Update status
                update_request["status"] = "processing"
                update_request["started_at"] = datetime.now().isoformat()
                
                # Process update
                if update_request["model_type"] == "all":
                    result = await self.update_all_models(
                        training_data=update_request.get("data")
                    )
                else:
                    result = await self.update_model(
                        model_type=update_request["model_type"],
                        training_data=update_request.get("data")
                    )
                
                # Update request status
                update_request["status"] = "completed" if result["success"] else "failed"
                update_request["completed_at"] = datetime.now().isoformat()
                update_request["result"] = result
                
                results.append(update_request)
                
                # Store result
                await self._store_update_result(update_request)
                
            except Exception as e:
                logger.error(f"Error processing update {update_request['id']}: {e}")
                update_request["status"] = "failed"
                update_request["error"] = str(e)
                results.append(update_request)
        
        return results
    
    async def update_model(
        self,
        model_type: str,
        training_data: Optional[Any] = None,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Update a specific model.
        
        Args:
            model_type: Type of model (objection, needs, conversion)
            training_data: Training data (will fetch if not provided)
            validation_split: Validation data split
            
        Returns:
            Update results
        """
        try:
            logger.info(f"Starting update for {model_type} model")
            
            # Backup current model
            backup_path = await self._backup_model(model_type)
            
            # Get training data if not provided
            if training_data is None:
                training_data = await self._fetch_training_data(model_type)
            
            # Check if we have enough data
            sample_count = len(training_data) if isinstance(training_data, list) else \
                          training_data.shape[0] if hasattr(training_data, 'shape') else 0
            
            if sample_count < self.update_config["min_training_samples"]:
                logger.warning(f"Insufficient training data: {sample_count} < {self.update_config['min_training_samples']}")
                return {
                    "success": False,
                    "error": "Insufficient training data",
                    "sample_count": sample_count
                }
            
            # Train new model
            train_result = await self._train_new_model(
                model_type=model_type,
                training_data=training_data,
                validation_split=validation_split
            )
            
            if not train_result["success"]:
                logger.error(f"Training failed: {train_result.get('error')}")
                return train_result
            
            # Evaluate new model
            evaluation = await self._evaluate_model(
                model_type=model_type,
                new_metrics=train_result["metrics"],
                backup_path=backup_path
            )
            
            # Deploy or rollback based on evaluation
            if evaluation["should_deploy"]:
                deploy_result = await self._deploy_model(
                    model_type=model_type,
                    new_version=train_result["version"]
                )
                
                if deploy_result["success"]:
                    logger.info(f"Successfully deployed {model_type} model v{train_result['version']}")
                    return {
                        "success": True,
                        "model_type": model_type,
                        "version": train_result["version"],
                        "metrics": train_result["metrics"],
                        "improvement": evaluation["improvement"],
                        "deployed_at": deploy_result["deployed_at"]
                    }
                else:
                    # Rollback on deployment failure
                    await self._rollback_model(model_type, backup_path)
                    return {
                        "success": False,
                        "error": "Deployment failed, rolled back",
                        "details": deploy_result
                    }
            else:
                # New model didn't meet improvement threshold
                logger.info(f"New model didn't meet improvement threshold, keeping current version")
                await self._cleanup_failed_update(model_type, train_result["version"])
                return {
                    "success": False,
                    "reason": "insufficient_improvement",
                    "current_metrics": evaluation["current_metrics"],
                    "new_metrics": train_result["metrics"],
                    "improvement": evaluation["improvement"]
                }
            
        except Exception as e:
            logger.error(f"Error updating model: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_all_models(
        self,
        training_data: Optional[Dict[str, Any]] = None,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Update all models.
        
        Args:
            training_data: Training data for all models
            validation_split: Validation split
            
        Returns:
            Update results for all models
        """
        results = {}
        
        for model_type in ["objection", "needs", "conversion"]:
            model_data = training_data.get(model_type) if training_data else None
            result = await self.update_model(
                model_type=model_type,
                training_data=model_data,
                validation_split=validation_split
            )
            results[model_type] = result
        
        # Summary
        successful_updates = sum(1 for r in results.values() if r.get("success", False))
        
        return {
            "success": successful_updates > 0,
            "models_updated": successful_updates,
            "total_models": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_update_metrics(self) -> Dict[str, Any]:
        """
        Get model update metrics.
        
        Returns:
            Update metrics and history
        """
        try:
            # Get recent updates
            since = datetime.now() - timedelta(days=30)
            
            response = await self.supabase.table("ml_experiments").select(
                "*"
            ).eq(
                "experiment_type", "model_update"
            ).gte(
                "created_at", since.isoformat()
            ).execute()
            
            updates = response.data or []
            
            # Calculate metrics
            total_updates = len(updates)
            successful_updates = sum(1 for u in updates if u.get("status") == "completed")
            
            # Get average improvement
            improvements = []
            for update in updates:
                if update.get("results") and "improvement" in update["results"]:
                    improvements.append(update["results"]["improvement"])
            
            avg_improvement = sum(improvements) / len(improvements) if improvements else 0
            
            # Model-specific metrics
            model_metrics = {}
            for model_type in ["objection", "needs", "conversion"]:
                model_updates = [u for u in updates if u.get("config", {}).get("model_type") == model_type]
                model_metrics[model_type] = {
                    "total_updates": len(model_updates),
                    "last_update": max((u["created_at"] for u in model_updates), default=None),
                    "current_version": self.current_versions.get(model_type, {}).get("version", "unknown")
                }
            
            return {
                "total_updates": total_updates,
                "successful_updates": successful_updates,
                "success_rate": successful_updates / total_updates if total_updates > 0 else 0,
                "average_improvement": avg_improvement,
                "model_metrics": model_metrics,
                "queue_size": len(self.update_queue),
                "last_update": max((u["created_at"] for u in updates), default=None)
            }
            
        except Exception as e:
            logger.error(f"Error getting update metrics: {e}")
            return {"error": str(e)}
    
    async def rollback_model(
        self,
        model_type: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rollback a model to a previous version.
        
        Args:
            model_type: Type of model
            version: Specific version to rollback to (latest backup if not specified)
            
        Returns:
            Rollback results
        """
        try:
            # Find backup
            backup_dir = os.path.join(self.models_dir, "backups", model_type)
            if not os.path.exists(backup_dir):
                return {"success": False, "error": "No backups found"}
            
            if version:
                backup_path = os.path.join(backup_dir, f"v{version}")
            else:
                # Get latest backup
                backups = sorted(os.listdir(backup_dir), reverse=True)
                if not backups:
                    return {"success": False, "error": "No backups found"}
                backup_path = os.path.join(backup_dir, backups[0])
            
            if not os.path.exists(backup_path):
                return {"success": False, "error": f"Backup version {version} not found"}
            
            # Perform rollback
            result = await self._rollback_model(model_type, backup_path)
            
            if result["success"]:
                # Update version info
                backup_version = os.path.basename(backup_path).replace("v", "")
                self.current_versions[model_type] = {
                    "version": backup_version,
                    "deployed_at": datetime.now().isoformat(),
                    "rollback": True
                }
                self._save_version_info()
                
                # Log rollback
                await self._log_rollback(model_type, backup_version)
            
            return result
            
        except Exception as e:
            logger.error(f"Error rolling back model: {e}")
            return {"success": False, "error": str(e)}
    
    # Private helper methods
    
    async def _backup_model(
        self,
        model_type: str
    ) -> str:
        """
        Backup current model.
        
        Args:
            model_type: Type of model
            
        Returns:
            Backup path
        """
        try:
            current_model_path = os.path.join(self.models_dir, f"{model_type}_model.pkl")
            if not os.path.exists(current_model_path):
                logger.warning(f"No current model to backup for {model_type}")
                return ""
            
            # Create backup directory
            backup_dir = os.path.join(self.models_dir, "backups", model_type)
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup version
            current_version = self.current_versions.get(model_type, {}).get("version", "0")
            backup_version = f"v{current_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(backup_dir, backup_version)
            
            # Copy model and metadata
            os.makedirs(backup_path, exist_ok=True)
            shutil.copy2(current_model_path, os.path.join(backup_path, f"{model_type}_model.pkl"))
            
            # Copy metadata if exists
            metadata_path = os.path.join(self.models_dir, f"{model_type}_metadata.json")
            if os.path.exists(metadata_path):
                shutil.copy2(metadata_path, os.path.join(backup_path, f"{model_type}_metadata.json"))
            
            logger.info(f"Backed up {model_type} model to {backup_path}")
            
            # Clean old backups
            await self._cleanup_old_backups(model_type)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Error backing up model: {e}")
            return ""
    
    async def _fetch_training_data(
        self,
        model_type: str
    ) -> Any:
        """
        Fetch training data for model update.
        
        Args:
            model_type: Type of model
            
        Returns:
            Training data
        """
        try:
            # Get recent conversation data from database
            since = datetime.now() - timedelta(days=30)
            
            response = await self.supabase.table("conversation_outcomes").select(
                "*"
            ).gte(
                "created_at", since.isoformat()
            ).execute()
            
            conversations = response.data or []
            
            # Process based on model type
            if model_type == "objection":
                return self._prepare_objection_training_data(conversations)
            elif model_type == "needs":
                return self._prepare_needs_training_data(conversations)
            elif model_type == "conversion":
                return self._prepare_conversion_training_data(conversations)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
        except Exception as e:
            logger.error(f"Error fetching training data: {e}")
            # Fallback to synthetic data
            return self.data_generator.generate_training_data(model_type, samples=1000)
    
    async def _train_new_model(
        self,
        model_type: str,
        training_data: Any,
        validation_split: float
    ) -> Dict[str, Any]:
        """
        Train a new model version.
        
        Args:
            model_type: Type of model
            training_data: Training data
            validation_split: Validation split
            
        Returns:
            Training results
        """
        try:
            # Generate new version number
            current_version = int(self.current_versions.get(model_type, {}).get("version", "0"))
            new_version = str(current_version + 1)
            
            # Train model
            if model_type == "objection":
                result = self.trainer.train_objection_model(training_data)
            elif model_type == "needs":
                result = self.trainer.train_needs_model(training_data)
            elif model_type == "conversion":
                result = self.trainer.train_conversion_model(training_data)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            if result["success"]:
                result["version"] = new_version
                result["metrics"] = {
                    "accuracy": result.get("accuracy", 0),
                    "precision": result.get("precision", 0),
                    "recall": result.get("recall", 0),
                    "f1_score": result.get("f1_score", 0)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return {"success": False, "error": str(e)}
    
    async def _evaluate_model(
        self,
        model_type: str,
        new_metrics: Dict[str, float],
        backup_path: str
    ) -> Dict[str, Any]:
        """
        Evaluate if new model should be deployed.
        
        Args:
            model_type: Type of model
            new_metrics: New model metrics
            backup_path: Path to backup for comparison
            
        Returns:
            Evaluation results
        """
        try:
            # Get current model metrics
            current_metrics = self.current_versions.get(model_type, {}).get("metrics", {})
            
            if not current_metrics:
                # No current metrics, deploy new model
                return {
                    "should_deploy": True,
                    "improvement": 1.0,
                    "current_metrics": {},
                    "new_metrics": new_metrics
                }
            
            # Calculate improvement
            current_score = current_metrics.get("f1_score", current_metrics.get("accuracy", 0))
            new_score = new_metrics.get("f1_score", new_metrics.get("accuracy", 0))
            
            improvement = (new_score - current_score) / current_score if current_score > 0 else 1.0
            
            # Check if improvement meets threshold
            should_deploy = improvement >= self.update_config["performance_threshold"]
            
            return {
                "should_deploy": should_deploy,
                "improvement": improvement,
                "current_metrics": current_metrics,
                "new_metrics": new_metrics,
                "threshold": self.update_config["performance_threshold"]
            }
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {
                "should_deploy": False,
                "error": str(e)
            }
    
    async def _deploy_model(
        self,
        model_type: str,
        new_version: str
    ) -> Dict[str, Any]:
        """
        Deploy new model version.
        
        Args:
            model_type: Type of model
            new_version: New version number
            
        Returns:
            Deployment results
        """
        try:
            # Update version info
            self.current_versions[model_type] = {
                "version": new_version,
                "deployed_at": datetime.now().isoformat(),
                "metrics": self.trainer.get_model_metrics(model_type)
            }
            
            # Save version info
            self._save_version_info()
            
            # Reload model in trainer
            self.trainer.load_model(model_type)
            
            # Log deployment
            await self._log_deployment(model_type, new_version)
            
            return {
                "success": True,
                "deployed_at": self.current_versions[model_type]["deployed_at"]
            }
            
        except Exception as e:
            logger.error(f"Error deploying model: {e}")
            return {"success": False, "error": str(e)}
    
    async def _rollback_model(
        self,
        model_type: str,
        backup_path: str
    ) -> Dict[str, Any]:
        """
        Rollback to backup model.
        
        Args:
            model_type: Type of model
            backup_path: Path to backup
            
        Returns:
            Rollback results
        """
        try:
            # Copy backup to active location
            model_file = os.path.join(backup_path, f"{model_type}_model.pkl")
            target_path = os.path.join(self.models_dir, f"{model_type}_model.pkl")
            
            if os.path.exists(model_file):
                shutil.copy2(model_file, target_path)
            else:
                return {"success": False, "error": "Backup model file not found"}
            
            # Copy metadata if exists
            metadata_file = os.path.join(backup_path, f"{model_type}_metadata.json")
            if os.path.exists(metadata_file):
                target_metadata = os.path.join(self.models_dir, f"{model_type}_metadata.json")
                shutil.copy2(metadata_file, target_metadata)
            
            # Reload model
            self.trainer.load_model(model_type)
            
            logger.info(f"Rolled back {model_type} model from {backup_path}")
            
            return {"success": True, "backup_path": backup_path}
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return {"success": False, "error": str(e)}
    
    def _load_version_info(self) -> Dict[str, Any]:
        """Load version information from file."""
        version_file = os.path.join(self.models_dir, "model_versions.json")
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_version_info(self) -> None:
        """Save version information to file."""
        version_file = os.path.join(self.models_dir, "model_versions.json")
        with open(version_file, 'w') as f:
            json.dump(self.current_versions, f, indent=2)
    
    async def _store_update_request(
        self,
        update_request: Dict[str, Any]
    ) -> None:
        """Store update request in database."""
        try:
            await self.supabase.table("ml_experiments").insert({
                "id": update_request["id"],
                "name": f"model_update_{update_request['model_type']}",
                "experiment_type": "model_update",
                "status": update_request["status"],
                "config": {
                    "model_type": update_request["model_type"],
                    "reason": update_request["reason"],
                    "priority": update_request["priority"]
                },
                "created_at": update_request["created_at"]
            }).execute()
        except Exception as e:
            logger.error(f"Error storing update request: {e}")
    
    async def _store_update_result(
        self,
        update_result: Dict[str, Any]
    ) -> None:
        """Store update result in database."""
        try:
            await self.supabase.table("ml_experiments").update({
                "status": update_result["status"],
                "results": update_result.get("result", {}),
                "completed_at": update_result.get("completed_at")
            }).eq(
                "id", update_result["id"]
            ).execute()
        except Exception as e:
            logger.error(f"Error storing update result: {e}")
    
    async def _cleanup_old_backups(
        self,
        model_type: str
    ) -> None:
        """Clean up old backup files."""
        try:
            backup_dir = os.path.join(self.models_dir, "backups", model_type)
            if not os.path.exists(backup_dir):
                return
            
            retention_days = self.update_config["backup_retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for backup in os.listdir(backup_dir):
                backup_path = os.path.join(backup_dir, backup)
                if os.path.isdir(backup_path):
                    # Check modification time
                    mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
                    if mtime < cutoff_date:
                        shutil.rmtree(backup_path)
                        logger.info(f"Removed old backup: {backup_path}")
        except Exception as e:
            logger.error(f"Error cleaning backups: {e}")
    
    async def _cleanup_failed_update(
        self,
        model_type: str,
        version: str
    ) -> None:
        """Clean up after failed update."""
        # Implementation depends on specific cleanup needs
        pass
    
    def _prepare_objection_training_data(
        self,
        conversations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare objection training data from conversations."""
        training_data = []
        
        for conv in conversations:
            if conv.get("objections_encountered"):
                messages = json.loads(conv.get("messages", "[]"))
                for objection in conv["objections_encountered"]:
                    training_data.append({
                        "messages": messages,
                        "objection_type": objection["type"],
                        "handled_successfully": objection.get("resolved", False)
                    })
        
        return training_data
    
    def _prepare_needs_training_data(
        self,
        conversations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare needs training data from conversations."""
        training_data = []
        
        for conv in conversations:
            if conv.get("needs_identified"):
                messages = json.loads(conv.get("messages", "[]"))
                for need in conv["needs_identified"]:
                    training_data.append({
                        "messages": messages,
                        "need_type": need["type"],
                        "priority": need.get("priority", "medium")
                    })
        
        return training_data
    
    def _prepare_conversion_training_data(
        self,
        conversations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare conversion training data from conversations."""
        training_data = []
        
        for conv in conversations:
            messages = json.loads(conv.get("messages", "[]"))
            outcome = conv.get("outcome", "abandoned")
            
            training_data.append({
                "messages": messages,
                "converted": outcome in ["completed", "qualified"],
                "outcome": outcome,
                "duration_seconds": conv.get("duration_seconds", 0),
                "message_count": len(messages)
            })
        
        return training_data
    
    async def _log_deployment(
        self,
        model_type: str,
        version: str
    ) -> None:
        """Log model deployment."""
        try:
            await self.supabase.table("ml_tracking_events").insert({
                "event_type": "model_deployed",
                "event_category": "deployment",
                "data": json.dumps({
                    "model_type": model_type,
                    "version": version,
                    "metrics": self.current_versions[model_type].get("metrics", {})
                }),
                "created_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error logging deployment: {e}")
    
    async def _log_rollback(
        self,
        model_type: str,
        version: str
    ) -> None:
        """Log model rollback."""
        try:
            await self.supabase.table("ml_tracking_events").insert({
                "event_type": "model_rollback",
                "event_category": "deployment",
                "data": json.dumps({
                    "model_type": model_type,
                    "rollback_to_version": version
                }),
                "created_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error logging rollback: {e}")

import uuid