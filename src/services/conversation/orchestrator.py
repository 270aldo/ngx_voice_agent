"""
Conversation Orchestrator

Main orchestrator that combines all conversation functionality using mixins.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from io import BytesIO
import uuid

from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformContext, PlatformInfo, SourceType, PlatformType
from src.core.agent_factory import agent_factory, AgentInterface
from src.core.platform_config import PlatformConfigManager
from src.integrations.elevenlabs import voice_engine
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

# Import service dependencies
from src.services.intent_analysis_service import IntentAnalysisService
from src.services.enhanced_intent_analysis_service import EnhancedIntentAnalysisService
from src.services.qualification_service import LeadQualificationService
from src.services.human_transfer_service import HumanTransferService
from src.services.follow_up_service import FollowUpService
from src.services.personalization_service import PersonalizationService
from src.services.multi_voice_service import MultiVoiceService, SalesSection
from src.services.program_router import ProgramRouter
from src.services.advanced_empathy_engine import AdvancedEmpathyEngine
from src.services.ultra_empathy_greetings import get_greeting_engine, GreetingContext
from src.services.ultra_empathy_price_handler import get_price_handler, PriceObjectionContext
from src.config.empathy_config import EmpathyConfig
from src.services.conversation.response_cache import response_cache
from src.services.conversation.hybrid_model_selector import HybridModelSelector
from src.services.conversation.conversation_cache_router import ConversationCacheRouter
from src.services.response_precomputation_service import ResponsePrecomputationService
from src.services.cache.decision_cache import DecisionCacheLayer as DecisionCache

# Import predictive services for ML integration
from src.services.objection_prediction_service import ObjectionPredictionService
from src.services.needs_prediction_service import NeedsPredictionService
from src.services.conversion_prediction_service import ConversionPredictionService
from src.services.unified_decision_engine import UnifiedDecisionEngine
from src.services.predictive_model_service import PredictiveModelService
from src.services.nlp_integration_service import NLPIntegrationService

# Import ML Pipeline for continuous learning
try:
    from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
except ImportError:
    MLPipelineService = None
    # logger not defined yet, will log later

# Import Pattern Recognition Engine
try:
    from src.services.pattern_recognition_engine import pattern_recognition_engine
except ImportError:
    pattern_recognition_engine = None
    # logger not defined yet, will log later

# Import mixins
from .base import BaseConversationService
from .ml_tracking import MLTrackingMixin
from .tier_management import TierManagementMixin
from .emotional_processing import EmotionalProcessingMixin
from .sales_strategy import SalesStrategyMixin
from .ab_testing_mixin import ABTestingMixin
from src.services.compatibility_wrappers import ServiceCompatibilityMixin

logger = logging.getLogger(__name__)


class ConversationOrchestrator(
    BaseConversationService,
    MLTrackingMixin,
    TierManagementMixin,
    EmotionalProcessingMixin,
    SalesStrategyMixin,
    ABTestingMixin,
    ServiceCompatibilityMixin
):
    """
    Main conversation orchestrator that combines all functionality.
    
    This class integrates:
    - Base conversation management
    - ML tracking and adaptive learning
    - Tier detection and management
    - Emotional intelligence processing
    - Sales strategy and ROI calculations
    - A/B testing for continuous optimization
    - Pattern recognition for behavior analysis
    """
    
    def __init__(self, industry: str = 'salud', platform_context: Optional[PlatformContext] = None):
        """
        Initialize the conversation orchestrator.
        
        Args:
            industry: Industry for intent analysis customization
            platform_context: Platform context (optional)
        """
        # Initialize all parent classes
        BaseConversationService.__init__(self, industry)
        MLTrackingMixin.__init__(self)
        TierManagementMixin.__init__(self)
        EmotionalProcessingMixin.__init__(self)
        SalesStrategyMixin.__init__(self)
        ABTestingMixin.__init__(self)
        
        self.platform_context = platform_context
        
        # Initialize supporting services
        self.intent_analysis_service = IntentAnalysisService()
        self.enhanced_intent_service = EnhancedIntentAnalysisService(industry=industry)
        self.qualification_service = LeadQualificationService()
        self.human_transfer_service = HumanTransferService()
        self.follow_up_service = FollowUpService()
        self.personalization_service = PersonalizationService()
        self.multi_voice_service = MultiVoiceService()
        
        # Advanced empathy engine
        self.advanced_empathy_engine = AdvancedEmpathyEngine()
        
        # Program router for automatic detection
        self.program_router = ProgramRouter()
        
        # Initialize predictive services - set to None initially
        # They will be initialized in initialize() method to avoid circular dependencies
        self.objection_predictor = None
        self.needs_predictor = None
        self.conversion_predictor = None
        self.decision_engine = None
        
        # Initialize base predictive services needed by predictors
        self.predictive_model_service = None
        self.nlp_integration_service = None
        self.entity_recognition_service = None
        
        # ML enhanced services
        self.ml_prediction_service = None
        self.fallback_predictor = None
        
        # ML Pipeline for continuous learning
        self.ml_pipeline = None
        if MLPipelineService:
            try:
                self.ml_pipeline = MLPipelineService()
                logger.info("ML Pipeline Service initialized")
            except Exception as e:
                logger.warning(f"Could not initialize ML Pipeline: {e}")
        
        # Pattern Recognition Engine
        self.pattern_recognition = pattern_recognition_engine
        
        # Cache Router for ultra-fast responses (<0.5s)
        self.cache_router = None
        
        logger.info(f"ConversationOrchestrator initialized for industry: {industry}")
    
    async def initialize(self) -> None:
        """Initialize all async services."""
        if self._initialized:
            return
        
        try:
            # Initialize ML services
            self._init_ml_services()
            if self.adaptive_learning_service:
                await self.adaptive_learning_service.initialize()
            
            # Initialize predictive services
            await self._init_predictive_services()
            
            # Initialize other services
            self._init_tier_services()
            self._init_emotional_services()
            self._init_sales_services()
            
            # Initialize A/B testing
            await self._init_ab_testing()
            
            # Initialize ML Pipeline
            if self.ml_pipeline:
                try:
                    await self.ml_pipeline.initialize()
                    logger.info("ML Pipeline initialized successfully")
                except Exception as e:
                    logger.warning(f"ML Pipeline initialization warning: {e}")
            
            # Initialize Pattern Recognition
            if self.pattern_recognition:
                try:
                    await self.pattern_recognition.initialize()
                    logger.info("Pattern Recognition Engine initialized successfully")
                except Exception as e:
                    logger.warning(f"Pattern Recognition initialization warning: {e}")
            
            # Initialize Cache Router for ultra-fast responses (<0.5s)
            if self._cache_manager:
                try:
                    # Get Redis client from dependencies
                    from src.core.dependencies import get_redis_client
                    redis_client = await get_redis_client()
                    
                    # Initialize services needed for cache router
                    precompute_service = ResponsePrecomputationService(self._cache_manager)
                    decision_cache = DecisionCache(redis_client=redis_client, enable_l2=True)
                    
                    # Create and initialize cache router
                    self.cache_router = ConversationCacheRouter(
                        cache_manager=self._cache_manager,
                        precompute_service=precompute_service,
                        decision_cache=decision_cache
                    )
                    
                    # Pre-warm cache with common responses
                    cache_stats = await self.cache_router.warm_router_cache()
                    logger.info(f"Cache Router initialized with {cache_stats.get('total', 0)} pre-warmed responses")
                except Exception as e:
                    logger.warning(f"Could not initialize Cache Router: {e}")
                    self.cache_router = None
            
            self._initialized = True
            logger.info("ConversationOrchestrator fully initialized")
            
        except Exception as e:
            logger.error(f"Error initializing ConversationOrchestrator: {e}")
            raise
    
    async def start_conversation(
        self,
        customer_data: CustomerData,
        program_type: Optional[str] = None,
        platform_info: Optional[PlatformInfo] = None
    ) -> ConversationState:
        """
        Start a new conversation with comprehensive setup.
        
        Args:
            customer_data: Customer data
            program_type: Program type (optional, auto-detected if not provided)
            platform_info: Platform information
            
        Returns:
            ConversationState: Initial conversation state
            
        Raises:
            ValueError: If user is in cooldown
            RuntimeError: If agent creation fails
        """
        await self._ensure_initialized()
        
        try:
            # Check cooldown
            cooldown_status = await self.qualification_service._check_cooldown(str(customer_data.id))
            if cooldown_status['in_cooldown']:
                raise ValueError(
                    f"Solo se permite una llamada cada 48 horas. "
                    f"Disponible en {cooldown_status['hours_remaining']} horas"
                )
            
            # Auto-detect program if not specified
            if not program_type:
                program_type = await self._auto_detect_program(customer_data)
            
            # Create conversation state
            conversation_id = str(uuid.uuid4())
            state = ConversationState(
                conversation_id=conversation_id,
                customer_data=customer_data.model_dump() if hasattr(customer_data, 'model_dump') else customer_data.dict(),
                messages=[],
                context={},
                program_type=program_type,
                ml_tracking_enabled=True
            )
            
            # Register session
            await self._register_session(conversation_id, customer_data, platform_info)
            
            # Start ML tracking
            ml_config = await self._start_ml_conversation_tracking(
                conversation_id,
                customer_data.dict(),
                {"source": platform_info.source if platform_info else "web"}
            )
            state.experiment_assignments = ml_config.get("experiments_assigned", [])
            
            # NO CREAR AGENTE - usar OpenAI directamente
            self._current_agent = None
            
            # Generate initial greeting
            greeting = await self._generate_platform_greeting(
                customer_data, program_type, platform_info
            )
            
            # Add greeting message
            greeting_message = Message(
                role="assistant",
                content=greeting,
                timestamp=datetime.now().isoformat()
            )
            state.messages.append(greeting_message)
            
            # Save initial state
            await self._save_conversation_state(state)
            
            logger.info(f"Conversation started: {conversation_id} for program: {program_type}")
            return state
            
        except Exception as e:
            logger.error(f"Error starting conversation: {e}")
            raise
    
    async def process_message(
        self,
        conversation_id: str,
        message_text: str,
        audio_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Process a user message with full intelligence pipeline.
        
        Args:
            conversation_id: Conversation ID
            message_text: User message text
            audio_data: Optional audio data
            
        Returns:
            Dict with response and metadata
        """
        await self._ensure_initialized()
        
        try:
            # Get conversation state
            state = await self._get_conversation_state(conversation_id)
            if not state:
                raise ValueError(f"Conversation not found: {conversation_id}")
            
            # NO RESTAURAR AGENTE - usar OpenAI directamente
            # El sistema usa OpenAI directamente en _process_with_consultive_agent
            
            # Add user message
            user_message = Message(
                role="user",
                content=message_text,
                timestamp=datetime.now().isoformat()
            )
            state.messages.append(user_message)
            
            # SIMPLIFIED FLOW: Consolidate all analysis
            
            # 1. Quick context analysis (no external calls)
            context_analysis = self._quick_context_analysis(message_text, state)
            
            # 2. Run predictive services (if available)
            predictive_insights = await self._run_predictive_analysis(
                conversation_id, state.messages, state.customer_data
            )
            
            # 3. Build consolidated context for single GPT call
            consultive_context = {
                "emotional_state": context_analysis["primary_emotion"],
                "has_price_concern": context_analysis["has_price_objection"],
                "urgency_level": context_analysis["urgency_level"],
                "conversation_phase": state.phase,
                "message_count": len(state.messages),
                "predictive_insights": predictive_insights
            }
            
            # 4. Check for ROI calculation need
            roi_data = None
            if any(word in message_text.lower() for word in ["precio", "costo", "inversión", "valor", "roi"]):
                roi_data = await self._calculate_personalized_roi(state, message_text)
                if roi_data:
                    consultive_context["roi_calculation"] = roi_data
                    # Add ROI to predictive insights for API response
                    if predictive_insights:
                        predictive_insights["roi_calculation"] = roi_data
            
            # 4. Single response generation with Cache Router for ultra-fast responses
            if self.cache_router:
                try:
                    # Build cache context for optimal performance
                    cache_context = self._build_cache_context(state, consultive_context)
                    
                    # Use cache router for <0.5s response times
                    response_data, cache_metrics = await self.cache_router.route_request(
                        message=message_text,
                        context=cache_context,
                        compute_callback=lambda msg, ctx: self._process_with_consultive_agent(
                            msg, state, consultive_context
                        )
                    )
                    
                    # Extract response text
                    if isinstance(response_data, dict):
                        final_response = response_data.get("response", str(response_data))
                    else:
                        final_response = str(response_data)
                    
                    # Log performance metrics
                    if cache_metrics.get('response_time_ms', 0) < 500:
                        logger.info(f"Fast response delivered in {cache_metrics['response_time_ms']}ms from {cache_metrics['cache_level']} cache")
                    else:
                        logger.warning(f"Slow response: {cache_metrics['response_time_ms']}ms from {cache_metrics['cache_level']} cache")
                    
                    # Add cache metrics to predictive insights for monitoring
                    if predictive_insights:
                        predictive_insights["cache_metrics"] = cache_metrics
                        
                except Exception as e:
                    logger.error(f"Cache router error: {e}, falling back to direct processing")
                    # Fallback to original method
                    final_response = await self._process_with_consultive_agent(
                        message_text, state, consultive_context
                    )
            else:
                # Fallback to original method if cache router not available
                final_response = await self._process_with_consultive_agent(
                    message_text, state, consultive_context
                )
            
            # 5. Check for price objections and handle with ultra empathy
            if context_analysis["has_price_objection"]:
                # Check for A/B test variant for price objection handling
                price_ab_variant = None
                if self.ab_testing:
                    price_ab_variant = await self._apply_price_objection_ab_test(
                        conversation_id=conversation_id,
                        objection_text=message_text,
                        tier_detected=state.context.get("tier_detected", "pro"),
                        emotional_state=context_analysis["primary_emotion"]
                    )
                
                price_handler = get_price_handler()
                price_context = PriceObjectionContext(
                    objection_text=message_text,
                    customer_name=state.customer_data.get("name", ""),
                    detected_emotion=context_analysis["primary_emotion"],
                    tier_mentioned=state.context.get("tier_detected", "pro"),
                    conversation_phase=state.phase or "exploration",
                    previous_objections=[]
                )
                
                # Apply A/B variant approach if available
                if price_ab_variant:
                    if price_ab_variant.get("approach") == "value_demonstration":
                        price_context.focus_on_roi = True
                    elif price_ab_variant.get("approach") == "payment_options":
                        price_context.emphasize_flexibility = True
                    elif price_ab_variant.get("approach") == "social_proof":
                        price_context.use_testimonials = True
                
                price_response = price_handler.generate_ultra_empathetic_response(price_context)
                
                # Override with ultra-empathetic price response
                final_response = price_response["response"]
                if price_response.get("follow_up_question"):
                    final_response += f"\n\n{price_response['follow_up_question']}"
                
                # Enhance with A/B variant if available
                if price_ab_variant:
                    final_response = self._enhance_response_with_ab_variant(final_response, price_ab_variant)
                    # Track that we handled a price objection
                    state.context["price_objection_handled"] = True
                    state.context["price_ab_variant"] = price_ab_variant.get("variant_id")
            
            # 6. Generate Audio if needed
            audio_response = None
            if self.multi_voice_service:
                sales_section = self._determine_sales_section(state)
                audio_response = await self._generate_adaptive_audio(
                    final_response, sales_section, state.conversation_id
                )
            
            # 7. Add assistant message
            assistant_message = Message(
                role="assistant",
                content=final_response,
                timestamp=datetime.now().isoformat()
            )
            state.messages.append(assistant_message)
            
            # 8. Update conversation phase
            self._update_conversation_phase(state, message_text, final_response)
            
            # 9. Track ML Pipeline events and Pattern Recognition
            if self.ml_pipeline:
                try:
                    # Track message exchange event
                    await self.ml_pipeline.event_tracker.track_event(
                        event_type="message_exchange",
                        event_data={
                            "conversation_id": state.conversation_id,
                            "message_type": "user_assistant",
                            "phase": state.phase,
                            "emotion_detected": context_analysis.get("primary_emotion"),
                            "intent": context_analysis.get("intent", "unknown"),
                            "tier_detected": state.tier_detected,
                            "price_mentioned": any(word in message_text.lower() for word in ["precio", "costo", "inversión"]),
                            "price_objection_handled": state.context.get("price_objection_handled", False)
                        }
                    )
                    
                    # Process conversation predictions through ML Pipeline
                    message_dicts = [
                        {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                        for msg in state.messages
                    ]
                    
                    pipeline_result = await self.ml_pipeline.process_conversation_predictions(
                        conversation_id=state.conversation_id,
                        messages=message_dicts,
                        context={
                            "customer_data": state.customer_data,
                            "phase": state.phase,
                            "tier_detected": state.tier_detected,
                            "emotional_state": context_analysis.get("primary_emotion"),
                            "platform": "web"
                        },
                        predictions=predictive_insights
                    )
                    
                    # Update predictive insights with ML Pipeline results
                    if pipeline_result and "predictions" in pipeline_result:
                        predictive_insights.update(pipeline_result["predictions"])
                        # Add A/B test variants to state
                        if "ab_variants" in pipeline_result:
                            state.context["ab_variants"] = pipeline_result["ab_variants"]
                    
                except Exception as e:
                    logger.warning(f"ML Pipeline event tracking failed: {e}")
                
                # Track pattern recognition separately
                if self.pattern_recognition:
                    try:
                        patterns = await self.pattern_recognition.detect_patterns(
                            conversation_id=state.conversation_id,
                            messages=message_dicts,
                            context={
                                "customer_data": state.customer_data,
                                "phase": state.phase,
                                "emotional_state": context_analysis.get("primary_emotion"),
                                "tier_detected": state.tier_detected
                            }
                        )
                        
                        if patterns:
                            # Track patterns through ML Pipeline
                            await self.ml_pipeline.event_tracker.track_event(
                                event_type="pattern_detected",
                                event_data={
                                    "conversation_id": state.conversation_id,
                                    "patterns": patterns,
                                    "confidence_scores": {p["type"]: p["confidence"] for p in patterns}
                                }
                            )
                            
                            # Store patterns in state for use in response generation
                            state.context["detected_patterns"] = patterns
                            
                    except Exception as e:
                        logger.warning(f"Pattern recognition failed: {e}")
            
            # 10. Update ML metrics (simplified)
            await self._update_ml_conversation_metrics(
                conversation_id,
                {
                    "emotional_state": context_analysis["primary_emotion"],
                    "tier_detected": state.context.get("tier_detected", "unknown"),
                    "engagement_level": self._assess_engagement_level(state),
                    "sales_phase": state.phase,
                    "objections_detected": 1 if context_analysis["has_price_objection"] else 0
                }
            )
            
            # 10. Save updated state
            await self._save_conversation_state(state)
            
            # 11. Simple check if conversation should continue
            should_continue = len(state.messages) < 50  # Simple limit
            
            return {
                "response": final_response,
                "audio": audio_response,
                "conversation_id": conversation_id,
                "emotional_state": {"primary_emotion": context_analysis["primary_emotion"]},
                "sales_phase": state.phase,
                "engagement_level": self._assess_engagement_level(state),
                "ml_insights": predictive_insights,
                "roi_calculation": roi_data,
                "should_continue": should_continue,
                "metadata": {
                    "message_count": len(state.messages),
                    "has_price_concern": context_analysis["has_price_objection"],
                    "urgency_detected": context_analysis["urgency_level"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    async def end_conversation(
        self, 
        conversation_id: str, 
        end_reason: str = "completed"
    ) -> ConversationState:
        """
        End conversation with ML outcome recording.
        
        Args:
            conversation_id: Conversation ID
            end_reason: Reason for ending
            
        Returns:
            Final conversation state
        """
        await self._ensure_initialized()
        
        try:
            state = await self._get_conversation_state(conversation_id)
            if not state:
                raise ValueError(f"Conversation not found: {conversation_id}")
            
            # Calculate outcome metrics
            outcome_metrics = {
                "final_tier": state.tier_detected,
                "message_count": len(state.messages),
                "duration_seconds": self._calculate_conversation_duration(state) * 60,
                "engagement_final": self._assess_engagement_level(state),
                "conversion_value": state.context.get("conversion_value", 0),
                "tier_selected": state.context.get("tier_selected", None),
                "price_objection_overcome": state.context.get("price_objection_handled", False),
                "satisfaction_score": self._estimate_satisfaction_score(state),
                "engagement_score": self._assess_engagement_level(state)
            }
            
            # Record ML outcome
            await self._record_conversation_outcome_for_ml(
                conversation_id,
                end_reason,
                outcome_metrics
            )
            
            # Record ML Pipeline outcome and trigger feedback loop
            if self.ml_pipeline:
                try:
                    # Record conversation outcome
                    await self.ml_pipeline.record_conversation_outcome(
                        conversation_id=conversation_id,
                        outcome=end_reason,
                        metrics=outcome_metrics
                    )
                    
                    # Include A/B test results in outcome metrics if available
                    if state.context.get("ab_variants"):
                        outcome_metrics["ab_variants"] = state.context["ab_variants"]
                    
                    logger.info(f"ML Pipeline outcome recorded for {conversation_id}")
                    
                    # Note: Feedback loop runs automatically via background tasks
                    
                except Exception as e:
                    logger.warning(f"Failed to record ML Pipeline outcome: {e}")
            
            # Record A/B testing outcome separately if needed
            if self.ab_testing and state.context.get("ab_variants"):
                try:
                    await self._record_ab_testing_outcome(
                        conversation_id=conversation_id,
                        outcome=end_reason,
                        metrics=outcome_metrics
                    )
                except Exception as e:
                    logger.warning(f"Failed to record A/B testing outcome: {e}")
            
            # Generate closing message
            closing_message = self._generate_closing_message(end_reason)
            
            if closing_message:
                final_message = Message(
                    role="assistant",
                    content=closing_message,
                    timestamp=datetime.now().isoformat()
                )
                state.messages.append(final_message)
            
            # Update state
            state.context["end_reason"] = end_reason
            state.context["ended_at"] = datetime.now().isoformat()
            
            # Save final state
            await self._save_conversation_state(state)
            
            logger.info(f"Conversation ended: {conversation_id} - Reason: {end_reason}")
            return state
            
        except Exception as e:
            logger.error(f"Error ending conversation: {e}")
            raise
    
    async def _auto_detect_program(self, customer_data: CustomerData) -> str:
        """Auto-detect program type based on customer data."""
        try:
            program_decision = await self.program_router.determine_program(
                customer_data=customer_data.dict(),
                initial_message="",
                conversation_context=None
            )
            return program_decision["recommended_program"]
        except Exception as e:
            logger.warning(f"Program auto-detection failed: {e}, defaulting to LONGEVITY")
            return "LONGEVITY"
    
    async def _register_session(
        self,
        conversation_id: str,
        customer_data: CustomerData,
        platform_info: Optional[PlatformInfo]
    ) -> None:
        """Register conversation session."""
        try:
            session_data = {
                "conversation_id": conversation_id,
                "customer_id": customer_data.id,
                "platform_source": platform_info.source if platform_info else "web",
                "started_at": datetime.now().isoformat(),
                "status": "active"
            }
            
            await supabase_client.insert(
                table="conversation_sessions",
                data=session_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to register session: {e}")
    
    async def _generate_platform_greeting(
        self,
        customer_data: CustomerData,
        program_type: str,
        platform_info: Optional[PlatformInfo]
    ) -> str:
        """Generate platform-specific greeting using ultra empathy system with A/B testing."""
        # Get conversation ID for A/B testing (use a temporary one for greeting)
        temp_conversation_id = getattr(customer_data, 'conversation_id', str(uuid.uuid4()))
        
        # Check for A/B test variant
        ab_variant = None
        if self.ab_testing:
            customer_dict = customer_data.model_dump() if hasattr(customer_data, 'model_dump') else customer_data.dict()
            ab_variant = await self._apply_greeting_ab_test(
                conversation_id=temp_conversation_id,
                customer_data=customer_dict,
                program_type=program_type
            )
        
        # Usar el nuevo Ultra Empathy Greeting Engine para greetings 10/10
        greeting_engine = get_greeting_engine()
        
        # Preparar contexto
        greeting_context = GreetingContext(
            customer_name=customer_data.name,
            age=getattr(customer_data, 'age', None),
            initial_message=getattr(customer_data, 'initial_message', None),
            platform=platform_info.source if platform_info else "web"
        )
        
        # Apply A/B test variant parameters if available
        if ab_variant:
            # Modify greeting context based on variant
            if ab_variant.get('style') == 'warm_personal':
                greeting_context.style = 'warm'
            elif ab_variant.get('style') == 'motivational_inspiring':
                greeting_context.style = 'motivational'
            elif ab_variant.get('style') == 'consultive_professional':
                greeting_context.style = 'consultive'
        
        # Generar greeting ultra-empático
        ultra_greeting = greeting_engine.generate_ultra_empathetic_greeting(greeting_context)
        
        # Enhance with A/B variant if available
        if ab_variant:
            ultra_greeting = self._enhance_response_with_ab_variant(ultra_greeting, ab_variant)
        
        # Si el greeting es muy corto, usar el sistema consultivo como fallback
        if len(ultra_greeting) < 100:
            # Fallback al sistema anterior
            temp_state = ConversationState(
                conversation_id="temp_greeting",
                customer_data=customer_data.model_dump() if hasattr(customer_data, 'model_dump') else customer_data.dict(),
                messages=[],
                context={"phase": "greeting", "program_type": program_type},
                program_type=program_type
            )
            
            initial_message = customer_data.initial_message if hasattr(customer_data, 'initial_message') and customer_data.initial_message else f"Hola, soy {customer_data.name}. Quiero información sobre sus programas."
            
            ultra_greeting = await self._process_with_consultive_agent(
                initial_message,
                temp_state,
                {
                    "is_greeting": True,
                    "platform": platform_info.source if platform_info else "web",
                    "customer_name": customer_data.name,
                    "customer_age": getattr(customer_data, 'age', None),
                    "program_type": program_type
                }
            )
        
        # Agregar emoji de plataforma si corresponde
        if platform_info and platform_info.source == "mobile":
            return f"📱 {ultra_greeting}"
        elif platform_info and platform_info.source == "whatsapp":
            return f"💬 {ultra_greeting}"
        
        return ultra_greeting
    
    def _build_cache_context(self, state: ConversationState, consultive_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build optimized context for cache routing.
        
        Args:
            state: Current conversation state
            consultive_context: Consultive agent context
            
        Returns:
            Cache-friendly context dictionary
        """
        # Extract customer data safely
        customer_data = state.customer_data
        if isinstance(customer_data, dict):
            customer_type = customer_data.get('profession', 'general')
            customer_name = customer_data.get('name', '')
        else:
            customer_type = getattr(customer_data, 'profession', 'general')
            customer_name = getattr(customer_data, 'name', '')
        
        # Build comprehensive cache context
        cache_context = {
            'conversation_id': state.conversation_id,
            'customer_type': customer_type,
            'customer_name': customer_name,
            'tier': state.context.get('tier_detected', 'standard'),
            'conversation_stage': state.phase or 'exploration',
            'emotional_state': consultive_context.get('emotional_state', 'neutral'),
            'has_price_concern': consultive_context.get('has_price_concern', False),
            'has_price_objection': consultive_context.get('has_price_objection', False),
            'message_count': len(state.messages),
            'interests': state.context.get('identified_needs', []),
            'objection_type': consultive_context.get('objection_type'),
            'program_type': state.program_type,
            'urgency_level': consultive_context.get('urgency_level', 'normal'),
            'engagement_level': state.context.get('engagement_level', 'medium')
        }
        
        # Add ML insights if available
        if 'ml_insights' in consultive_context:
            cache_context['predicted_need'] = consultive_context['ml_insights'].get('primary_need')
            cache_context['conversion_probability'] = consultive_context['ml_insights'].get('conversion_probability', 0.5)
        
        return cache_context
    
    async def _process_with_consultive_agent(
        self,
        message_text: str,
        state: ConversationState,
        consultive_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process message with consultative AI agent using OpenAI directly."""
        try:
            # Check cache first
            cache_key_context = {
                "emotional_state": consultive_context.get("emotional_state", "neutral") if consultive_context else "neutral",
                "has_price_concern": consultive_context.get("has_price_concern", False) if consultive_context else False,
                "conversation_phase": state.phase or "exploration"
            }
            
            cached_response = response_cache.get(message_text, cache_key_context)
            if cached_response:
                return cached_response
            # USAR OPENAI DIRECTAMENTE CON TODO EL SISTEMA DE NGX
            from src.integrations.openai_client import get_openai_client
            from src.conversation.prompts.optimized_prompts import OPTIMIZED_SYSTEM_PROMPT
            
            openai_client = get_openai_client()
            
            # Construir el prompt con TODO el contexto de NGX
            customer_age = None
            if consultive_context and consultive_context.get('customer_age'):
                customer_age = consultive_context['customer_age']
            elif hasattr(state, 'customer_data'):
                if isinstance(state.customer_data, dict):
                    customer_age = state.customer_data.get('age')
                else:
                    customer_age = getattr(state.customer_data, 'age', None)
            
            age_range = "30-45"  # Default
            if customer_age:
                if customer_age < 35:
                    age_range = "25-35"
                elif customer_age < 45:
                    age_range = "35-45"
                elif customer_age < 55:
                    age_range = "45-55"
                else:
                    age_range = "55+"
            
            system_prompt = OPTIMIZED_SYSTEM_PROMPT.format(
                age_range=age_range,
                initial_interests=['optimización', 'rendimiento'] if state.program_type == "PRIME" else ['bienestar', 'longevidad']
            )
            
            # Si hay cálculo de ROI, agregarlo al prompt
            if consultive_context and consultive_context.get('roi_calculation'):
                roi = consultive_context['roi_calculation']
                system_prompt += f"\n\nROI CALCULADO PARA ESTE CLIENTE:\n"
                system_prompt += f"- ROI Proyectado: {roi.get('projected_roi_percentage', 0):.0f}%\n"
                system_prompt += f"- Valor Anual: ${roi.get('annual_value', 0):,.0f}\n"
                system_prompt += f"- Recuperación en: {roi.get('payback_period_months', 0):.1f} meses\n"
                if roi.get('key_insights'):
                    system_prompt += "- Insights clave:\n"
                    for insight in roi['key_insights'][:3]:
                        system_prompt += f"  • {insight}\n"
                system_prompt += "\nUSA ESTOS DATOS PARA RESPONDER DE MANERA PERSONALIZADA Y CONVINCENTE."
            
            # Si hay insights predictivos, agregarlos al prompt
            if consultive_context and consultive_context.get('predictive_insights'):
                insights = consultive_context['predictive_insights']
                
                # Add predicted objections
                if insights.get('objections_predicted'):
                    system_prompt += "\n\nOBJECIONES PREDICHAS:\n"
                    for obj in insights['objections_predicted'][:2]:  # Top 2 objections
                        system_prompt += f"- {obj['type']} (confianza: {obj['confidence']:.0%})\n"
                        if obj.get('suggested_responses'):
                            system_prompt += f"  Sugerencia: {obj['suggested_responses'][0]}\n"
                
                # Add detected needs
                if insights.get('needs_detected'):
                    system_prompt += "\n\nNECESIDADES DETECTADAS:\n"
                    for need in insights['needs_detected'][:3]:  # Top 3 needs
                        system_prompt += f"- {need.get('type', 'Unknown')}: {need.get('description', '')}\n"
                
                # Add conversion probability
                if insights.get('conversion_probability', 0) > 0:
                    system_prompt += f"\n\nPROBABILIDAD DE CONVERSIÓN: {insights['conversion_probability']:.0%}\n"
                
                # Add recommended actions
                if insights.get('recommended_actions'):
                    system_prompt += "\n\nACCIONES RECOMENDADAS:\n"
                    for action in insights['recommended_actions'][:2]:  # Top 2 actions
                        system_prompt += f"- {action}\n"
                
                system_prompt += "\nUSA ESTOS INSIGHTS PREDICTIVOS PARA PERSONALIZAR TU RESPUESTA."
            
            # Si es un greeting, agregar instrucciones especiales
            if consultive_context and consultive_context.get('is_greeting'):
                customer_name = consultive_context.get('customer_name', '')
                system_prompt += f"\n\nIMPORTANTE: Esta es tu PRIMERA interacción con {customer_name}. Genera un saludo ULTRA EMPÁTICO que:\n"
                system_prompt += "- Sea cálido, personal y genuino (NO genérico)\n"
                system_prompt += "- Muestre interés real en la persona\n"
                system_prompt += "- NO menciones precios ni paquetes en el saludo\n"
                system_prompt += "- Haz una pregunta abierta que invite a compartir\n"
                system_prompt += "- Usa el nombre de la persona naturalmente\n"
                system_prompt += "- Transmite calidez humana desde el primer momento"
            
            # Incluir historial de conversación
            messages = [{"role": "system", "content": system_prompt}]
            for msg in state.messages[-5:]:  # Últimos 5 mensajes para contexto
                messages.append({"role": msg.role, "content": msg.content})
            messages.append({"role": "user", "content": message_text})
            
            # Determinar contexto para parámetros de empatía
            empathy_context = "general"
            if consultive_context and consultive_context.get('is_greeting'):
                empathy_context = "greeting"
            elif "precio" in message_text.lower() or "costo" in message_text.lower():
                empathy_context = "price_objection"
            elif any(word in message_text.lower() for word in ["cansado", "agotado", "triste", "frustrado"]):
                empathy_context = "emotional_moment"
            
            # Select optimal model based on context
            model_selection = HybridModelSelector.select_model(
                message_text,
                cache_key_context,
                len(state.messages)
            )
            
            # Get base parameters and override with model-specific ones
            model_params = EmpathyConfig.get_context_params(empathy_context)
            model_params.update(model_selection["params"])
            model_params["model"] = model_selection["model"]
            
            # Log model selection for monitoring
            logger.info(f"Selected model: {model_selection['model']} (reason: {model_selection['reason']})")
            
            # Mejorar system prompt con instrucciones de empatía
            enhanced_system_prompt = EmpathyConfig.enhance_with_empathy_instructions(
                system_prompt, empathy_context
            )
            messages[0]["content"] = enhanced_system_prompt
            
            # Llamar a OpenAI con parámetros optimizados
            response_dict = await openai_client.create_chat_completion(
                messages=messages,
                **model_params
            )
            
            # Extraer el contenido de la respuesta
            if response_dict and response_dict.get('choices') and len(response_dict['choices']) > 0:
                response_content = response_dict['choices'][0]['message']['content']
                
                # Cache the response for future use
                response_cache.set(message_text, cache_key_context, response_content)
                
                return response_content
            else:
                return "Gracias por compartir eso conmigo. ¿Qué te gustaría saber sobre nuestros programas?"
                
        except Exception as e:
            logger.error(f"Error in consultative agent processing: {e}")
            return "Gracias por compartir eso conmigo. ¿Qué te gustaría saber sobre nuestros programas?"
    
    async def _merge_response_strategies(
        self,
        base_response: str,
        empathic_data: Dict[str, Any],
        sales_context: Dict[str, Any]
    ) -> str:
        """Merge different response strategies."""
        # Check if empathic response is a fallback (contains the user's message)
        empathic_response = empathic_data.get("empathic_response", "")
        
        # If empathic response contains "Entiendo tu punto" (fallback marker) or is too short, use base response
        if "Entiendo tu punto" in empathic_response or len(empathic_response) < 50:
            response = base_response
        elif empathic_response:
            response = empathic_response
        else:
            response = base_response
        
        # Add sales elements if appropriate
        sales_phase = sales_context.get("sales_phase", "discovery")
        if sales_phase in ["negotiation", "closing"]:
            urgency_factors = sales_context.get("urgency_factors", {}).get("factors", [])
            if urgency_factors:
                response += f"\\n\\n{urgency_factors[0]}"
        
        return response
    
    async def _merge_objection_handling(
        self,
        base_response: str,
        objection_response: Dict[str, Any]
    ) -> str:
        """Merge objection handling into response."""
        if objection_response.get("response"):
            # Prepend objection handling
            return f"{objection_response['response']}\\n\\n{base_response}"
        
        return base_response
    
    async def _analyze_intent(self, state: ConversationState, conversation_id: str) -> None:
        """Analyze intent for workflow triggers."""
        try:
            last_message = state.messages[-1].content if state.messages else ""
            
            # Enhanced intent analysis
            intent_result = await self.enhanced_intent_service.analyze_intent(
                message=last_message,
                context={
                    "conversation_history": [msg.content for msg in state.messages[-5:]],
                    "customer_data": state.customer_data,
                    "program_type": state.program_type
                }
            )
            
            state.intent = intent_result.get("primary_intent")
            state.context["intent_confidence"] = intent_result.get("confidence", 0.0)
            
        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
    
    async def _check_human_transfer(
        self,
        message_text: str,
        state: ConversationState,
        emotional_analysis: Dict[str, Any]
    ) -> bool:
        """Check if human transfer is needed."""
        try:
            transfer_needed = await self.human_transfer_service.should_transfer(
                message_text=message_text,
                conversation_context={
                    "messages": len(state.messages),
                    "emotional_state": emotional_analysis.get("primary_emotion"),
                    "tier": state.tier_detected,
                    "program": state.program_type
                }
            )
            
            if transfer_needed:
                state.human_transfer_needed = True
                logger.info(f"Human transfer flagged for conversation: {state.conversation_id}")
            
            return transfer_needed
            
        except Exception as e:
            logger.error(f"Error checking human transfer: {e}")
            return False
    
    def _determine_sales_section(self, state: ConversationState) -> SalesSection:
        """Determine current sales section for voice adaptation."""
        message_count = len(state.messages)
        
        if message_count <= 3:
            return SalesSection.OPENING
        elif message_count <= 8:
            return SalesSection.DISCOVERY
        elif message_count <= 15:
            return SalesSection.PRESENTATION
        elif message_count <= 25:
            return SalesSection.OBJECTION_HANDLING
        else:
            return SalesSection.CLOSING
    
    async def _generate_adaptive_audio(
        self,
        text: str,
        sales_section: SalesSection,
        conversation_id: str
    ) -> Optional[BytesIO]:
        """Generate adaptive audio response."""
        try:
            return await self.multi_voice_service.generate_adaptive_voice(
                text=text,
                sales_section=sales_section,
                conversation_id=conversation_id
            )
        except Exception as e:
            logger.error(f"Error generating adaptive audio: {e}")
            return None
    
    def _generate_closing_message(self, end_reason: str) -> str:
        """Generate appropriate closing message."""
        closing_messages = {
            "completed": "¡Excelente! Ha sido un placer ayudarte. ¡Nos vemos pronto en tu transformación! 🌟",
            "human_transfer": "Te conectaré con uno de nuestros especialistas humanos para continuar. ¡Gracias por tu paciencia!",
            "timeout": "Parece que necesitas tiempo para pensar. ¡Estaré aquí cuando estés listo para continuar!",
            "abandoned": "Gracias por tu tiempo. Si cambias de opinión, estaré aquí para ayudarte. ¡Que tengas un excelente día!",
            "qualified": "Perfecto, has calificado para nuestro programa. ¡Te contactaremos pronto con los siguientes pasos!"
        }
        
        return closing_messages.get(end_reason, "¡Gracias por la conversación! 👋")
    
    def set_platform_context(self, platform_context: PlatformContext) -> None:
        """Set platform context."""
        self.platform_context = platform_context
    
    def get_platform_context(self) -> Optional[PlatformContext]:
        """Get platform context."""
        return self.platform_context
    
    def _quick_context_analysis(self, message_text: str, state: ConversationState) -> Dict[str, Any]:
        """
        Quick context analysis without external service calls.
        Analyzes message for emotional signals, objections, and urgency.
        """
        text_lower = message_text.lower()
        
        # Detect price objection
        price_keywords = ["precio", "costo", "caro", "dinero", "pagar", "inversión", "presupuesto", "cuánto", "vale"]
        has_price_objection = any(keyword in text_lower for keyword in price_keywords)
        
        # Detect primary emotion
        emotion_keywords = {
            "frustrated": ["frustrado", "cansado", "agotado", "harto", "estresado", "molesto"],
            "excited": ["emocionado", "entusiasmado", "motivado", "listo", "decidido", "genial"],
            "skeptical": ["dudo", "no creo", "escéptico", "no estoy seguro", "desconfío", "no sé"],
            "anxious": ["preocupado", "ansioso", "nervioso", "miedo", "temor", "inquieto"],
            "hopeful": ["esperanza", "espero", "ojalá", "me gustaría", "quisiera", "sería bueno"]
        }
        
        primary_emotion = "neutral"
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                primary_emotion = emotion
                break
        
        # Detect urgency level
        urgency_keywords = ["urgente", "ya", "ahora", "rápido", "pronto", "inmediato", "hoy", "mañana"]
        urgency_level = "high" if any(keyword in text_lower for keyword in urgency_keywords) else "normal"
        
        return {
            "has_price_objection": has_price_objection,
            "primary_emotion": primary_emotion,
            "urgency_level": urgency_level,
            "message_length": len(message_text),
            "conversation_length": len(state.messages)
        }
    
    def _update_conversation_phase(self, state: ConversationState, message: str, response: str) -> None:
        """
        Update conversation phase based on content and progress.
        """
        message_count = len(state.messages)
        
        # Simple phase detection based on conversation flow
        if message_count <= 2:
            state.phase = "greeting"
        elif any(word in message.lower() for word in ["precio", "costo", "caro", "vale"]):
            state.phase = "objection_handling"
        elif any(word in response.lower() for word in ["empezar", "comenzar", "inscribir", "registrar"]):
            state.phase = "closing"
        elif message_count > 15:
            state.phase = "negotiation"
        elif message_count > 8:
            state.phase = "presentation"
        else:
            state.phase = "exploration"
    
    async def _init_predictive_services(self) -> None:
        """
        Initialize predictive services with proper dependencies.
        This is done asynchronously to handle any initialization requirements.
        """
        try:
            # Import ML enhanced services
            from src.services.fallback_predictor import FallbackPredictor
            from src.services.training.ml_prediction_service import MLPredictionService
            
            # Initialize fallback predictor first (always available)
            self.fallback_predictor = FallbackPredictor()
            logger.info("FallbackPredictor initialized")
            
            # Try to initialize ML prediction service
            try:
                self.ml_prediction_service = MLPredictionService()
                logger.info("MLPredictionService initialized successfully")
            except Exception as e:
                logger.warning(f"MLPredictionService initialization failed: {e}. Using fallback only.")
                self.ml_prediction_service = None
            
            # Initialize ML Pipeline for continuous learning
            if MLPipelineService:
                try:
                    self.ml_pipeline = MLPipelineService()
                    await self.ml_pipeline.initialize()
                    logger.info("ML Pipeline initialized successfully")
                except Exception as e:
                    logger.warning(f"ML Pipeline initialization failed: {e}")
                    self.ml_pipeline = None
            
            # Initialize Pattern Recognition Engine
            if self.pattern_engine:
                try:
                    await self.pattern_engine.initialize()
                    logger.info("Pattern Recognition Engine initialized successfully")
                except Exception as e:
                    logger.warning(f"Pattern Recognition Engine initialization failed: {e}")
                    self.pattern_engine = None
            
            # Import required services for legacy predictors
            from src.services.predictive_model_service import PredictiveModelService
            from src.services.nlp_integration_service import NLPIntegrationService
            from src.services.entity_recognition_service import EntityRecognitionService
            
            # Initialize base services first
            if not self.predictive_model_service:
                self.predictive_model_service = PredictiveModelService(supabase_client)
                logger.info("PredictiveModelService initialized")
            
            if not self.nlp_integration_service:
                self.nlp_integration_service = NLPIntegrationService()
                logger.info("NLPIntegrationService initialized")
            
            if not self.entity_recognition_service:
                self.entity_recognition_service = EntityRecognitionService()
                logger.info("EntityRecognitionService initialized")
            
            # Now initialize predictive services with dependencies
            if not self.objection_predictor:
                self.objection_predictor = ObjectionPredictionService(
                    supabase_client=supabase_client,
                    predictive_model_service=self.predictive_model_service,
                    nlp_integration_service=self.nlp_integration_service
                )
                await self.objection_predictor.initialize()
                logger.info("ObjectionPredictionService initialized")
            
            if not self.needs_predictor:
                self.needs_predictor = NeedsPredictionService(
                    supabase_client=supabase_client,
                    predictive_model_service=self.predictive_model_service,
                    nlp_integration_service=self.nlp_integration_service,
                    entity_recognition_service=self.entity_recognition_service
                )
                await self.needs_predictor.initialize()
                logger.info("NeedsPredictionService initialized")
            
            if not self.conversion_predictor:
                self.conversion_predictor = ConversionPredictionService(
                    supabase_client=supabase_client,
                    predictive_model_service=self.predictive_model_service,
                    nlp_integration_service=self.nlp_integration_service
                )
                await self.conversion_predictor.initialize()
                logger.info("ConversionPredictionService initialized")
            
            if not self.decision_engine and self.objection_predictor and self.needs_predictor and self.conversion_predictor:
                self.decision_engine = UnifiedDecisionEngine(
                    supabase=supabase_client,
                    predictive_model_service=self.predictive_model_service,
                    nlp_integration_service=self.nlp_integration_service,
                    objection_prediction_service=self.objection_predictor,
                    needs_prediction_service=self.needs_predictor,
                    conversion_prediction_service=self.conversion_predictor
                )
                await self.decision_engine.initialize()
                logger.info("UnifiedDecisionEngine initialized")
            
            logger.info("All predictive services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing predictive services: {e}")
            # Don't raise - allow system to work without predictive services
            logger.warning("System will continue without predictive services")
    
    async def _run_predictive_analysis(
        self,
        conversation_id: str,
        messages: List[Message],
        customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run all predictive services and gather insights.
        Now enhanced with ML predictions and fallback support.
        
        Args:
            conversation_id: Conversation ID
            messages: Conversation messages
            customer_data: Customer data
            
        Returns:
            Dict with predictive insights
        """
        insights = {
            "objections_predicted": [],
            "needs_detected": [],
            "conversion_probability": 0.0,
            "recommended_actions": []
        }
        
        try:
            # Convert messages to dict format for services
            message_dicts = [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                for msg in messages
            ]
            
            # Try ML prediction service first
            if self.ml_prediction_service:
                try:
                    # Use ML predictions
                    objection_result = await self.ml_prediction_service.predict_objections(message_dicts)
                    if objection_result:
                        insights["objections_predicted"] = objection_result
                    
                    needs_result = await self.ml_prediction_service.predict_needs(message_dicts)
                    if needs_result:
                        insights["needs_detected"] = needs_result
                    
                    conversion_result = await self.ml_prediction_service.predict_conversion(message_dicts)
                    if conversion_result:
                        insights["conversion_probability"] = conversion_result.get("probability", 0.0)
                        insights["recommended_actions"] = conversion_result.get("recommended_actions", [])
                    
                    logger.info(f"ML predictions successful for {conversation_id}")
                    
                    # Send predictions to ML Pipeline for tracking
                    if self.ml_pipeline:
                        try:
                            await self.ml_pipeline.track_prediction(
                                conversation_id=conversation_id,
                                prediction_type="ml_composite",
                                predictions=insights,
                                confidence_scores={
                                    "objection": objection_result.get("confidence", 0.0),
                                    "needs": needs_result.get("confidence", 0.0),
                                    "conversion": conversion_result.get("confidence", 0.0)
                                },
                                context={
                                    "message_count": len(message_dicts),
                                    "customer_data": customer_data
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Failed to track ML predictions: {e}")
                    
                    return insights
                    
                except Exception as e:
                    logger.warning(f"ML prediction failed, using fallback: {e}")
            
            # Use fallback predictor if ML is not available or failed
            if self.fallback_predictor:
                fallback_results = self.fallback_predictor.predict_all(message_dicts, customer_data)
                insights.update(fallback_results)
                logger.info(f"Fallback predictions used for {conversation_id}")
                
                # Track fallback predictions in ML Pipeline
                if self.ml_pipeline:
                    try:
                        await self.ml_pipeline.track_prediction(
                            conversation_id=conversation_id,
                            prediction_type="fallback",
                            predictions=insights,
                            confidence_scores={
                                "objection": fallback_results.get("objection_confidence", 0.5),
                                "needs": fallback_results.get("needs_confidence", 0.5),
                                "conversion": fallback_results.get("conversion_confidence", 0.5)
                            },
                            context={
                                "message_count": len(message_dicts),
                                "customer_data": customer_data,
                                "fallback_reason": "ml_unavailable"
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to track fallback predictions: {e}")
                
                return insights
            
            # 1. Predict objections
            if self.objection_predictor:
                objection_result = await self.objection_predictor.predict_objections(
                    conversation_id, message_dicts, customer_data
                )
                if objection_result.get("objections"):
                    insights["objections_predicted"] = objection_result["objections"]
            
            # 2. Detect needs
            if self.needs_predictor:
                needs_result = await self.needs_predictor.predict_needs(
                    conversation_id, message_dicts, customer_data
                )
                if needs_result.get("needs"):
                    insights["needs_detected"] = needs_result["needs"]
            
            # 3. Predict conversion probability
            if self.conversion_predictor:
                conversion_result = await self.conversion_predictor.predict_conversion(
                    conversation_id, message_dicts, customer_data
                )
                insights["conversion_probability"] = conversion_result.get("conversion_probability", 0.0)
            
            # 4. Get decision engine recommendations
            if self.decision_engine:
                try:
                    # Create context for decision engine
                    decision_context = {
                        "conversation_id": conversation_id,
                        "messages": message_dicts,
                        "customer_data": customer_data,
                        "objection_predictions": objection_result if self.objection_predictor else {},
                        "needs_predictions": needs_result if self.needs_predictor else {},
                        "conversion_predictions": conversion_result if self.conversion_predictor else {}
                    }
                    
                    decision_result = await self.decision_engine.get_next_best_action(
                        conversation_id, message_dicts, customer_data,
                        objection_result if self.objection_predictor else {},
                        needs_result if self.needs_predictor else {},
                        conversion_result if self.conversion_predictor else {}
                    )
                    
                    if decision_result.get("recommended_actions"):
                        insights["recommended_actions"] = decision_result["recommended_actions"]
                    
                    # Add decision engine insights
                    if decision_result.get("strategy_recommendation"):
                        insights["strategy_recommendation"] = decision_result["strategy_recommendation"]
                        
                except Exception as e:
                    logger.warning(f"Decision engine error: {e}")
                    # Continue without decision engine recommendations
            
            logger.info(f"Predictive analysis completed for {conversation_id}: {len(insights['objections_predicted'])} objections, {len(insights['needs_detected'])} needs")
            
        except Exception as e:
            logger.error(f"Error in predictive analysis: {e}")
            # Return empty insights on error - don't break the conversation
        
        return insights
    
    def _estimate_satisfaction_score(self, state: ConversationState) -> float:
        """
        Estimate customer satisfaction based on conversation signals.
        
        Args:
            state: Current conversation state
            
        Returns:
            Estimated satisfaction score (0-10)
        """
        try:
            score = 5.0  # Base score
            
            # Positive indicators
            positive_words = ["gracias", "excelente", "perfecto", "genial", "interesante", "me gusta"]
            negative_words = ["no", "caro", "difícil", "complicado", "duda", "problema"]
            
            # Analyze messages
            for message in state.messages:
                if message.role == "user":
                    content_lower = message.content.lower()
                    
                    # Check positive indicators
                    for word in positive_words:
                        if word in content_lower:
                            score += 0.3
                    
                    # Check negative indicators
                    for word in negative_words:
                        if word in content_lower:
                            score -= 0.2
            
            # Engagement factor
            if len(state.messages) > 10:
                score += 0.5  # Good engagement
            elif len(state.messages) < 4:
                score -= 0.5  # Low engagement
            
            # Phase progression
            if state.phase in ["closing", "commitment"]:
                score += 1.0  # Reached advanced phase
            
            # Price objection handling
            if state.context.get("price_objection_handled"):
                score += 0.5  # Successfully handled objection
            
            # Ensure score is within bounds
            return max(0.0, min(10.0, score))
            
        except Exception as e:
            logger.error(f"Error estimating satisfaction score: {e}")
            return 5.0  # Default neutral score