"""
Unit tests for Service Registry.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.services.conversation.service_registry import (
    ServiceRegistry,
    ServiceFactory,
    IntentAnalysisServiceFactory
)


class MockService:
    """Mock service for testing."""
    def __init__(self, name="mock"):
        self.name = name
        self.initialized = False
        self.cleaned_up = False
    
    async def initialize(self):
        self.initialized = True
    
    async def cleanup(self):
        self.cleaned_up = True


class MockServiceFactory(ServiceFactory):
    """Mock service factory for testing."""
    def __init__(self, service_name="mock"):
        self.service_name = service_name
        self.create_called = False
    
    async def create(self):
        self.create_called = True
        return MockService(self.service_name)


class TestServiceRegistry:
    """Test ServiceRegistry functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ServiceRegistry(industry="test")
    
    def test_initialization(self):
        """Test registry initialization."""
        assert self.registry.industry == "test"
        assert not self.registry._initialized
        assert len(self.registry._services) == 0
        assert len(self.registry._factories) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_core_services(self):
        """Test core services initialization."""
        # Mock the imports
        mock_services = {
            'intent_analysis': Mock(),
            'enhanced_intent_analysis': Mock(spec=['__init__']),
            'qualification': Mock(),
            'human_transfer': Mock(),
            'follow_up': Mock(),
            'personalization': Mock()
        }
        
        with patch.dict('sys.modules', {
            'src.services.intent_analysis_service': Mock(IntentAnalysisService=lambda: mock_services['intent_analysis']),
            'src.services.enhanced_intent_analysis_service': Mock(
                EnhancedIntentAnalysisService=lambda industry: mock_services['enhanced_intent_analysis']
            ),
            'src.services.qualification_service': Mock(LeadQualificationService=lambda: mock_services['qualification']),
            'src.services.human_transfer_service': Mock(HumanTransferService=lambda: mock_services['human_transfer']),
            'src.services.follow_up_service': Mock(FollowUpService=lambda: mock_services['follow_up']),
            'src.services.personalization_service': Mock(PersonalizationService=lambda: mock_services['personalization'])
        }):
            await self.registry.initialize()
            
            # Verify services are registered
            assert self.registry._initialized
            assert self.registry.get('intent_analysis') is mock_services['intent_analysis']
            assert self.registry.get('qualification') is mock_services['qualification']
            
            # Second initialize should be no-op
            await self.registry.initialize()
            assert self.registry._initialized
    
    def test_register_factory(self):
        """Test factory registration."""
        factory = MockServiceFactory("test_service")
        self.registry.register_factory("test_service", factory)
        
        assert "test_service" in self.registry._factories
        assert self.registry._factories["test_service"] is factory
    
    def test_register_service(self):
        """Test direct service registration."""
        service = MockService("direct")
        self.registry.register_service("direct_service", service)
        
        assert self.registry.get("direct_service") is service
        assert self.registry.has_service("direct_service")
    
    def test_get_service(self):
        """Test getting registered services."""
        service = MockService("test")
        self.registry.register_service("test", service)
        
        # Should return registered service
        assert self.registry.get("test") is service
        
        # Should return None for non-existent
        assert self.registry.get("non_existent") is None
    
    @pytest.mark.asyncio
    async def test_get_or_create_existing(self):
        """Test get_or_create with existing service."""
        service = MockService("existing")
        self.registry.register_service("existing", service)
        
        result = await self.registry.get_or_create("existing")
        assert result is service
    
    @pytest.mark.asyncio
    async def test_get_or_create_with_factory(self):
        """Test get_or_create with factory."""
        factory = MockServiceFactory("lazy")
        
        # Provide factory directly
        result = await self.registry.get_or_create("lazy", factory)
        
        assert factory.create_called
        assert isinstance(result, MockService)
        assert result.name == "lazy"
        assert self.registry.get("lazy") is result
    
    @pytest.mark.asyncio
    async def test_get_or_create_registered_factory(self):
        """Test get_or_create with pre-registered factory."""
        factory = MockServiceFactory("registered")
        self.registry.register_factory("registered", factory)
        
        result = await self.registry.get_or_create("registered")
        
        assert factory.create_called
        assert isinstance(result, MockService)
        assert result.name == "registered"
    
    @pytest.mark.asyncio
    async def test_get_or_create_no_factory_error(self):
        """Test get_or_create raises error when no factory available."""
        with pytest.raises(ValueError, match="Service 'missing' not found"):
            await self.registry.get_or_create("missing")
    
    def test_has_service(self):
        """Test service existence check."""
        assert not self.registry.has_service("test")
        
        self.registry.register_service("test", MockService())
        assert self.registry.has_service("test")
    
    def test_get_all_services(self):
        """Test getting all services."""
        service1 = MockService("service1")
        service2 = MockService("service2")
        
        self.registry.register_service("s1", service1)
        self.registry.register_service("s2", service2)
        
        all_services = self.registry.get_all_services()
        assert len(all_services) == 2
        assert all_services["s1"] is service1
        assert all_services["s2"] is service2
        
        # Should be a copy
        all_services["s3"] = MockService("s3")
        assert not self.registry.has_service("s3")
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test service cleanup."""
        # Register services with cleanup methods
        service1 = MockService("s1")
        service2 = MockService("s2")
        service3 = Mock(spec=['close'])  # Has close method
        service3.close = AsyncMock()
        
        self.registry.register_service("s1", service1)
        self.registry.register_service("s2", service2)
        self.registry.register_service("s3", service3)
        
        await self.registry.cleanup()
        
        # Verify cleanup was called
        assert service1.cleaned_up
        assert service2.cleaned_up
        service3.close.assert_called_once()
        
        # Registry should be cleared
        assert len(self.registry._services) == 0
        assert not self.registry._initialized
    
    @pytest.mark.asyncio
    async def test_cleanup_with_errors(self):
        """Test cleanup continues despite errors."""
        # Service that raises during cleanup
        bad_service = Mock()
        bad_service.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        
        good_service = MockService("good")
        
        self.registry.register_service("bad", bad_service)
        self.registry.register_service("good", good_service)
        
        # Should not raise
        await self.registry.cleanup()
        
        # Good service should still be cleaned up
        assert good_service.cleaned_up
        assert len(self.registry._services) == 0
    
    @pytest.mark.asyncio
    async def test_ml_services_initialization(self):
        """Test ML services initialization handling."""
        # Test with missing ML services (ImportError)
        with patch('src.services.conversation.service_registry.logger') as mock_logger:
            await self.registry._initialize_ml_services()
            
            # Should log warnings but not fail
            assert mock_logger.warning.called
    
    @pytest.mark.asyncio
    async def test_predictive_services_initialization(self):
        """Test predictive services initialization."""
        # Mock predictive services
        mock_predictors = {
            'objection': Mock(),
            'needs': Mock(),
            'conversion': Mock()
        }
        
        mock_decision_engine = Mock()
        
        with patch.dict('sys.modules', {
            'src.services.objection_prediction_service': Mock(
                ObjectionPredictionService=lambda: mock_predictors['objection']
            ),
            'src.services.needs_prediction_service': Mock(
                NeedsPredictionService=lambda: mock_predictors['needs']
            ),
            'src.services.conversion_prediction_service': Mock(
                ConversionPredictionService=lambda: mock_predictors['conversion']
            ),
            'src.services.unified_decision_engine': Mock(
                UnifiedDecisionEngine=lambda **kwargs: mock_decision_engine
            )
        }):
            await self.registry._initialize_predictive_services()
            
            # Verify services are registered
            assert self.registry.get('objection_predictor') is mock_predictors['objection']
            assert self.registry.get('needs_predictor') is mock_predictors['needs']
            assert self.registry.get('conversion_predictor') is mock_predictors['conversion']
            assert self.registry.get('decision_engine') is mock_decision_engine


class TestServiceFactories:
    """Test built-in service factories."""
    
    @pytest.mark.asyncio
    async def test_intent_analysis_factory(self):
        """Test IntentAnalysisServiceFactory."""
        factory = IntentAnalysisServiceFactory()
        
        with patch('src.services.conversation.service_registry.IntentAnalysisService') as mock_class:
            mock_service = Mock()
            mock_class.return_value = mock_service
            
            result = await factory.create()
            
            mock_class.assert_called_once()
            assert result is mock_service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])