"""
Test suite for ML Pipeline Integration.

This test suite verifies that all ML Pipeline components are properly integrated
and working together in the conversation orchestrator.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import uuid

from src.services.conversation.orchestrator import ConversationOrchestrator
from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformInfo


@pytest.fixture
async def orchestrator():
    """Create a test orchestrator instance."""
    orchestrator = ConversationOrchestrator(industry='salud')
    await orchestrator.initialize()
    return orchestrator


@pytest.fixture
def customer_data():
    """Create test customer data."""
    return CustomerData(
        id="test-customer-123",
        name="Juan Pérez",
        age=35,
        email="juan@test.com",
        phone="+1234567890",
        initial_message="Hola, quiero información sobre sus programas"
    )


@pytest.fixture
def platform_info():
    """Create test platform info."""
    return PlatformInfo(
        source="web",
        user_agent="test-agent",
        ip="127.0.0.1"
    )


class TestMLPipelineIntegration:
    """Test ML Pipeline Integration functionality."""
    
    @pytest.mark.asyncio
    async def test_ml_pipeline_initialization(self, orchestrator):
        """Test that ML Pipeline is properly initialized."""
        assert orchestrator.ml_pipeline is not None
        assert orchestrator.pattern_recognition is not None
        assert hasattr(orchestrator.ml_pipeline, 'event_tracker')
        assert hasattr(orchestrator.ml_pipeline, 'process_conversation_predictions')
    
    @pytest.mark.asyncio
    async def test_conversation_tracking_integration(self, orchestrator, customer_data, platform_info):
        """Test that conversations are properly tracked in ML Pipeline."""
        # Start conversation
        state = await orchestrator.start_conversation(
            customer_data=customer_data,
            platform_info=platform_info
        )
        
        assert state is not None
        assert state.conversation_id is not None
        assert state.ml_tracking_enabled is True
        
        # Mock ML Pipeline event tracker
        with patch.object(orchestrator.ml_pipeline.event_tracker, 'track_event', new_callable=AsyncMock) as mock_track:
            # Process message
            result = await orchestrator.process_message(
                conversation_id=state.conversation_id,
                message_text="¿Cuánto cuesta el programa PRIME?"
            )
            
            # Verify event tracking was called
            assert mock_track.called
            call_args = mock_track.call_args_list[0]
            assert call_args[1]['event_type'] == 'message_exchange'
            assert 'conversation_id' in call_args[1]['event_data']
            assert 'emotion_detected' in call_args[1]['event_data']
    
    @pytest.mark.asyncio
    async def test_pattern_recognition_integration(self, orchestrator, customer_data):
        """Test that pattern recognition is integrated with conversation flow."""
        # Start conversation
        state = await orchestrator.start_conversation(customer_data=customer_data)
        
        # Mock pattern recognition
        mock_patterns = [
            {
                "type": "price_sensitivity",
                "pattern": "high",
                "confidence": 0.85,
                "data": {"price_mentions": 2, "concern_levels": ["high"]}
            }
        ]
        
        with patch.object(orchestrator.pattern_recognition, 'detect_patterns', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = mock_patterns
            
            # Process price-related message
            result = await orchestrator.process_message(
                conversation_id=state.conversation_id,
                message_text="Está muy caro, no puedo pagar tanto"
            )
            
            # Verify pattern detection was called
            assert mock_detect.called
            call_args = mock_detect.call_args[1]
            assert call_args['conversation_id'] == state.conversation_id
            assert 'messages' in call_args
            assert 'context' in call_args
            
            # Check that patterns were stored in state
            updated_state = await orchestrator._get_conversation_state(state.conversation_id)
            assert 'detected_patterns' in updated_state.context
    
    @pytest.mark.asyncio
    async def test_ab_testing_integration(self, orchestrator, customer_data):
        """Test that A/B testing is integrated with ML Pipeline."""
        # Mock A/B testing
        mock_ab_variant = {
            "experiment_id": "greeting_experiment_1",
            "variant_id": "warm_personal",
            "variant_name": "Warm Personal",
            "parameters": {"style": "warm", "empathy_level": "high"}
        }
        
        with patch.object(orchestrator.ab_testing, 'get_greeting_variant', new_callable=AsyncMock) as mock_ab:
            mock_ab.return_value = mock_ab_variant
            
            # Start conversation (which uses greeting A/B testing)
            state = await orchestrator.start_conversation(customer_data=customer_data)
            
            # Verify A/B testing was called
            assert mock_ab.called
            
            # Check that variant was applied
            # The greeting should be influenced by the A/B test variant
            assert len(state.messages) > 0
            greeting_message = state.messages[0]
            assert greeting_message.role == "assistant"
    
    @pytest.mark.asyncio
    async def test_predictive_insights_flow(self, orchestrator, customer_data):
        """Test that predictive insights flow through the ML Pipeline."""
        state = await orchestrator.start_conversation(customer_data=customer_data)
        
        # Mock predictive services
        mock_objections = [{"type": "price", "confidence": 0.9}]
        mock_needs = [{"type": "weight_loss", "confidence": 0.85}]
        mock_conversion = {"probability": 0.75, "recommended_actions": ["focus_on_value"]}
        
        with patch.object(orchestrator, '_run_predictive_analysis', new_callable=AsyncMock) as mock_predict:
            mock_predict.return_value = {
                "objections_predicted": mock_objections,
                "needs_detected": mock_needs,
                "conversion_probability": 0.75,
                "recommended_actions": ["focus_on_value"]
            }
            
            # Process message
            result = await orchestrator.process_message(
                conversation_id=state.conversation_id,
                message_text="Me interesa pero tengo dudas sobre el precio"
            )
            
            # Verify predictive analysis was called
            assert mock_predict.called
            
            # Check that insights are included in response
            assert 'ml_insights' in result
            assert result['ml_insights']['conversion_probability'] == 0.75
    
    @pytest.mark.asyncio
    async def test_ml_pipeline_predictions_processing(self, orchestrator, customer_data):
        """Test that ML Pipeline processes predictions correctly."""
        state = await orchestrator.start_conversation(customer_data=customer_data)
        
        # Mock ML Pipeline process_conversation_predictions
        mock_pipeline_result = {
            "predictions": {
                "objections": {"predicted_objections": [{"type": "price", "confidence": 0.9}]},
                "needs": {"predicted_needs": [{"type": "weight_loss", "confidence": 0.85}]},
                "conversion": {"probability": 0.75}
            },
            "tracking_id": "test-tracking-123",
            "ab_variants": {
                "pricing_experiment": {
                    "experiment_id": "pricing_exp_1",
                    "variant_id": "value_focus",
                    "parameters": {"approach": "value_demonstration"}
                }
            },
            "confidence_scores": {
                "objection_confidence": 0.9,
                "needs_confidence": 0.85,
                "conversion_probability": 0.75
            }
        }
        
        with patch.object(orchestrator.ml_pipeline, 'process_conversation_predictions', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_pipeline_result
            
            # Process message
            result = await orchestrator.process_message(
                conversation_id=state.conversation_id,
                message_text="¿Qué incluye el programa?"
            )
            
            # Verify ML Pipeline processing was called
            assert mock_process.called
            call_args = mock_process.call_args[1]
            assert call_args['conversation_id'] == state.conversation_id
            assert 'messages' in call_args
            assert 'context' in call_args
            
            # Check that A/B variants were stored in state
            updated_state = await orchestrator._get_conversation_state(state.conversation_id)
            assert 'ab_variants' in updated_state.context
    
    @pytest.mark.asyncio
    async def test_outcome_recording_integration(self, orchestrator, customer_data):
        """Test that conversation outcomes are properly recorded in ML Pipeline."""
        state = await orchestrator.start_conversation(customer_data=customer_data)
        
        # Add some conversation history
        await orchestrator.process_message(
            conversation_id=state.conversation_id,
            message_text="Me interesa el programa PRIME"
        )
        
        # Mock ML Pipeline outcome recording
        with patch.object(orchestrator.ml_pipeline, 'record_conversation_outcome', new_callable=AsyncMock) as mock_record:
            # End conversation
            final_state = await orchestrator.end_conversation(
                conversation_id=state.conversation_id,
                end_reason="completed"
            )
            
            # Verify outcome recording was called
            assert mock_record.called
            call_args = mock_record.call_args[1]
            assert call_args['conversation_id'] == state.conversation_id
            assert call_args['outcome'] == "completed"
            assert 'metrics' in call_args
            assert 'final_tier' in call_args['metrics']
            assert 'message_count' in call_args['metrics']
    
    @pytest.mark.asyncio
    async def test_feedback_loop_integration(self, orchestrator, customer_data):
        """Test that feedback loop is integrated with conversation outcomes."""
        state = await orchestrator.start_conversation(customer_data=customer_data)
        
        # Process multiple messages to create learning opportunities
        messages = [
            "Hola, me interesa el programa PRIME",
            "¿Cuánto cuesta?",
            "Está caro, pero me gusta lo que ofrecen",
            "Sí, quiero empezar"
        ]
        
        for msg in messages:
            await orchestrator.process_message(
                conversation_id=state.conversation_id,
                message_text=msg
            )
        
        # Mock ML Pipeline feedback processing
        with patch.object(orchestrator.ml_pipeline, 'record_conversation_outcome', new_callable=AsyncMock) as mock_record:
            # End with successful outcome
            await orchestrator.end_conversation(
                conversation_id=state.conversation_id,
                end_reason="completed"
            )
            
            # Verify outcome was recorded for feedback loop
            assert mock_record.called
            # The feedback loop should process this automatically via background tasks
    
    @pytest.mark.asyncio
    async def test_error_handling_in_ml_pipeline(self, orchestrator, customer_data):
        """Test that ML Pipeline integration handles errors gracefully."""
        state = await orchestrator.start_conversation(customer_data=customer_data)
        
        # Mock ML Pipeline to raise an exception
        with patch.object(orchestrator.ml_pipeline.event_tracker, 'track_event', new_callable=AsyncMock) as mock_track:
            mock_track.side_effect = Exception("ML Pipeline connection error")
            
            # Process message - should not fail despite ML Pipeline error
            result = await orchestrator.process_message(
                conversation_id=state.conversation_id,
                message_text="¿Cómo funciona el programa?"
            )
            
            # Conversation should continue normally
            assert result is not None
            assert 'response' in result
            assert result['should_continue'] is True
    
    @pytest.mark.asyncio
    async def test_ml_metrics_update(self, orchestrator, customer_data):
        """Test that ML metrics are updated during conversation."""
        state = await orchestrator.start_conversation(customer_data=customer_data)
        
        # Mock ML metrics update
        with patch.object(orchestrator, '_update_ml_conversation_metrics', new_callable=AsyncMock) as mock_update:
            # Process message
            await orchestrator.process_message(
                conversation_id=state.conversation_id,
                message_text="Me parece interesante el programa"
            )
            
            # Verify metrics update was called
            assert mock_update.called
            call_args = mock_update.call_args
            assert call_args[0][0] == state.conversation_id  # conversation_id
            metrics = call_args[0][1]  # metrics dict
            assert 'emotional_state' in metrics
            assert 'tier_detected' in metrics
            assert 'engagement_level' in metrics
            assert 'sales_phase' in metrics


class TestMLPipelineComponents:
    """Test individual ML Pipeline components."""
    
    @pytest.mark.asyncio
    async def test_event_tracker_functionality(self, orchestrator):
        """Test that the event tracker works correctly."""
        if orchestrator.ml_pipeline and orchestrator.ml_pipeline.event_tracker:
            event_id = await orchestrator.ml_pipeline.event_tracker.track_event(
                event_type="test_event",
                event_data={"test": "data"},
                conversation_id="test-conv-123"
            )
            
            assert event_id is not None
            assert isinstance(event_id, str)
    
    @pytest.mark.asyncio
    async def test_pattern_recognition_functionality(self, orchestrator):
        """Test that pattern recognition works correctly."""
        if orchestrator.pattern_recognition:
            # Create test messages
            messages = [
                {"role": "user", "content": "Hola, me interesa el programa"},
                {"role": "assistant", "content": "¡Perfecto! Te ayudo con información"},
                {"role": "user", "content": "¿Cuánto cuesta?"},
                {"role": "assistant", "content": "El programa PRIME tiene diferentes opciones..."}
            ]
            
            patterns = await orchestrator.pattern_recognition.detect_patterns(
                conversation_id="test-conv-123",
                messages=messages,
                context={"phase": "exploration", "emotional_state": "interested"}
            )
            
            assert isinstance(patterns, list)
            # Should detect conversation flow and potentially price sensitivity
    
    @pytest.mark.asyncio
    async def test_ab_testing_variant_selection(self, orchestrator):
        """Test that A/B testing variant selection works."""
        if orchestrator.ab_testing:
            variant = await orchestrator.ab_testing.get_greeting_variant(
                conversation_id="test-conv-123",
                context={
                    "customer_age": 35,
                    "customer_segment": "professional",
                    "program_type": "PRIME"
                }
            )
            
            # Should return None or a valid variant structure
            if variant:
                assert 'style' in variant
                assert 'variant_id' in variant


@pytest.mark.asyncio
async def test_full_ml_pipeline_flow(orchestrator, customer_data, platform_info):
    """
    Integration test for the complete ML Pipeline flow.
    
    This test simulates a full conversation with all ML components active.
    """
    # Start conversation
    state = await orchestrator.start_conversation(
        customer_data=customer_data,
        platform_info=platform_info
    )
    
    conversation_id = state.conversation_id
    
    # Simulate a full conversation flow
    conversation_flow = [
        "Me interesa conocer más sobre sus programas",
        "¿Qué incluye el programa PRIME?",
        "¿Cuánto cuesta el programa completo?",
        "Parece caro, ¿hay opciones de pago?",
        "Me gusta lo que ofrecen, quiero empezar"
    ]
    
    # Process each message
    for i, message in enumerate(conversation_flow):
        result = await orchestrator.process_message(
            conversation_id=conversation_id,
            message_text=message
        )
        
        # Verify basic response structure
        assert 'response' in result
        assert 'conversation_id' in result
        assert 'emotional_state' in result
        assert 'sales_phase' in result
        
        # ML insights should be present
        if 'ml_insights' in result:
            assert isinstance(result['ml_insights'], dict)
        
        # Check that conversation progresses
        assert result['should_continue'] is True
    
    # End conversation successfully
    final_state = await orchestrator.end_conversation(
        conversation_id=conversation_id,
        end_reason="completed"
    )
    
    # Verify final state
    assert final_state.context.get('end_reason') == "completed"
    assert len(final_state.messages) > len(conversation_flow)  # Includes assistant responses


if __name__ == "__main__":
    # Run specific tests for development
    pytest.main([__file__, "-v", "-s"])