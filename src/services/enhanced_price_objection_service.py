"""
Enhanced Price Objection Service integrado con el sistema HIE existente.

Este servicio maneja objeciones de precio integrándose correctamente con:
- El sistema HIE existente (Hybrid Intelligence Engine)  
- TierDetectionService para ajustes de tier
- Cálculos de ROI biológico personalizados
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.services.price_objection_service import PriceObjectionService, BiologicalROI
from src.services.tier_detection_service import TierDetectionService

logger = logging.getLogger(__name__)


class EnhancedPriceObjectionService(PriceObjectionService):
    """
    Servicio mejorado que integra manejo de objeciones con el sistema HIE existente.
    """
    
    def __init__(self):
        super().__init__()
        # Ya tenemos tier_detection_service del padre
    
    async def analyze_objection(self, objection_text: str, customer_profile: Dict, conversation_context: Dict) -> Dict[str, Any]:
        """
        Analizar la objeción del cliente.
        
        Args:
            objection_text: Texto de la objeción
            customer_profile: Perfil del cliente
            conversation_context: Contexto de la conversación
            
        Returns:
            Dict con análisis de la objeción
        """
        # Usar el método detect_objection_type del padre
        objection_type = self.detect_objection_type(objection_text)
        
        return {
            "objection_type": objection_type,
            "severity": self._assess_objection_severity(objection_text),
            "suggested_response_type": self._suggest_response_type(objection_type),
            "customer_sentiment": self._analyze_sentiment(objection_text)
        }
    
    def _assess_objection_severity(self, objection_text: str) -> str:
        """Evaluar severidad de la objeción."""
        strong_words = ["nunca", "jamás", "imposible", "no puedo", "demasiado", "muy caro"]
        if any(word in objection_text.lower() for word in strong_words):
            return "high"
        elif "?" in objection_text:
            return "low"
        else:
            return "medium"
    
    def _suggest_response_type(self, objection_type: str) -> str:
        """Sugerir tipo de respuesta según objeción."""
        response_map = {
            "price_high": "value_demonstration",
            "price_comparison": "competitive_advantage",
            "affordability": "payment_options",
            "value_questioning": "roi_demonstration",
            "not_interested": "reengagement"
        }
        return response_map.get(objection_type, "empathetic_validation")
    
    def _analyze_sentiment(self, text: str) -> str:
        """Análisis simple de sentimiento."""
        negative_words = ["no", "nunca", "mal", "caro", "mucho", "imposible"]
        positive_words = ["bien", "bueno", "interesante", "posible"]
        
        neg_count = sum(1 for word in negative_words if word in text.lower())
        pos_count = sum(1 for word in positive_words if word in text.lower())
        
        if neg_count > pos_count:
            return "negative"
        elif pos_count > neg_count:
            return "positive"
        else:
            return "neutral"
    
    async def generate_response(self, objection_analysis: Dict, use_biological_roi: bool = True, include_guarantee: bool = False) -> Dict[str, Any]:
        """
        Generar respuesta a la objeción.
        
        Args:
            objection_analysis: Análisis de la objeción
            use_biological_roi: Si usar ROI biológico
            include_guarantee: Si incluir garantía
            
        Returns:
            Dict con respuesta generada
        """
        objection_type = objection_analysis.get("objection_type", "general")
        
        # Usar el método del padre para generar respuesta base
        base_response = self.handle_objection(objection_type, {})
        
        # Mejorar respuesta con elementos adicionales
        enhanced_response = base_response
        if use_biological_roi:
            enhanced_response += "\n\nConsidera que con NGX estás invirtiendo en años de vida saludable, no solo en un programa."
        
        if include_guarantee:
            enhanced_response += "\n\nAdemás, tienes nuestra garantía de satisfacción de 30 días."
        
        # Determinar acción sugerida
        if objection_analysis.get("severity") == "high":
            suggested_action = "downsell"
        elif objection_analysis.get("customer_sentiment") == "positive":
            suggested_action = "close"
        else:
            suggested_action = "continue_nurturing"
        
        return {
            "response": enhanced_response,
            "suggested_action": suggested_action,
            "confidence": 0.8,
            "alternative_approaches": self._get_alternative_approaches(objection_type)
        }
    
    def _get_alternative_approaches(self, objection_type: str) -> List[str]:
        """Obtener enfoques alternativos para manejar la objeción."""
        approaches = {
            "price_high": [
                "Ofrecer plan de pagos",
                "Mostrar testimonios de ROI",
                "Comparar con competencia"
            ],
            "affordability": [
                "Sugerir tier más económico", 
                "Explicar costo por día",
                "Ofrecer trial period"
            ],
            "value_questioning": [
                "Demo personalizada",
                "Casos de éxito similares",
                "Garantía de resultados"
            ]
        }
        return approaches.get(objection_type, ["Validar preocupación", "Ofrecer más información"])
        
    def generate_hie_integrated_objection_response(self, 
                                                 objection_message: str,
                                                 user_profile: Dict,
                                                 tier_info: Dict,
                                                 current_tier: str = "Pro") -> Dict:
        """
        Genera respuesta a objeción integrada con el sistema HIE existente.
        
        Args:
            objection_message: Mensaje de objeción del usuario
            user_profile: Perfil del usuario construido desde conversation state
            tier_info: Información de tier del TierDetectionService
            current_tier: Tier actual sugerido
            
        Returns:
            Dict con respuesta integrada con HIE
        """
        try:
            # Usar el servicio base para detectar tipo de objeción
            objection_type = self.detect_objection_type(objection_message)
            
            # Calcular ROI basado en tier detectado
            program_price = tier_info.get('pricing', {}).get('monthly_price', 149)
            roi_data = self.calculate_roi(user_profile, program_price)
            
            # Generar respuesta base
            base_response = super().generate_objection_response(
                objection_message, user_profile, current_tier, program_price
            )
            
            # Mejorar respuesta con contexto HIE (Hybrid Intelligence Engine)
            enhanced_response = self._enhance_with_hie_context(
                base_response, tier_info, roi_data
            )
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error en respuesta HIE integrada: {str(e)}")
            return self._fallback_hie_response(objection_message, tier_info)
    
    def _enhance_with_hie_context(self, base_response: Dict, tier_info: Dict, roi_data: BiologicalROI) -> Dict:
        """Mejora la respuesta con contexto del Hybrid Intelligence Engine."""
        
        # Agregar contexto HIE a la respuesta
        hie_enhancement = (
            f"\n\nAdemás, con {tier_info.get('tier', 'Pro')} tienes acceso completo a nuestro "
            f"Hybrid Intelligence Engine - un sistema avanzado de IA "
            f"trabajando 24/7 para tu éxito. Esta tecnología es imposible de clonar "
            f"y te da una ventaja competitiva única."
        )
        
        enhanced_response = base_response.copy()
        enhanced_response["primary_response"] += hie_enhancement
        
        # Agregar información HIE específica
        enhanced_response["hie_context"] = {
            "system_name": "Hybrid Intelligence Engine",
            "system_type": "Sistema de 2 capas adaptativo",
            "unique_value": "Tecnología imposible de clonar",
            "tier_access": tier_info.get('tier', 'Pro'),
            "roi_with_hie": f"{roi_data.roi_percentage}% anual incluyendo HIE"
        }
        
        return enhanced_response
    
    def _fallback_hie_response(self, objection_message: str, tier_info: Dict) -> Dict:
        """Respuesta de fallback con contexto HIE."""
        return {
            "primary_response": (
                f"Entiendo tu preocupación sobre el precio. Con NGX {tier_info.get('tier', 'Pro')} "
                f"no solo obtienes un programa de wellness, sino acceso completo a nuestro "
                f"Hybrid Intelligence Engine - tecnología avanzada que es "
                f"imposible de clonar. El ROI se calcula en meses, no años."
            ),
            "objection_type": "precio_alto",
            "hie_context": {
                "system_name": "Hybrid Intelligence Engine", 
                "system_type": "Sistema de 2 capas adaptativo",
                "unique_value": "Imposible de clonar"
            },
            "success": True,
            "enhanced_with_hie": True
        }