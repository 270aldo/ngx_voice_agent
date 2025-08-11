"""
ML Tracking Mixin

Handles all ML-related tracking, experiments, and adaptive learning functionality.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from src.models.conversation import ConversationState
from src.services.conversation_outcome_tracker import ConversationOutcomeTracker
from src.services.adaptive_learning_service import AdaptiveLearningService
from src.services.ab_testing_framework import ABTestingFramework
from src.models.learning_models import AdaptiveLearningConfig

logger = logging.getLogger(__name__)


class MLTrackingMixin:
    """Mixin for ML tracking and adaptive learning functionality."""
    
    def __init__(self):
        """Initialize ML tracking components."""
        # These will be initialized by the main service
        self.outcome_tracker: Optional[ConversationOutcomeTracker] = None
        self.adaptive_learning_service: Optional[AdaptiveLearningService] = None
        self.ab_testing_framework: Optional[ABTestingFramework] = None
        self.active_experiments: Dict[str, Any] = {}
    
    def _init_ml_services(self):
        """Initialize ML services if not already initialized."""
        if not self.outcome_tracker:
            self.outcome_tracker = ConversationOutcomeTracker()
        if not self.adaptive_learning_service:
            self.adaptive_learning_service = AdaptiveLearningService(self.outcome_tracker)
        if not self.ab_testing_framework:
            self.ab_testing_framework = ABTestingFramework(AdaptiveLearningConfig())
    
    async def _start_ml_conversation_tracking(
        self,
        conversation_id: str,
        customer_data: Dict[str, Any],
        platform_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Iniciar el tracking ML para una nueva conversación.
        
        Args:
            conversation_id: ID de la conversación
            customer_data: Datos del cliente
            platform_context: Contexto de la plataforma
            
        Returns:
            Dict con configuración de tracking y experimentos asignados
        """
        self._init_ml_services()
        
        try:
            # Inicializar tracking de resultado
            await self.outcome_tracker.start_conversation(
                conversation_id=conversation_id,
                customer_data=customer_data,
                platform_source=platform_context.get('source', 'web') if platform_context else 'web'
            )
            
            # Obtener experimentos activos
            experiments = await self._get_active_experiments_for_conversation(
                conversation_id, customer_data
            )
            
            # Guardar experimentos activos para esta conversación
            self.active_experiments[conversation_id] = experiments
            
            logger.info(
                f"ML tracking iniciado para conversación {conversation_id} "
                f"con {len(experiments)} experimentos activos"
            )
            
            return {
                "ml_tracking_enabled": True,
                "experiments_assigned": experiments,
                "tracking_start_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error iniciando ML tracking: {e}")
            return {
                "ml_tracking_enabled": False,
                "experiments_assigned": [],
                "error": str(e)
            }
    
    async def _update_ml_conversation_metrics(
        self,
        conversation_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Actualizar métricas ML durante la conversación.
        
        Args:
            conversation_id: ID de la conversación
            metrics: Métricas a actualizar
        """
        self._init_ml_services()
        
        try:
            # Actualizar métricas en el tracker
            await self.outcome_tracker.update_metrics(
                conversation_id=conversation_id,
                **metrics
            )
            
            # Si hay experimentos activos, registrar eventos
            if conversation_id in self.active_experiments:
                for experiment_id in self.active_experiments[conversation_id]:
                    await self.ab_testing_framework.record_event(
                        experiment_id=experiment_id,
                        event_type="metric_update",
                        event_data=metrics
                    )
            
            logger.debug(f"Métricas ML actualizadas para {conversation_id}: {metrics}")
            
        except Exception as e:
            logger.error(f"Error actualizando métricas ML: {e}")
    
    async def _record_conversation_outcome_for_ml(
        self,
        conversation_id: str,
        outcome: str,
        outcome_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registrar el resultado final de la conversación para aprendizaje ML.
        
        Args:
            conversation_id: ID de la conversación
            outcome: Resultado (completed, abandoned, transferred, etc.)
            outcome_details: Detalles adicionales del resultado
        """
        self._init_ml_services()
        
        try:
            # Preparar detalles del resultado
            details = outcome_details or {}
            details['final_outcome'] = outcome
            details['end_time'] = datetime.now().isoformat()
            
            # Registrar resultado
            await self.outcome_tracker.end_conversation(
                conversation_id=conversation_id,
                outcome=outcome,
                final_metrics=details
            )
            
            # Procesar resultados de experimentos si hay
            if conversation_id in self.active_experiments:
                for experiment_id in self.active_experiments[conversation_id]:
                    # Determinar si fue exitoso basado en el outcome
                    success = outcome in ['completed', 'qualified', 'scheduled_followup']
                    
                    await self.ab_testing_framework.record_conversion(
                        experiment_id=experiment_id,
                        variant_id=details.get('variant_id', 'control'),
                        success=success,
                        value=details.get('conversion_value', 0)
                    )
                
                # Limpiar experimentos de esta conversación
                del self.active_experiments[conversation_id]
            
            # Trigger aprendizaje adaptativo si es necesario
            if await self._should_trigger_learning(outcome, details):
                await self.adaptive_learning_service.process_conversation_outcome(
                    conversation_id=conversation_id,
                    outcome_data=await self.outcome_tracker.get_conversation_data(conversation_id)
                )
            
            logger.info(f"Resultado ML registrado para {conversation_id}: {outcome}")
            
        except Exception as e:
            logger.error(f"Error registrando resultado ML: {e}")
    
    async def _get_active_experiments_for_conversation(
        self,
        conversation_id: str,
        customer_data: Dict[str, Any]
    ) -> List[str]:
        """
        Obtener experimentos activos aplicables a esta conversación.
        
        Args:
            conversation_id: ID de la conversación
            customer_data: Datos del cliente para segmentación
            
        Returns:
            Lista de IDs de experimentos asignados
        """
        self._init_ml_services()
        
        try:
            experiments = []
            
            # Obtener todos los experimentos activos
            active_experiments = await self.ab_testing_framework.get_active_experiments()
            
            for experiment in active_experiments:
                # Verificar si el cliente cumple con los criterios del experimento
                if self._customer_matches_experiment_criteria(
                    customer_data, 
                    experiment.get('targeting_criteria', {})
                ):
                    # Asignar a un grupo del experimento
                    variant = await self.ab_testing_framework.assign_variant(
                        experiment_id=experiment['id'],
                        user_id=customer_data.get('id', conversation_id)
                    )
                    
                    if variant:
                        experiments.append(experiment['id'])
                        logger.info(
                            f"Conversación {conversation_id} asignada a experimento "
                            f"{experiment['id']} (variante: {variant})"
                        )
            
            return experiments
            
        except Exception as e:
            logger.error(f"Error obteniendo experimentos activos: {e}")
            return []
    
    def _customer_matches_experiment_criteria(
        self,
        customer_data: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> bool:
        """
        Verificar si un cliente cumple con los criterios de un experimento.
        
        Args:
            customer_data: Datos del cliente
            criteria: Criterios del experimento
            
        Returns:
            True si cumple con los criterios
        """
        # Si no hay criterios, incluir a todos
        if not criteria:
            return True
        
        # Verificar edad
        if 'min_age' in criteria:
            age = customer_data.get('age', 0)
            if age < criteria['min_age']:
                return False
        
        if 'max_age' in criteria:
            age = customer_data.get('age', 100)
            if age > criteria['max_age']:
                return False
        
        # Verificar ubicación
        if 'locations' in criteria:
            location = customer_data.get('location', '').lower()
            if location not in [loc.lower() for loc in criteria['locations']]:
                return False
        
        # Verificar intereses
        if 'interests' in criteria:
            customer_interests = set(customer_data.get('interests', []))
            required_interests = set(criteria['interests'])
            if not customer_interests.intersection(required_interests):
                return False
        
        return True
    
    async def _should_trigger_learning(
        self,
        outcome: str,
        details: Dict[str, Any]
    ) -> bool:
        """
        Determinar si se debe triggear el aprendizaje adaptativo.
        
        Args:
            outcome: Resultado de la conversación
            details: Detalles del resultado
            
        Returns:
            True si se debe triggear aprendizaje
        """
        # Siempre aprender de conversaciones completadas
        if outcome in ['completed', 'qualified', 'scheduled_followup']:
            return True
        
        # Aprender de abandonos si duraron más de 2 minutos
        if outcome == 'abandoned' and details.get('duration_seconds', 0) > 120:
            return True
        
        # Aprender de transferencias humanas
        if outcome == 'human_transfer':
            return True
        
        return False
    
    async def get_ml_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Obtener resumen ML de una conversación."""
        self._init_ml_services()
        
        try:
            # Obtener datos del outcome tracker
            conversation_data = await self.outcome_tracker.get_conversation_data(conversation_id)
            
            if not conversation_data:
                return None
            
            # Agregar información de experimentos si existe
            if conversation_id in self.active_experiments:
                conversation_data['active_experiments'] = self.active_experiments[conversation_id]
            
            return conversation_data
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen ML: {e}")
            return None
    
    async def get_adaptive_learning_status(self) -> Dict[str, Any]:
        """Obtener el estado actual del sistema de aprendizaje adaptativo."""
        self._init_ml_services()
        
        try:
            return await self.adaptive_learning_service.get_learning_status()
        except Exception as e:
            logger.error(f"Error obteniendo estado de aprendizaje: {e}")
            return {"error": str(e)}