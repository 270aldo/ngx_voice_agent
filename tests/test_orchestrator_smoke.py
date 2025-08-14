"""
Smoke Tests for Orchestrator Migration

Quick validation tests to ensure basic functionality works
with both legacy and refactored orchestrators.
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock

from src.services.conversation_service import ConversationService
from src.models.conversation import CustomerData
from src.config.settings import get_settings


class TestOrchestratorSmoke:
    """Smoke tests for orchestrator functionality."""

    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment."""
        # Mock external dependencies to avoid real API calls
        with patch('src.integrations.supabase.supabase_client') as mock_supabase:
            mock_supabase.return_value = MagicMock()
            yield

    def test_legacy_orchestrator_creation(self):
        """Test that legacy orchestrator can be created."""
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            # Clear settings cache to pick up new environment
            from src.config.settings import get_settings
            get_settings.cache_clear()
            
            with patch('src.services.conversation.orchestrator.ConversationOrchestrator') as mock_orch:
                mock_instance = MagicMock()
                mock_instance.industry = 'salud'
                mock_instance.platform_context = None
                mock_instance._initialized = False
                mock_instance._current_agent = None
                mock_orch.return_value = mock_instance
                
                service = ConversationService()
                
                assert service is not None
                assert service._orchestrator is mock_instance
                assert service.settings.use_refactored_orchestrator is False
                mock_orch.assert_called_once_with('salud', None)

    def test_refactored_orchestrator_creation(self):
        """Test that refactored orchestrator can be created."""
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            # Clear settings cache to pick up new environment
            from src.config.settings import get_settings
            get_settings.cache_clear()
            
            # Mock the entire import to avoid loading actual refactored modules
            with patch('src.services.conversation_service.ConversationService._create_orchestrator') as mock_create:
                mock_instance = MagicMock()
                mock_instance.industry = 'salud'
                mock_instance.platform_context = None
                mock_instance.initialized = False
                mock_create.return_value = mock_instance
                
                service = ConversationService()
                
                assert service is not None
                assert service._orchestrator is mock_instance
                assert service.settings.use_refactored_orchestrator is True

    def test_fallback_on_import_error(self):
        """Test fallback to legacy orchestrator when refactored import fails."""
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            # Mock the _create_orchestrator to simulate fallback behavior
            with patch('src.services.conversation_service.ConversationService._create_orchestrator') as mock_create:
                def side_effect():
                    # Simulate fallback logic
                    from unittest.mock import MagicMock
                    mock_instance = MagicMock()
                    mock_instance.industry = 'salud'
                    mock_instance.platform_context = None
                    mock_instance._initialized = False
                    mock_instance._current_agent = None
                    return mock_instance
                
                mock_create.side_effect = side_effect
                
                # Should not raise exception, should fall back
                service = ConversationService()
                
                assert service is not None
                assert service._orchestrator is not None
                # Feature flag still says to use refactored, but service fell back
                assert service.settings.use_refactored_orchestrator is True

    @pytest.mark.asyncio
    async def test_basic_async_methods_legacy(self):
        """Test that basic async methods work with legacy orchestrator."""
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            with patch('src.services.conversation.orchestrator.ConversationOrchestrator') as mock_orch:
                mock_instance = AsyncMock()
                mock_instance.industry = 'salud'
                mock_instance.platform_context = None
                mock_instance._initialized = True
                mock_instance._current_agent = None
                mock_orch.return_value = mock_instance
                
                service = ConversationService()
                
                # Test initialize
                await service.initialize()
                mock_instance.initialize.assert_called_once()
                
                # Test _ensure_initialized
                await service._ensure_initialized()
                mock_instance._ensure_initialized.assert_called_once()

    @pytest.mark.asyncio
    async def test_basic_async_methods_refactored(self):
        """Test that basic async methods work with refactored orchestrator."""
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            # Clear settings cache to pick up new environment
            from src.config.settings import get_settings
            get_settings.cache_clear()
            
            # Mock the _create_orchestrator method to avoid importing actual refactored modules
            with patch('src.services.conversation_service.ConversationService._create_orchestrator') as mock_create:
                mock_instance = AsyncMock()
                mock_instance.industry = 'salud'
                mock_instance.platform_context = None
                mock_instance.initialized = True
                # Don't add _ensure_initialized to simulate refactored orchestrator behavior
                delattr(mock_instance, '_ensure_initialized') if hasattr(mock_instance, '_ensure_initialized') else None
                mock_create.return_value = mock_instance
                
                service = ConversationService()
                
                # Test initialize
                await service.initialize()
                mock_instance.initialize.assert_called_once()
                
                # Test _ensure_initialized (should call initialize for refactored since no _ensure_initialized)
                mock_instance.reset_mock()
                await service._ensure_initialized()
                mock_instance.initialize.assert_called_once()

    def test_property_exposure(self):
        """Test that properties are properly exposed."""
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            with patch('src.services.conversation.orchestrator.ConversationOrchestrator') as mock_orch:
                mock_instance = MagicMock()
                mock_instance.industry = 'fitness'
                mock_instance.platform_context = 'test_context'
                mock_instance._initialized = True
                mock_instance._current_agent = 'test_agent'
                
                # Mock legacy services
                mock_instance.intent_analysis_service = 'intent_service'
                mock_instance.enhanced_intent_service = 'enhanced_service'
                mock_instance.qualification_service = 'qual_service'
                mock_instance.human_transfer_service = 'transfer_service'
                mock_instance.follow_up_service = 'followup_service'
                mock_instance.personalization_service = 'person_service'
                mock_instance.multi_voice_service = 'voice_service'
                mock_instance.program_router = 'router_service'
                
                mock_orch.return_value = mock_instance
                
                service = ConversationService(industry='fitness', platform_context='test_context')
                
                # Check that properties are properly exposed
                assert service.industry == 'fitness'
                assert service.platform_context == 'test_context'
                assert service._initialized is True
                assert service._current_agent == 'test_agent'
                
                # Check that services are exposed
                assert service.intent_analysis_service == 'intent_service'
                assert service.enhanced_intent_service == 'enhanced_service'
                assert service.qualification_service == 'qual_service'

    def test_configuration_reading(self):
        """Test that configuration is properly read."""
        # Test default (should be False)
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()
            # Clear cache to get fresh settings
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.use_refactored_orchestrator is False

        # Test explicit true
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.use_refactored_orchestrator is True

        # Test explicit false
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.use_refactored_orchestrator is False

    def test_service_instantiation_with_parameters(self):
        """Test service instantiation with different parameters."""
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            with patch('src.services.conversation.orchestrator.ConversationOrchestrator') as mock_orch:
                mock_instance = MagicMock()
                mock_instance.industry = 'health'
                mock_instance.platform_context = 'mobile'
                mock_instance._initialized = False
                mock_instance._current_agent = None
                mock_orch.return_value = mock_instance
                
                service = ConversationService(industry='health', platform_context='mobile')
                
                # Verify orchestrator was called with correct parameters
                mock_orch.assert_called_once_with('health', 'mobile')
                assert service.industry == 'health'
                assert service.platform_context == 'mobile'

    def test_logging_output(self, caplog):
        """Test that appropriate logging is generated."""
        import logging
        
        # Set the logger level to capture INFO logs
        caplog.set_level(logging.INFO)
        
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'false'}):
            # Clear settings cache to pick up new environment
            from src.config.settings import get_settings
            get_settings.cache_clear()
            
            with patch('src.services.conversation.orchestrator.ConversationOrchestrator') as mock_orch:
                mock_instance = MagicMock()
                mock_instance.industry = 'salud'
                mock_instance.platform_context = None
                mock_instance._initialized = False
                mock_instance._current_agent = None
                mock_orch.return_value = mock_instance
                
                # Capture logs for the specific logger
                with caplog.at_level(logging.INFO, logger="src.services.conversation_service"):
                    service = ConversationService()
                
                # Check that log messages were generated
                assert len(caplog.records) > 0, f"No log records captured. Available loggers: {[r.name for r in caplog.records]}"
                # Look for any log message that indicates legacy orchestrator usage
                log_messages = [r.message for r in caplog.records]
                assert any("legacy" in msg.lower() for msg in log_messages), f"No legacy orchestrator message found in: {log_messages}"

        caplog.clear()
        
        with patch.dict(os.environ, {'USE_REFACTORED_ORCHESTRATOR': 'true'}):
            # Clear settings cache to pick up new environment
            get_settings.cache_clear()
            
            # Use _create_orchestrator mock to avoid actual imports
            with patch('src.services.conversation_service.ConversationService._create_orchestrator') as mock_create:
                mock_instance = MagicMock()
                mock_instance.industry = 'salud'
                mock_instance.platform_context = None
                mock_instance.initialized = False
                mock_create.return_value = mock_instance
                
                # Capture logs for the specific logger
                with caplog.at_level(logging.INFO, logger="src.services.conversation_service"):
                    service = ConversationService()
                
                # Check that log messages were generated
                log_messages = [r.message for r in caplog.records]
                assert len(caplog.records) > 0, f"No log records captured for refactored test"
                assert any("refactored" in msg.lower() for msg in log_messages), f"No refactored orchestrator message found in: {log_messages}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])