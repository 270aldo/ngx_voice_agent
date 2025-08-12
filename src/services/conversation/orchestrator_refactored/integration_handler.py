"""
Integration Handler

Manages integrations with external services (OpenAI, ElevenLabs, Supabase, etc).
Single responsibility: External service coordination.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

from src.integrations.openai_client import OpenAIClient
from src.integrations.elevenlabs import voice_engine
from src.integrations.supabase.resilient_client import resilient_supabase_client
from src.services.multi_voice_service import MultiVoiceService
from src.services.qualification_service import LeadQualificationService
from src.services.human_transfer_service import HumanTransferService
from src.services.follow_up_service import FollowUpService

logger = logging.getLogger(__name__)


class IntegrationHandler:
    """Handles all external service integrations."""
    
    def __init__(self):
        """Initialize integration handler with service clients."""
        self.openai_client = None
        self.voice_engine = voice_engine
        self.supabase_client = resilient_supabase_client
        self.multi_voice_service = None
        self.lead_qualification_service = None
        self.human_transfer_service = None
        self.follow_up_service = None
        
        # Service health status
        self.service_status = {
            "openai": False,
            "elevenlabs": False,
            "supabase": False,
            "lead_qualification": False
        }
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all integration services."""
        try:
            # Initialize OpenAI client
            self.openai_client = OpenAIClient()
            self.service_status["openai"] = True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
        
        try:
            # Initialize Multi-Voice Service
            self.multi_voice_service = MultiVoiceService()
            self.service_status["elevenlabs"] = self.voice_engine is not None
        except Exception as e:
            logger.error(f"Failed to initialize Multi-Voice service: {e}")
        
        try:
            # Initialize Lead Qualification Service
            self.lead_qualification_service = LeadQualificationService()
            self.service_status["lead_qualification"] = True
        except Exception as e:
            logger.error(f"Failed to initialize Lead Qualification service: {e}")
        
        try:
            # Initialize Human Transfer Service
            self.human_transfer_service = HumanTransferService()
        except Exception as e:
            logger.error(f"Failed to initialize Human Transfer service: {e}")
        
        try:
            # Initialize Follow-up Service
            self.follow_up_service = FollowUpService()
        except Exception as e:
            logger.error(f"Failed to initialize Follow-up service: {e}")
        
        # Check Supabase status
        self.service_status["supabase"] = self.supabase_client is not None
    
    async def generate_ai_response(
        self,
        prompt: str,
        context: Dict[str, Any],
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Generate AI response using OpenAI.
        
        Args:
            prompt: The prompt to send to AI
            context: Conversation context
            model: OpenAI model to use
            temperature: Response temperature
            
        Returns:
            Generated response or None if failed
        """
        if not self.openai_client:
            logger.error("OpenAI client not initialized")
            return None
        
        try:
            # Prepare messages for OpenAI
            messages = self._prepare_messages(prompt, context)
            
            # Generate response
            response = await self.openai_client.generate_response(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=500
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            return None
    
    async def synthesize_voice(
        self,
        text: str,
        voice_id: Optional[str] = None,
        section: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesize voice using ElevenLabs.
        
        Args:
            text: Text to synthesize
            voice_id: Optional voice ID
            section: Optional section for multi-voice
            
        Returns:
            Audio bytes or None if failed
        """
        if not self.voice_engine:
            logger.error("Voice engine not initialized")
            return None
        
        try:
            # Use multi-voice service if section is specified
            if section and self.multi_voice_service:
                audio = await self.multi_voice_service.synthesize_for_section(
                    text=text,
                    section=section
                )
            else:
                # Use default voice synthesis
                audio = await self.voice_engine.synthesize(
                    text=text,
                    voice_id=voice_id
                )
            
            return audio
            
        except Exception as e:
            logger.error(f"Failed to synthesize voice: {e}")
            return None
    
    async def qualify_lead(
        self,
        customer_data: Dict[str, Any],
        conversation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Qualify a lead using the lead qualification service.
        
        Args:
            customer_data: Customer information
            conversation_data: Conversation information
            
        Returns:
            Lead qualification results
        """
        if not self.lead_qualification_service:
            return {"score": 0.5, "tier": "unknown", "qualified": False}
        
        try:
            # Calculate lead score
            score = await self.lead_qualification_service.calculate_lead_score(
                customer_data=customer_data,
                conversation_data=conversation_data
            )
            
            # Determine qualification status
            qualified = score > 0.7
            tier = self._determine_tier(score)
            
            return {
                "score": score,
                "tier": tier,
                "qualified": qualified,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to qualify lead: {e}")
            return {"score": 0.5, "tier": "unknown", "qualified": False}
    
    async def check_human_transfer(
        self,
        conversation_state: Dict[str, Any],
        trigger_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if human transfer is needed.
        
        Args:
            conversation_state: Current conversation state
            trigger_reason: Optional specific trigger reason
            
        Returns:
            Transfer decision and details
        """
        if not self.human_transfer_service:
            return {"transfer_needed": False, "reason": "service_unavailable"}
        
        try:
            # Check transfer conditions
            result = await self.human_transfer_service.check_transfer_conditions(
                conversation_state=conversation_state,
                trigger_reason=trigger_reason
            )
            
            return {
                "transfer_needed": result.get("transfer", False),
                "reason": result.get("reason", ""),
                "priority": result.get("priority", "normal"),
                "suggested_agent": result.get("suggested_agent"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check human transfer: {e}")
            return {"transfer_needed": False, "reason": "check_failed"}
    
    async def schedule_follow_up(
        self,
        conversation_id: str,
        follow_up_data: Dict[str, Any]
    ) -> bool:
        """
        Schedule a follow-up for the conversation.
        
        Args:
            conversation_id: Conversation identifier
            follow_up_data: Follow-up details
            
        Returns:
            True if scheduled successfully
        """
        if not self.follow_up_service:
            return False
        
        try:
            # Schedule follow-up
            result = await self.follow_up_service.schedule(
                conversation_id=conversation_id,
                follow_up_type=follow_up_data.get("type", "email"),
                scheduled_time=follow_up_data.get("scheduled_time"),
                message=follow_up_data.get("message"),
                metadata=follow_up_data.get("metadata", {})
            )
            
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Failed to schedule follow-up: {e}")
            return False
    
    async def save_to_database(
        self,
        table: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Save data to database using Supabase.
        
        Args:
            table: Table name
            data: Data to save
            
        Returns:
            True if saved successfully
        """
        if not self.supabase_client:
            logger.error("Supabase client not initialized")
            return False
        
        try:
            # Add timestamp if not present
            if "created_at" not in data:
                data["created_at"] = datetime.utcnow().isoformat()
            
            # Save to database
            result = await self.supabase_client.insert(table, data)
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            return False
    
    async def retrieve_from_database(
        self,
        table: str,
        filters: Dict[str, Any],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve data from database.
        
        Args:
            table: Table name
            filters: Query filters
            limit: Maximum number of results
            
        Returns:
            List of results
        """
        if not self.supabase_client:
            logger.error("Supabase client not initialized")
            return []
        
        try:
            # Query database
            result = await self.supabase_client.query(
                table=table,
                filters=filters,
                limit=limit
            )
            
            return result.data if result else []
            
        except Exception as e:
            logger.error(f"Failed to retrieve from database: {e}")
            return []
    
    def _prepare_messages(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Prepare messages for OpenAI API."""
        messages = []
        
        # Add system message
        system_prompt = context.get("system_prompt", "You are a helpful AI assistant.")
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history if available
        history = context.get("history", [])
        for msg in history[-5:]:  # Last 5 messages for context
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def _determine_tier(self, score: float) -> str:
        """Determine customer tier based on score."""
        if score >= 0.8:
            return "premium"
        elif score >= 0.6:
            return "standard"
        elif score >= 0.4:
            return "basic"
        else:
            return "trial"
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health status of all integrations.
        
        Returns:
            Health status of all services
        """
        health_status = {}
        
        # Check OpenAI
        try:
            if self.openai_client:
                # Simple test call
                test_response = await asyncio.wait_for(
                    self.openai_client.generate_response(
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=5
                    ),
                    timeout=5.0
                )
                health_status["openai"] = test_response is not None
            else:
                health_status["openai"] = False
        except Exception:
            health_status["openai"] = False
        
        # Check ElevenLabs
        health_status["elevenlabs"] = self.voice_engine is not None
        
        # Check Supabase
        try:
            if self.supabase_client:
                # Simple connectivity test
                result = await asyncio.wait_for(
                    self.supabase_client.query("conversations", {"limit": 1}),
                    timeout=5.0
                )
                health_status["supabase"] = True
            else:
                health_status["supabase"] = False
        except Exception:
            health_status["supabase"] = False
        
        # Check other services
        health_status["lead_qualification"] = self.lead_qualification_service is not None
        health_status["human_transfer"] = self.human_transfer_service is not None
        health_status["follow_up"] = self.follow_up_service is not None
        
        # Overall health
        health_status["overall"] = all([
            health_status.get("openai", False),
            health_status.get("supabase", False)
        ])
        
        return health_status
    
    def get_service_status(self) -> Dict[str, bool]:
        """Get current status of all services."""
        return self.service_status.copy()