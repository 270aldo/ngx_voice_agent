"""
Service Registry - Centralized service container with lazy initialization.
Part of the ConversationOrchestrator refactoring to break down the god class.
"""

import logging
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from abc import ABC, abstractmethod

# Type variable for generic service types
T = TypeVar('T')

logger = logging.getLogger(__name__)


class ServiceFactory(ABC, Generic[T]):
    """Abstract factory for creating services."""
    
    @abstractmethod
    async def create(self) -> T:
        """Create and initialize a service instance."""
        pass


class ServiceRegistry:
    """
    Centralized service container with lazy initialization.
    
    This class manages service lifecycle and provides dependency injection
    for the conversation system, helping to break down the god class pattern.
    """
    
    def __init__(self, industry: str = 'salud'):
        """
        Initialize the service registry.
        
        Args:
            industry: Industry for service customization
        """
        self.industry = industry
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, ServiceFactory] = {}
        self._initialized = False
        
        # Register default factories
        self._register_default_factories()
        
        logger.info(f"ServiceRegistry initialized for industry: {industry}")
    
    def _register_default_factories(self):
        """Register default service factories."""
        # These will be implemented as we refactor
        pass
    
    async def initialize(self):
        """Initialize core services that are always needed."""
        if self._initialized:
            return
        
        logger.info("Initializing core services...")
        
        try:
            # Import and initialize core services
            from src.services.intent_analysis_service import IntentAnalysisService
            from src.services.enhanced_intent_analysis_service import EnhancedIntentAnalysisService
            from src.services.qualification_service import LeadQualificationService
            from src.services.human_transfer_service import HumanTransferService
            from src.services.follow_up_service import FollowUpService
            from src.services.personalization_service import PersonalizationService
            
            # Initialize core services
            self._services['intent_analysis'] = IntentAnalysisService()
            self._services['enhanced_intent_analysis'] = EnhancedIntentAnalysisService(industry=self.industry)
            self._services['qualification'] = LeadQualificationService()
            self._services['human_transfer'] = HumanTransferService()
            self._services['follow_up'] = FollowUpService()
            self._services['personalization'] = PersonalizationService()
            
            # Initialize predictive services if available
            await self._initialize_predictive_services()
            
            # Initialize ML services if available
            await self._initialize_ml_services()
            
            self._initialized = True
            logger.info("Core services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            raise
    
    async def _initialize_predictive_services(self):
        """Initialize predictive ML services."""
        try:
            from src.services.objection_prediction_service import ObjectionPredictionService
            from src.services.needs_prediction_service import NeedsPredictionService
            from src.services.conversion_prediction_service import ConversionPredictionService
            from src.services.unified_decision_engine import UnifiedDecisionEngine
            
            # Initialize predictive services
            objection_predictor = ObjectionPredictionService()
            needs_predictor = NeedsPredictionService()
            conversion_predictor = ConversionPredictionService()
            
            # Initialize decision engine with predictors
            decision_engine = UnifiedDecisionEngine(
                conversion_predictor=conversion_predictor,
                objection_predictor=objection_predictor,
                needs_predictor=needs_predictor
            )
            
            # Store services
            self._services['objection_predictor'] = objection_predictor
            self._services['needs_predictor'] = needs_predictor
            self._services['conversion_predictor'] = conversion_predictor
            self._services['decision_engine'] = decision_engine
            
            logger.info("Predictive services initialized")
            
        except ImportError as e:
            logger.warning(f"Predictive services not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize predictive services: {e}")
    
    async def _initialize_ml_services(self):
        """Initialize ML pipeline and pattern recognition services."""
        try:
            # ML Pipeline
            try:
                from src.services.ml_pipeline import MLPipelineService
                self._services['ml_pipeline'] = MLPipelineService()
                logger.info("ML Pipeline service initialized")
            except ImportError:
                logger.warning("ML Pipeline service not available")
            
            # Pattern Recognition
            try:
                from src.services.pattern_recognition_engine import pattern_recognition_engine
                self._services['pattern_recognition'] = pattern_recognition_engine
                logger.info("Pattern Recognition engine initialized")
            except ImportError:
                logger.warning("Pattern Recognition engine not available")
                
        except Exception as e:
            logger.error(f"Failed to initialize ML services: {e}")
    
    def register_factory(self, service_name: str, factory: ServiceFactory):
        """
        Register a service factory for lazy initialization.
        
        Args:
            service_name: Name of the service
            factory: Factory instance for creating the service
        """
        self._factories[service_name] = factory
        logger.debug(f"Registered factory for service: {service_name}")
    
    def register_service(self, service_name: str, service_instance: Any):
        """
        Register a service instance directly.
        
        Args:
            service_name: Name of the service
            service_instance: The service instance
        """
        self._services[service_name] = service_instance
        logger.debug(f"Registered service: {service_name}")
    
    def get(self, service_name: str) -> Optional[Any]:
        """
        Get a service by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance or None if not found
        """
        return self._services.get(service_name)
    
    async def get_or_create(self, service_name: str, factory: Optional[ServiceFactory] = None) -> Any:
        """
        Get or create a service lazily.
        
        Args:
            service_name: Name of the service
            factory: Optional factory to use if service doesn't exist
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service doesn't exist and no factory provided
        """
        # Return if already exists
        if service_name in self._services:
            return self._services[service_name]
        
        # Try registered factory
        if service_name in self._factories:
            factory = self._factories[service_name]
        
        # Create using factory
        if factory:
            logger.info(f"Creating service lazily: {service_name}")
            service = await factory.create()
            self._services[service_name] = service
            return service
        
        raise ValueError(f"Service '{service_name}' not found and no factory provided")
    
    def has_service(self, service_name: str) -> bool:
        """Check if a service is registered."""
        return service_name in self._services
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all registered services."""
        return self._services.copy()
    
    async def cleanup(self):
        """Cleanup all services."""
        logger.info("Cleaning up services...")
        
        for service_name, service in self._services.items():
            try:
                # Call cleanup method if available
                if hasattr(service, 'cleanup'):
                    await service.cleanup()
                elif hasattr(service, 'close'):
                    await service.close()
                    
                logger.debug(f"Cleaned up service: {service_name}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup service {service_name}: {e}")
        
        self._services.clear()
        self._initialized = False
        logger.info("Services cleaned up")


# Example service factories
class IntentAnalysisServiceFactory(ServiceFactory):
    """Factory for creating IntentAnalysisService."""
    
    async def create(self):
        from src.services.intent_analysis_service import IntentAnalysisService
        return IntentAnalysisService()


class ProgramRouterFactory(ServiceFactory):
    """Factory for creating ProgramRouter."""
    
    def __init__(self, base_path: str = "src/agents/programs"):
        self.base_path = base_path
    
    async def create(self):
        from src.services.program_router import ProgramRouter
        router = ProgramRouter(base_path=self.base_path)
        await router.initialize()
        return router


class EmpathyEngineFactory(ServiceFactory):
    """Factory for creating AdvancedEmpathyEngine."""
    
    async def create(self):
        from src.services.advanced_empathy_engine import AdvancedEmpathyEngine
        return AdvancedEmpathyEngine()


class MultiVoiceServiceFactory(ServiceFactory):
    """Factory for creating MultiVoiceService."""
    
    async def create(self):
        from src.services.multi_voice_service import MultiVoiceService
        return MultiVoiceService()