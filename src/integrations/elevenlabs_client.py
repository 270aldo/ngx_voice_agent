"""
ElevenLabs Client Integration with Circuit Breaker.

This module provides a centralized ElevenLabs client with circuit breaker protection
to handle API failures gracefully.
"""

import os
from typing import Optional, Dict, Any, BinaryIO
from io import BytesIO
import asyncio
from functools import lru_cache
import logging

from src.config import settings
from src.services.circuit_breaker_service import circuit_breaker, get_circuit_breaker, CircuitBreakerConfig
from src.utils.structured_logging import StructuredLogger
from src.utils.metrics import track_external_api_call

# Import ElevenLabs components
try:
    from elevenlabs import VoiceSettings
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    VoiceSettings = None
    ElevenLabs = None

logger = StructuredLogger.get_logger(__name__)


class ElevenLabsClientWrapper:
    """
    Wrapper for ElevenLabs client with circuit breaker protection.
    
    Features:
    - Automatic circuit breaker on API calls
    - Voice synthesis with fallback to cached audio
    - Mock mode for development/testing
    - Metrics tracking for API usage
    """
    
    # Voice mapping for different programs and genders
    VOICE_MAPPING = {
        "PRIME_MALE": "pNInz6obpgDQGcFmaJgB",      # Adam
        "PRIME_FEMALE": "EXAVITQu4vr4xnSDxMaL",    # Nicole
        "LONGEVITY_MALE": "VR6AewLTigWG4xSOukaG",  # Arnold
        "LONGEVITY_FEMALE": "oWAxZDx7w5VEj9dCyTzz"  # Grace
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ElevenLabs client wrapper.
        
        Args:
            api_key: ElevenLabs API key. If None, uses ELEVENLABS_API_KEY from environment.
        """
        self.api_key = api_key or settings.elevenlabs_api_key.get_secret_value() if settings.elevenlabs_api_key else None
        
        if not self.api_key:
            self.api_key = os.getenv("ELEVENLABS_API_KEY")
            
        self.mock_mode = False
        
        if not self.api_key or not ELEVENLABS_AVAILABLE:
            logger.warning(
                "ElevenLabs API key not found or library not available - using mock mode",
                extra={
                    "has_api_key": bool(self.api_key),
                    "library_available": ELEVENLABS_AVAILABLE
                }
            )
            self.mock_mode = True
        
        # Initialize voice settings
        if VoiceSettings:
            self.voice_settings = VoiceSettings(
                stability=0.71,
                similarity_boost=0.5,
                style=0.0,
                use_speaker_boost=True
            )
        else:
            self.voice_settings = None
        
        # Initialize client if not in mock mode
        self.client = None
        if not self.mock_mode and ELEVENLABS_AVAILABLE:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                logger.info("ElevenLabs client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs client: {e}")
                self.mock_mode = True
        
        # Cache for fallback audio
        self._audio_cache: Dict[str, bytes] = {}
        
        logger.info(
            f"ElevenLabs client initialized",
            extra={
                "mock_mode": self.mock_mode,
                "voice_count": len(self.VOICE_MAPPING)
            }
        )
    
    def get_voice_id(self, program_type: str, gender: str = "male") -> str:
        """
        Get voice ID for program and gender.
        
        Args:
            program_type: Program type ("PRIME" or "LONGEVITY")
            gender: Voice gender ("male" or "female")
            
        Returns:
            Voice ID for ElevenLabs
        """
        key = f"{program_type}_{gender}".upper()
        voice_id = self.VOICE_MAPPING.get(key)
        
        if not voice_id:
            logger.warning(
                f"Voice not found for {key}, using default",
                extra={"key": key}
            )
            # Use first available voice as default
            voice_id = next(iter(self.VOICE_MAPPING.values()))
        
        return voice_id
    
    @circuit_breaker(
        "elevenlabs_tts",
        failure_threshold=3,
        recovery_timeout=30
    )
    async def text_to_speech_async(
        self,
        text: str,
        program_type: str = "PRIME",
        gender: str = "male"
    ) -> BytesIO:
        """
        Convert text to speech with circuit breaker protection.
        
        Args:
            text: Text to convert to speech
            program_type: Program type ("PRIME" or "LONGEVITY")
            gender: Voice gender ("male" or "female")
            
        Returns:
            Audio stream as BytesIO
        """
        # Generate cache key
        cache_key = f"{program_type}_{gender}_{hash(text[:100])}"
        
        # Check cache first
        if cache_key in self._audio_cache:
            logger.debug("Using cached audio")
            return BytesIO(self._audio_cache[cache_key])
        
        # If in mock mode, return mock audio
        if self.mock_mode:
            logger.info(
                f"Mock mode: Would convert text to speech",
                extra={
                    "text_preview": text[:50] + "..." if len(text) > 50 else text,
                    "program_type": program_type,
                    "gender": gender
                }
            )
            mock_audio = b"mock_audio_data"
            return BytesIO(mock_audio)
        
        # Get voice ID
        voice_id = self.get_voice_id(program_type, gender)
        
        # Make API call with metrics tracking
        async with track_external_api_call("elevenlabs", "text_to_speech"):
            try:
                # Run synchronous API call in thread pool
                audio_bytes = await asyncio.to_thread(
                    self._sync_text_to_speech,
                    text,
                    voice_id
                )
                
                # Cache successful result (limit cache size)
                if len(self._audio_cache) < 100:  # Max 100 cached items
                    self._audio_cache[cache_key] = audio_bytes
                
                return BytesIO(audio_bytes)
                
            except Exception as e:
                logger.error(
                    f"ElevenLabs API error: {str(e)}",
                    extra={
                        "error_type": type(e).__name__,
                        "voice_id": voice_id,
                        "text_length": len(text)
                    },
                    exc_info=True
                )
                
                # Generate fallback audio
                return self._generate_fallback_audio(text, program_type, gender)
    
    def _sync_text_to_speech(self, text: str, voice_id: str) -> bytes:
        """
        Synchronous text to speech conversion.
        
        Args:
            text: Text to convert
            voice_id: ElevenLabs voice ID
            
        Returns:
            Audio bytes
        """
        if not self.client:
            raise RuntimeError("ElevenLabs client not initialized")
        
        # Call ElevenLabs API
        audio_generator = self.client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=self.voice_settings
        )
        
        # Collect audio chunks
        audio_bytes = b""
        try:
            for chunk in audio_generator:
                if chunk:
                    audio_bytes += chunk
        except TypeError:
            # If not a generator, use directly
            audio_bytes = audio_generator
        
        return audio_bytes
    
    def _generate_fallback_audio(
        self,
        text: str,
        program_type: str,
        gender: str
    ) -> BytesIO:
        """
        Generate fallback audio when API fails.
        
        Args:
            text: Original text
            program_type: Program type
            gender: Voice gender
            
        Returns:
            Fallback audio stream
        """
        # Check if we have any cached audio for this voice
        cache_prefix = f"{program_type}_{gender}_"
        for key, audio in self._audio_cache.items():
            if key.startswith(cache_prefix):
                logger.info(
                    "Using cached audio as fallback",
                    extra={
                        "cache_key": key,
                        "original_text_preview": text[:50]
                    }
                )
                return BytesIO(audio)
        
        # Generate silence or simple beep as last resort
        logger.warning(
            "No cached audio available, using silence fallback",
            extra={
                "program_type": program_type,
                "gender": gender
            }
        )
        
        # Simple silent MP3 (smallest valid MP3)
        silence_mp3 = b'\xff\xfb\x10\x00\x00\x0f\xf0\x00\x00\x69\x00\x00\x00\x08\x00\x00\x0d\x20\x00\x00\x01\x00\x00\x01\xa4\x00\x00\x00\x20\x00\x00\x34\x80\x00\x00\x04'
        return BytesIO(silence_mp3)
    
    def text_to_speech(
        self,
        text: str,
        program_type: str = "PRIME",
        gender: str = "male"
    ) -> BytesIO:
        """
        Synchronous wrapper for text to speech.
        
        Args:
            text: Text to convert to speech
            program_type: Program type
            gender: Voice gender
            
        Returns:
            Audio stream
        """
        # Create event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async method
        return loop.run_until_complete(
            self.text_to_speech_async(text, program_type, gender)
        )
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """
        Get available voices with circuit breaker protection.
        
        Returns:
            Dictionary of available voices
        """
        if self.mock_mode:
            return {
                "voices": [
                    {"voice_id": vid, "name": key}
                    for key, vid in self.VOICE_MAPPING.items()
                ]
            }
        
        @circuit_breaker(
            "elevenlabs_voices",
            failure_threshold=5,
            recovery_timeout=60
        )
        async def _get_voices():
            voices = await asyncio.to_thread(
                self.client.voices.get_all
            )
            return {"voices": voices}
        
        try:
            return await _get_voices()
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return {"voices": [], "error": str(e)}


# Singleton instance
_elevenlabs_client: Optional[ElevenLabsClientWrapper] = None


def get_elevenlabs_client() -> ElevenLabsClientWrapper:
    """
    Get singleton ElevenLabs client instance.
    
    Returns:
        ElevenLabs client wrapper with circuit breaker protection
    """
    global _elevenlabs_client
    if _elevenlabs_client is None:
        _elevenlabs_client = ElevenLabsClientWrapper()
    return _elevenlabs_client