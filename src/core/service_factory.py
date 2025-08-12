"""
Service Factory

Centralized factory for creating service instances and resolving dependencies.
This pattern helps avoid circular imports by deferring service creation.
"""

import logging
from typing import Dict, Any, Optional, Type, Callable
from functools import lru_cache

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory class for creating and managing service instances.
    
    Uses lazy loading and caching to avoid circular dependencies
    and improve performance.
    """
    
    def __init__(self):
        """Initialize the service factory."""
        self._services: Dict[str, Any] = {}
        self._service_creators: Dict[str, Callable] = {}
        self._service_configs: Dict[str, Dict[str, Any]] = {}
        
        # Register all service creators
        self._register_service_creators()
    
    def _register_service_creators(self):
        """Register all service creator functions."""
        # Conversation services
        self._service_creators['conversation_orchestrator'] = self._create_conversation_orchestrator
        self._service_creators['conversation_manager'] = self._create_conversation_manager
        self._service_creators['message_processor'] = self._create_message_processor
        self._service_creators['response_builder'] = self._create_response_builder
        self._service_creators['integration_handler'] = self._create_integration_handler
        self._service_creators['metrics_collector'] = self._create_metrics_collector
        
        # ML services
        self._service_creators['ml_pipeline'] = self._create_ml_pipeline
        self._service_creators['pattern_recognition'] = self._create_pattern_recognition
        self._service_creators['objection_predictor'] = self._create_objection_predictor
        self._service_creators['needs_predictor'] = self._create_needs_predictor
        self._service_creators['conversion_predictor'] = self._create_conversion_predictor
        
        # Integration services
        self._service_creators['openai_client'] = self._create_openai_client
        self._service_creators['elevenlabs_client'] = self._create_elevenlabs_client
        self._service_creators['supabase_client'] = self._create_supabase_client
        
        # Business services
        self._service_creators['lead_qualification'] = self._create_lead_qualification
        self._service_creators['roi_calculator'] = self._create_roi_calculator
        self._service_creators['tier_detection'] = self._create_tier_detection
        self._service_creators['empathy_engine'] = self._create_empathy_engine
        
        # Infrastructure services
        self._service_creators['cache_manager'] = self._create_cache_manager
        self._service_creators['websocket_manager'] = self._create_websocket_manager
        self._service_creators['rate_limiter'] = self._create_rate_limiter
    
    def get_service(
        self,
        service_name: str,
        config: Optional[Dict[str, Any]] = None,
        force_new: bool = False
    ) -> Any:
        """
        Get a service instance by name.
        
        Args:
            service_name: Name of the service to get
            config: Optional configuration for the service
            force_new: Force creation of a new instance
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service name is not registered
        """
        if service_name not in self._service_creators:
            raise ValueError(f"Unknown service: {service_name}")
        
        # Return cached instance if available and not forcing new
        if not force_new and service_name in self._services:
            return self._services[service_name]
        
        # Store config if provided
        if config:
            self._service_configs[service_name] = config
        
        # Create new instance
        try:
            creator = self._service_creators[service_name]
            service = creator()
            
            # Cache the instance
            if not force_new:
                self._services[service_name] = service
            
            logger.info(f"Created service: {service_name}")
            return service
            
        except Exception as e:
            logger.error(f"Failed to create service {service_name}: {e}")
            raise
    
    def clear_cache(self, service_name: Optional[str] = None):
        """
        Clear cached service instances.
        
        Args:
            service_name: Optional specific service to clear
        """
        if service_name:
            if service_name in self._services:
                del self._services[service_name]
                logger.info(f"Cleared cache for service: {service_name}")
        else:
            self._services.clear()
            logger.info("Cleared all service caches")
    
    # Service creator methods
    
    def _create_conversation_orchestrator(self) -> Any:
        """Create ConversationOrchestrator instance."""
        # Use the refactored version
        from src.services.conversation.orchestrator_refactored import ConversationOrchestratorFacade
        
        config = self._service_configs.get('conversation_orchestrator', {})
        return ConversationOrchestratorFacade(**config)
    
    def _create_conversation_manager(self) -> Any:
        """Create ConversationManager instance."""
        from src.services.conversation.orchestrator_refactored.conversation_manager import ConversationManager
        return ConversationManager()
    
    def _create_message_processor(self) -> Any:
        """Create MessageProcessor instance."""
        from src.services.conversation.orchestrator_refactored.message_processor import MessageProcessor
        return MessageProcessor()
    
    def _create_response_builder(self) -> Any:
        """Create ResponseBuilder instance."""
        from src.services.conversation.orchestrator_refactored.response_builder import ResponseBuilder
        return ResponseBuilder()
    
    def _create_integration_handler(self) -> Any:
        """Create IntegrationHandler instance."""
        from src.services.conversation.orchestrator_refactored.integration_handler import IntegrationHandler
        return IntegrationHandler()
    
    def _create_metrics_collector(self) -> Any:
        """Create MetricsCollector instance."""
        from src.services.conversation.orchestrator_refactored.metrics_collector import MetricsCollector
        return MetricsCollector()
    
    def _create_ml_pipeline(self) -> Any:
        """Create ML Pipeline service."""
        try:
            from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
            return MLPipelineService()
        except ImportError:
            logger.warning("ML Pipeline service not available")
            return None
    
    def _create_pattern_recognition(self) -> Any:
        """Create Pattern Recognition engine."""
        try:
            from src.services.pattern_recognition_engine import pattern_recognition_engine
            return pattern_recognition_engine
        except ImportError:
            logger.warning("Pattern Recognition engine not available")
            return None
    
    def _create_objection_predictor(self) -> Any:
        """Create Objection Prediction service."""
        from src.services.objection_prediction_service import ObjectionPredictionService
        service = ObjectionPredictionService()
        # Initialize model if needed
        if not service.model:
            try:
                service.train_model()
            except Exception as e:
                logger.warning(f"Failed to train objection predictor: {e}")
        return service
    
    def _create_needs_predictor(self) -> Any:
        """Create Needs Prediction service."""
        from src.services.needs_prediction_service import NeedsPredictionService
        service = NeedsPredictionService()
        # Initialize model if needed
        if not service.model:
            try:
                service.train_model()
            except Exception as e:
                logger.warning(f"Failed to train needs predictor: {e}")
        return service
    
    def _create_conversion_predictor(self) -> Any:
        """Create Conversion Prediction service."""
        from src.services.conversion_prediction_service import ConversionPredictionService
        service = ConversionPredictionService()
        # Initialize model if needed
        if not service.model:
            try:
                service.train_model()
            except Exception as e:
                logger.warning(f"Failed to train conversion predictor: {e}")
        return service
    
    def _create_openai_client(self) -> Any:
        """Create OpenAI client."""
        from src.integrations.openai_client import OpenAIClient
        config = self._service_configs.get('openai_client', {})
        return OpenAIClient(**config)
    
    def _create_elevenlabs_client(self) -> Any:
        """Create ElevenLabs client."""
        from src.integrations.elevenlabs import voice_engine
        return voice_engine
    
    def _create_supabase_client(self) -> Any:
        """Create Supabase client."""
        from src.integrations.supabase.resilient_client import resilient_supabase_client
        return resilient_supabase_client
    
    def _create_lead_qualification(self) -> Any:
        """Create Lead Qualification service."""
        from src.services.qualification_service import LeadQualificationService
        return LeadQualificationService()
    
    def _create_roi_calculator(self) -> Any:
        """Create ROI Calculator service."""
        from src.services.ngx_roi_calculator import NGXROICalculator
        return NGXROICalculator()
    
    def _create_tier_detection(self) -> Any:
        """Create Tier Detection service."""
        from src.services.tier_detection_service import TierDetectionService
        return TierDetectionService()
    
    def _create_empathy_engine(self) -> Any:
        """Create Empathy Engine."""
        from src.services.advanced_empathy_engine import AdvancedEmpathyEngine
        return AdvancedEmpathyEngine()
    
    def _create_cache_manager(self) -> Any:
        """Create Cache Manager."""
        from src.services.ngx_cache_manager import NGXCacheManager
        return NGXCacheManager()
    
    def _create_websocket_manager(self) -> Any:
        """Create WebSocket Manager."""
        from src.services.websocket.websocket_manager import manager
        return manager
    
    def _create_rate_limiter(self) -> Any:
        """Create Rate Limiter."""
        from src.api.middleware.rate_limiter import RateLimiter
        from src.config.settings import settings
        
        return RateLimiter(
            requests_per_minute=settings.rate_limit_per_minute,
            requests_per_hour=settings.rate_limit_per_hour,
            whitelist_ips=settings.rate_limit_whitelist_ips
        )
    
    def register_custom_service(
        self,
        service_name: str,
        creator_func: Callable[[], Any]
    ):
        """
        Register a custom service creator.
        
        Args:
            service_name: Name of the service
            creator_func: Function that creates the service
        """
        self._service_creators[service_name] = creator_func
        logger.info(f"Registered custom service: {service_name}")
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all cached service instances."""
        return self._services.copy()
    
    def is_service_available(self, service_name: str) -> bool:
        """
        Check if a service is available.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if service can be created
        """
        if service_name not in self._service_creators:
            return False
        
        try:
            # Try to create the service
            service = self.get_service(service_name)
            return service is not None
        except Exception:
            return False


# Global singleton instance
_service_factory = ServiceFactory()


def get_service_factory() -> ServiceFactory:
    """Get the global service factory instance."""
    return _service_factory


def get_service(
    service_name: str,
    config: Optional[Dict[str, Any]] = None,
    force_new: bool = False
) -> Any:
    """
    Convenience function to get a service from the global factory.
    
    Args:
        service_name: Name of the service
        config: Optional configuration
        force_new: Force creation of new instance
        
    Returns:
        Service instance
    """
    return _service_factory.get_service(service_name, config, force_new)


def clear_service_cache(service_name: Optional[str] = None):
    """
    Clear service cache.
    
    Args:
        service_name: Optional specific service to clear
    """
    _service_factory.clear_cache(service_name)