"""
Integration Tests for Orchestrator Migration

This test suite validates that the legacy and refactored orchestrator
implementations provide compatible APIs and behavior.
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from src.services.conversation_service import ConversationService
from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformContext, PlatformInfo
from src.config.settings import get_settings


class TestOrchestratorIntegration:
    """Test orchestrator integration and compatibility."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up common mocks for testing."""
        # Mock external dependencies
        with patch('src.integrations.supabase.get_supabase_client') as mock_supabase, \
             patch('src.services.conversation.orchestrator.ConversationOrchestrator') as mock_legacy, \
             patch('src.services.conversation.orchestrator_refactored.ConversationOrchestratorFacade') as mock_refactored:
            
            # Configure mock clients
            mock_supabase.return_value = MagicMock()
            
            # Configure legacy orchestrator mock
            mock_legacy_instance = AsyncMock()
            mock_legacy_instance.industry = 'salud'
            mock_legacy_instance.platform_context = None
            mock_legacy_instance._initialized = True
            mock_legacy_instance._current_agent = None
            mock_legacy.return_value = mock_legacy_instance
            
            # Configure refactored orchestrator mock
            mock_refactored_instance = AsyncMock()
            mock_refactored_instance.industry = 'salud'
            mock_refactored_instance.platform_context = None
            mock_refactored_instance.initialized = True
            mock_refactored.return_value = mock_refactored_instance
            
            self.mock_legacy = mock_legacy_instance
            self.mock_refactored = mock_refactored_instance
            
            yield

    @pytest.fixture
    def sample_customer_data(self) -> CustomerData:
        """Create sample customer data for testing."""
        return CustomerData(
            customer_id="test-123",
            name="Juan Pérez",
            email="juan@example.com",
            phone="+34600123456",
            customer_type="gym_owner",
            additional_info={"gym_size": "medium"}
        )

    @pytest.fixture
    def sample_platform_info(self) -> PlatformInfo:
        """Create sample platform info for testing."""
        return PlatformInfo(
            platform_type="web",
            user_agent="Test Browser",
            ip_address="127.0.0.1"
        )

    @pytest.mark.asyncio
    async def test_legacy_orchestrator_initialization(self, sample_customer_data):
        """Test that legacy orchestrator initializes correctly."""
        # Force legacy orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            service = ConversationService()
            
            assert service.settings.use_refactored_orchestrator is False
            assert service._orchestrator is not None
            
            # Test initialization
            await service.initialize()
            self.mock_legacy.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_refactored_orchestrator_initialization(self, sample_customer_data):
        """Test that refactored orchestrator initializes correctly."""
        # Force refactored orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            service = ConversationService()
            
            assert service.settings.use_refactored_orchestrator is True
            assert service._orchestrator is not None
            
            # Test initialization
            await service.initialize()
            self.mock_refactored.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_conversation_compatibility(self, sample_customer_data, sample_platform_info):
        """Test that both orchestrators handle start_conversation calls."""
        
        # Mock conversation state
        mock_conversation = ConversationState(
            conversation_id="conv-123",
            customer_data=sample_customer_data,
            messages=[],
            sales_phase="greeting",
            context={}
        )
        
        # Test legacy orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            service = ConversationService()
            self.mock_legacy.start_conversation.return_value = mock_conversation
            
            result = await service.start_conversation(
                sample_customer_data, 
                program_type="fitness_coaching",
                platform_info=sample_platform_info
            )
            
            # Verify legacy method was called with correct signature
            self.mock_legacy.start_conversation.assert_called_once_with(
                sample_customer_data, "fitness_coaching", sample_platform_info
            )
            assert result == mock_conversation

        # Test refactored orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            service = ConversationService()
            self.mock_refactored.start_conversation.return_value = mock_conversation
            
            result = await service.start_conversation(
                sample_customer_data,
                program_type="fitness_coaching", 
                platform_info=sample_platform_info
            )
            
            # Verify refactored method was called with adapted signature
            self.mock_refactored.start_conversation.assert_called_once()
            call_args = self.mock_refactored.start_conversation.call_args
            assert call_args[0][0] == sample_customer_data  # customer_data
            assert call_args[0][1] is not None  # platform_context (converted)

    @pytest.mark.asyncio
    async def test_process_message_compatibility(self):
        """Test that both orchestrators handle process_message calls."""
        
        # Mock response
        mock_response = {
            "text": "¡Hola! Soy María de NGX. ¿En qué puedo ayudarte hoy?",
            "metadata": {"intent": "greeting", "sentiment": "positive"},
            "analytics": {"confidence": 0.95}
        }
        
        # Test legacy orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            service = ConversationService()
            self.mock_legacy.process_message.return_value = mock_response
            
            result = await service.process_message(
                "conv-123", 
                "Hola, necesito información sobre NGX",
                audio_data=b"fake_audio_data"
            )
            
            # Verify legacy method signature
            self.mock_legacy.process_message.assert_called_once_with(
                "conv-123", "Hola, necesito información sobre NGX", b"fake_audio_data"
            )
            assert result == mock_response

        # Test refactored orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            service = ConversationService()
            self.mock_refactored.process_message.return_value = mock_response
            
            result = await service.process_message(
                "conv-123",
                "Hola, necesito información sobre NGX", 
                audio_data=b"fake_audio_data"
            )
            
            # Verify refactored method signature (audio_data -> voice_enabled)
            self.mock_refactored.process_message.assert_called_once_with(
                "conv-123", "Hola, necesito información sobre NGX", True  # voice_enabled=True
            )

    @pytest.mark.asyncio
    async def test_end_conversation_compatibility(self):
        """Test that both orchestrators handle end_conversation calls."""
        
        # Mock responses
        legacy_response = ConversationState(
            conversation_id="conv-123",
            status="completed",
            messages=[]
        )
        
        refactored_response = {
            "success": True,
            "conversation_id": "conv-123",
            "metrics": {"duration": 300, "message_count": 5},
            "reason": "completed"
        }
        
        # Test legacy orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            service = ConversationService()
            self.mock_legacy.end_conversation.return_value = legacy_response
            
            result = await service.end_conversation("conv-123", "user_ended")
            
            self.mock_legacy.end_conversation.assert_called_once_with("conv-123", "user_ended")
            assert result == legacy_response

        # Test refactored orchestrator
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            service = ConversationService()
            self.mock_refactored.end_conversation.return_value = refactored_response
            
            result = await service.end_conversation("conv-123", "user_ended")
            
            # Verify refactored method signature (end_reason -> reason)
            self.mock_refactored.end_conversation.assert_called_once_with("conv-123", reason="user_ended")
            assert result == refactored_response

    @pytest.mark.asyncio
    async def test_fallback_mechanism(self):
        """Test that service falls back to legacy orchestrator on errors."""
        
        # Force refactored orchestrator but simulate import failure
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}), \
             patch('src.services.conversation_service.ConversationService._create_orchestrator') as mock_create:
            
            # First call fails (refactored import fails)
            # Second call succeeds (legacy fallback)
            def side_effect():
                raise ImportError("Refactored orchestrator not available")
            
            mock_create.side_effect = side_effect
            
            # Should not raise exception, should use fallback
            service = ConversationService()
            
            # Verify the service was created (with fallback)
            assert service._orchestrator is not None

    def test_property_synchronization(self):
        """Test that properties are properly synchronized between orchestrators."""
        
        # Test legacy orchestrator property sync
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            service = ConversationService()
            
            # Properties should be synced from legacy orchestrator
            assert hasattr(service, 'industry')
            assert hasattr(service, 'platform_context')
            assert hasattr(service, '_initialized')

        # Test refactored orchestrator property sync
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            service = ConversationService()
            
            # Properties should be synced from refactored orchestrator
            assert hasattr(service, 'industry')
            assert hasattr(service, 'platform_context')
            assert hasattr(service, '_initialized')

    def test_legacy_services_exposure(self):
        """Test that legacy services are properly exposed or set to None."""
        
        # Test with legacy orchestrator (services should be available)
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            service = ConversationService()
            
            # Services should be exposed from legacy orchestrator
            legacy_services = [
                'intent_analysis_service', 'enhanced_intent_service', 'qualification_service',
                'human_transfer_service', 'follow_up_service', 'personalization_service',
                'multi_voice_service', 'program_router'
            ]
            
            for service_name in legacy_services:
                assert hasattr(service, service_name)

        # Test with refactored orchestrator (services might be None)
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            service = ConversationService()
            
            # Services should exist but might be None
            for service_name in legacy_services:
                assert hasattr(service, service_name)

    @pytest.mark.asyncio
    async def test_error_handling_parity(self):
        """Test that error handling works consistently across both orchestrators."""
        
        # Configure mock to raise an exception
        test_exception = Exception("Test error")
        
        # Test legacy orchestrator error handling
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            service = ConversationService()
            self.mock_legacy.process_message.side_effect = test_exception
            
            with pytest.raises(Exception) as exc_info:
                await service.process_message("conv-123", "test message")
            assert str(exc_info.value) == "Test error"

        # Test refactored orchestrator error handling
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            service = ConversationService()
            self.mock_refactored.process_message.side_effect = test_exception
            
            with pytest.raises(Exception) as exc_info:
                await service.process_message("conv-123", "test message")
            assert str(exc_info.value) == "Test error"

    def test_configuration_validation(self):
        """Test that configuration is properly validated."""
        
        # Test that feature flag is properly read
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            settings = get_settings()
            assert settings.use_refactored_orchestrator is True
            
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            settings = get_settings()
            assert settings.use_refactored_orchestrator is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])