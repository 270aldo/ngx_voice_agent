import os
import logging
from typing import Optional, Dict, Any, Union, BinaryIO
from io import BytesIO
from dotenv import load_dotenv
from enum import Enum
import asyncio

from src.integrations.elevenlabs_client import get_elevenlabs_client
from src.utils.structured_logging import StructuredLogger

# Configurar logging
logger = StructuredLogger.get_logger(__name__)

# Cargar variables de entorno
load_dotenv()

class ProgramVoice(str, Enum):
    """Voces predefinidas para cada programa."""
    PRIME_MALE = "prime_male"
    PRIME_FEMALE = "prime_female"
    LONGEVITY_MALE = "longevity_male"
    LONGEVITY_FEMALE = "longevity_female"

class VoiceEngine:
    """Motor de síntesis de voz utilizando ElevenLabs."""
    
    # Mapeo de voces de programa a ID de voz en ElevenLabs
    # Estos IDs son ejemplos y deben ser reemplazados por IDs reales
    VOICE_MAPPING = {
        "PRIME_MALE": "pNInz6obpgDQGcFmaJgB",      # Adam (ejemplo)
        "PRIME_FEMALE": "EXAVITQu4vr4xnSDxMaL",    # Nicole (ejemplo)
        "LONGEVITY_MALE": "VR6AewLTigWG4xSOukaG",  # Arnold (ejemplo)
        "LONGEVITY_FEMALE": "oWAxZDx7w5VEj9dCyTzz"  # Grace (ejemplo)
    }
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VoiceEngine, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Inicializar el motor de voz usando el cliente centralizado con circuit breaker."""
        # Usar el cliente centralizado que ya tiene circuit breaker
        self.client = get_elevenlabs_client()
        logger.info(
            "Motor de voz inicializado con cliente centralizado",
            extra={"mock_mode": self.client.mock_mode}
        )
    
    def get_voice_id(self, program_type: str, gender: str = "male") -> str:
        """
        Obtener ID de voz según programa y género.
        
        Args:
            program_type (str): Tipo de programa ("PRIME" o "LONGEVITY")
            gender (str): Género de la voz ("male" o "female")
            
        Returns:
            str: ID de voz en ElevenLabs
        """
        # Delegar al cliente centralizado
        return self.client.get_voice_id(program_type, gender)
    
    def text_to_speech(self, text: str, program_type: str = "PRIME", gender: str = "male") -> BytesIO:
        """
        Convertir texto a voz.
        
        Args:
            text (str): Texto a convertir a voz
            program_type (str): Tipo de programa ("PRIME" o "LONGEVITY")
            gender (str): Género de la voz ("male" o "female")
            
        Returns:
            BytesIO: Stream de audio
        """
        # Usar el cliente centralizado con circuit breaker
        return self.client.text_to_speech(text, program_type, gender)
    
    async def text_to_speech_async(self, text: str, program_type: str = "PRIME", gender: str = "male") -> BytesIO:
        """
        Convertir texto a voz de forma asíncrona.
        
        Args:
            text (str): Texto a convertir a voz
            program_type (str): Tipo de programa ("PRIME" o "LONGEVITY")
            gender (str): Género de la voz ("male" o "female")
            
        Returns:
            BytesIO: Stream de audio
        """
        # Usar el cliente centralizado con circuit breaker
        return await self.client.text_to_speech_async(text, program_type, gender)

# Singleton instance
voice_engine = VoiceEngine() 