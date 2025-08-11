"""
Initialize Models Script for NGX Voice Sales Agent.

This script initializes the predictive models with training data
to ensure they can make predictions immediately.
"""

import asyncio
import logging
from typing import Dict, Any

from src.services.training.training_data_generator import TrainingDataGenerator
from src.services.predictive_model_service import PredictiveModelService
from src.integrations.supabase.resilient_client import get_resilient_client

logger = logging.getLogger(__name__)

class ModelInitializer:
    """
    Initializes predictive models with training data.
    """
    
    def __init__(self):
        """Initialize the model initializer."""
        self.supabase = get_resilient_client()
        self.predictive_service = PredictiveModelService(self.supabase)
        self.data_generator = TrainingDataGenerator()
        
    async def initialize_all_models(self) -> Dict[str, Any]:
        """
        Initialize all predictive models with training data.
        
        Returns:
            Summary of initialization results
        """
        logger.info("Starting model initialization...")
        
        results = {
            "objection_model": False,
            "needs_model": False,
            "conversion_model": False,
            "training_samples_added": 0
        }
        
        try:
            # Generate training dataset
            logger.info("Generating training dataset...")
            dataset = self.data_generator.generate_complete_training_dataset()
            
            # Initialize objection prediction model
            logger.info("Initializing objection prediction model...")
            objection_result = await self._initialize_objection_model(dataset["objection"])
            results["objection_model"] = objection_result["success"]
            results["training_samples_added"] += objection_result["samples_added"]
            
            # Initialize needs prediction model
            logger.info("Initializing needs prediction model...")
            needs_result = await self._initialize_needs_model(dataset["needs"])
            results["needs_model"] = needs_result["success"]
            results["training_samples_added"] += needs_result["samples_added"]
            
            # Initialize conversion prediction model
            logger.info("Initializing conversion prediction model...")
            conversion_result = await self._initialize_conversion_model(dataset["conversion"])
            results["conversion_model"] = conversion_result["success"]
            results["training_samples_added"] += conversion_result["samples_added"]
            
            logger.info(f"Model initialization complete. Total samples added: {results['training_samples_added']}")
            
        except Exception as e:
            logger.error(f"Error during model initialization: {e}")
            results["error"] = str(e)
            
        return results
        
    async def _initialize_objection_model(self, training_data: list) -> Dict[str, Any]:
        """Initialize objection prediction model with training data."""
        try:
            model_name = "objection_prediction_model"
            samples_added = 0
            
            # Check if model exists
            model = await self.predictive_service.get_model(model_name)
            
            if not model:
                # Register the model
                model_params = {
                    "objection_types": [
                        "price", "value", "need", "urgency", "authority", 
                        "trust", "competition", "features", "implementation", 
                        "support", "compatibility"
                    ],
                    "confidence_threshold": 0.65,
                    "context_window": 5,
                    "signal_weights": {
                        "sentiment_negative": 0.3,
                        "hesitation_words": 0.2,
                        "comparison_phrases": 0.25,
                        "price_mentions": 0.4,
                        "uncertainty_phrases": 0.3
                    }
                }
                
                await self.predictive_service.register_model(
                    model_name=model_name,
                    model_type="objection",
                    model_params=model_params,
                    description="Model for predicting customer objections"
                )
                
            # Add training data
            for sample in training_data:
                await self.predictive_service.add_training_data(
                    model_name=model_name,
                    data_type="objection",
                    features=sample["features"],
                    label=sample["label"]
                )
                samples_added += 1
                
            return {"success": True, "samples_added": samples_added}
            
        except Exception as e:
            logger.error(f"Error initializing objection model: {e}")
            return {"success": False, "samples_added": 0, "error": str(e)}
            
    async def _initialize_needs_model(self, training_data: list) -> Dict[str, Any]:
        """Initialize needs prediction model with training data."""
        try:
            model_name = "needs_prediction_model"
            samples_added = 0
            
            # Check if model exists
            model = await self.predictive_service.get_model(model_name)
            
            if not model:
                # Register the model
                model_params = {
                    "need_categories": [
                        "information", "pricing", "features", "support",
                        "customization", "integration", "training", "comparison",
                        "technical_details", "case_studies", "alternatives"
                    ],
                    "confidence_threshold": 0.6,
                    "context_window": 10,
                    "feature_weights": {
                        "explicit_requests": 0.5,
                        "implicit_interests": 0.3,
                        "question_patterns": 0.4,
                        "entity_mentions": 0.35,
                        "similar_profiles": 0.25
                    }
                }
                
                await self.predictive_service.register_model(
                    model_name=model_name,
                    model_type="needs",
                    model_params=model_params,
                    description="Model for predicting customer needs"
                )
                
            # Add training data
            for sample in training_data:
                await self.predictive_service.add_training_data(
                    model_name=model_name,
                    data_type="needs",
                    features=sample["features"],
                    label=sample["label"]
                )
                samples_added += 1
                
            return {"success": True, "samples_added": samples_added}
            
        except Exception as e:
            logger.error(f"Error initializing needs model: {e}")
            return {"success": False, "samples_added": 0, "error": str(e)}
            
    async def _initialize_conversion_model(self, training_data: list) -> Dict[str, Any]:
        """Initialize conversion prediction model with training data."""
        try:
            model_name = "conversion_prediction_model"
            samples_added = 0
            
            # Check if model exists
            model = await self.predictive_service.get_model(model_name)
            
            if not model:
                # Register the model
                model_params = {
                    "conversion_thresholds": {
                        "low": 0.3,
                        "medium": 0.6,
                        "high": 0.8
                    },
                    "confidence_threshold": 0.65,
                    "context_window": 10,
                    "signal_weights": {
                        "buying_signals": 0.4,
                        "engagement_level": 0.3,
                        "question_frequency": 0.2,
                        "positive_sentiment": 0.25,
                        "specific_inquiries": 0.35,
                        "time_investment": 0.15
                    }
                }
                
                await self.predictive_service.register_model(
                    model_name=model_name,
                    model_type="conversion",
                    model_params=model_params,
                    description="Model for predicting conversion probability"
                )
                
            # Add training data
            for sample in training_data:
                await self.predictive_service.add_training_data(
                    model_name=model_name,
                    data_type="conversion",
                    features=sample["features"],
                    label=sample["label"]
                )
                samples_added += 1
                
            return {"success": True, "samples_added": samples_added}
            
        except Exception as e:
            logger.error(f"Error initializing conversion model: {e}")
            return {"success": False, "samples_added": 0, "error": str(e)}


async def main():
    """Main function to run model initialization."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize models
    initializer = ModelInitializer()
    results = await initializer.initialize_all_models()
    
    # Print results
    print("\n=== Model Initialization Results ===")
    print(f"Objection Model: {'✓' if results['objection_model'] else '✗'}")
    print(f"Needs Model: {'✓' if results['needs_model'] else '✗'}")
    print(f"Conversion Model: {'✓' if results['conversion_model'] else '✗'}")
    print(f"Total Training Samples Added: {results['training_samples_added']}")
    
    if "error" in results:
        print(f"\nError: {results['error']}")
    else:
        print("\nAll models initialized successfully!")


if __name__ == "__main__":
    asyncio.run(main())