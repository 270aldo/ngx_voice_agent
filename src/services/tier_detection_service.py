"""
Servicio de detección de tier óptimo por lead.

Este servicio analiza el perfil del cliente y la conversación para determinar
qué tier de suscripción es más adecuado para maximizar la conversión.
"""

import logging
import asyncio
import hashlib
import json
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from src.services.ngx_cache_manager import NGXCacheManager
from src.core.dependencies import get_ngx_cache_manager
from src.utils.async_task_manager import AsyncTaskManager, get_task_registry

logger = logging.getLogger(__name__)


class ArchetypeType(str, Enum):
    """Arquetipos principales de NGX."""
    PRIME = "prime"  # El Optimizador
    LONGEVITY = "longevity"  # El Arquitecto de Vida
    HYBRID = "hybrid"  # En transición (45-55 años)


class TierType(str, Enum):
    """Tipos de tier disponibles."""
    ESSENTIAL = "essential"  # $79/mes
    PRO = "pro"             # $149/mes  
    ELITE = "elite"         # $199/mes
    PRIME_PREMIUM = "prime_premium"      # $3,997
    LONGEVITY_PREMIUM = "longevity_premium"  # $3,997


@dataclass
class TierDetectionResult:
    """Resultado de detección de tier."""
    recommended_tier: TierType
    confidence: float
    reasoning: str
    price_point: str
    upsell_potential: str
    demographic_factors: Dict[str, Any]
    behavioral_signals: List[str]
    price_sensitivity: str
    detected_archetype: ArchetypeType
    archetype_confidence: float
    roi_projection: Optional[Dict[str, Any]] = None


class TierDetectionService:
    """Servicio para detectar el tier óptimo por lead."""
    
    def __init__(self):
        """Inicializar el servicio de detección de tier."""
        self._cache_manager: Optional[NGXCacheManager] = None
        self._initialize_cache_task = None
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Initialize async components (deferred until first use)
        self._initialized = False
        
        self.tier_pricing = {
            TierType.ESSENTIAL: 79,
            TierType.PRO: 149,
            TierType.ELITE: 199,
            TierType.PRIME_PREMIUM: 3997,
            TierType.LONGEVITY_PREMIUM: 3997
        }
        
        # Indicadores de ingresos por profesión
        self.income_indicators = {
            "estudiante": {"tier": TierType.ESSENTIAL, "budget": "low", "hourly_rate": 0},
            "freelancer": {"tier": TierType.PRO, "budget": "medium", "hourly_rate": 50},
            "gerente": {"tier": TierType.PRO, "budget": "medium", "hourly_rate": 75},
            "consultor": {"tier": TierType.ELITE, "budget": "high", "hourly_rate": 200},
            "director": {"tier": TierType.ELITE, "budget": "high", "hourly_rate": 300},
            "abogado": {"tier": TierType.PRIME_PREMIUM, "budget": "very_high", "hourly_rate": 400},
            "médico": {"tier": TierType.LONGEVITY_PREMIUM, "budget": "very_high", "hourly_rate": 300},
            "ceo": {"tier": TierType.PRIME_PREMIUM, "budget": "very_high", "hourly_rate": 500},
            "emprendedor": {"tier": TierType.ELITE, "budget": "high", "hourly_rate": 250},
            "ingeniero": {"tier": TierType.PRO, "budget": "medium", "hourly_rate": 100},
            "desarrollador": {"tier": TierType.PRO, "budget": "medium", "hourly_rate": 80}
        }
    
    async def _ensure_initialized(self):
        """Ensure async components are initialized."""
        if not self._initialized:
            await self._initialize_async()
            
    async def _initialize_async(self):
        """Async initialization including task manager setup."""
        try:
            # Get task manager from registry
            registry = get_task_registry()
            self.task_manager = await registry.register_service("tier_detection")
            
            self._initialized = True
            logger.info("TierDetectionService async initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize TierDetectionService async: {e}")
            # Set as initialized anyway to prevent repeated attempts
            self._initialized = True
    
    async def _ensure_cache_initialized(self):
        """Ensure cache is initialized."""
        if self._cache_manager is None and self._initialize_cache_task is None:
            if self.task_manager:
                self._initialize_cache_task = await self.task_manager.create_task(
                    self._initialize_cache(),
                    name="initialize_cache"
                )
            else:
                # Fallback if task manager not ready
                self._initialize_cache_task = asyncio.create_task(self._initialize_cache())
        if self._initialize_cache_task:
            await self._initialize_cache_task
    
    async def _initialize_cache(self):
        """Initialize cache manager."""
        try:
            self._cache_manager = await get_ngx_cache_manager()
            if self._cache_manager:
                logger.info("Cache manager initialized for tier detection service")
        except Exception as e:
            logger.error(f"Failed to initialize cache for tier detection: {e}")
        finally:
            self._initialize_cache_task = None
    
    def _generate_cache_key(self, user_profile: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate cache key for tier detection."""
        # Create deterministic key from profile and context
        key_data = {
            "occupation": user_profile.get("occupation", ""),
            "age": user_profile.get("age", ""),
            "location": user_profile.get("location", ""),
            "message_signals": context.get("message_signals", []),
            "behavioral_signals": context.get("behavioral_signals", [])
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def detect_optimal_tier(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> TierDetectionResult:
        """
        Detectar el tier óptimo para un lead específico.
        
        Args:
            user_message: Mensaje actual del usuario
            user_profile: Perfil del usuario con información demográfica
            conversation_history: Historial de conversación para contexto
            
        Returns:
            TierDetectionResult: Resultado con tier recomendado y reasoning
        """
        # Ensure async components are initialized
        await self._ensure_initialized()
        
        # Ensure cache is initialized
        await self._ensure_cache_initialized()
        
        # Generate cache key
        context = {
            "message_signals": self._extract_message_signals(user_message),
            "behavioral_signals": self._extract_behavioral_signals(conversation_history or [])
        }
        cache_key = self._generate_cache_key(user_profile, context)
        customer_id = user_profile.get("id", "unknown")
        
        # Try cache first
        if self._cache_manager:
            cached_result = await self._cache_manager.get_tier_detection(customer_id, cache_key)
            if cached_result:
                logger.debug(f"Tier detection result retrieved from cache for customer {customer_id}")
                return TierDetectionResult(**cached_result)
        
        try:
            # Análisis demográfico
            demographic_score = self._analyze_demographics(user_profile)
            
            # Análisis del mensaje
            message_analysis = self._analyze_message_content(user_message)
            
            # Análisis de historial si está disponible
            behavioral_analysis = self._analyze_behavioral_patterns(conversation_history) if conversation_history else {}
            
            # Análisis de sensibilidad al precio
            price_sensitivity = self._analyze_price_sensitivity(user_message, user_profile)
            
            # Determinar arquetipo final
            archetype_result = self._determine_final_archetype(
                demographic_score,
                message_analysis,
                user_profile
            )
            
            # Determinar tier basado en múltiples factores
            tier_recommendation = self._calculate_tier_recommendation(
                demographic_score,
                message_analysis,
                behavioral_analysis,
                price_sensitivity,
                archetype_result['archetype']
            )
            
            # Calcular ROI si es posible
            roi_projection = self._calculate_roi_projection(user_profile, tier_recommendation)
            
            result = TierDetectionResult(
                recommended_tier=tier_recommendation['tier'],
                confidence=tier_recommendation['confidence'],
                reasoning=tier_recommendation['reasoning'],
                price_point=f"${self.tier_pricing[tier_recommendation['tier']]}/mes" if tier_recommendation['tier'] in [TierType.ESSENTIAL, TierType.PRO, TierType.ELITE] else f"${self.tier_pricing[tier_recommendation['tier']]}",
                upsell_potential=tier_recommendation['upsell_potential'],
                demographic_factors=demographic_score,
                behavioral_signals=message_analysis.get('signals', []),
                price_sensitivity=price_sensitivity,
                detected_archetype=archetype_result['archetype'],
                archetype_confidence=archetype_result['confidence'],
                roi_projection=roi_projection
            )
            
            # Cache the result
            if self._cache_manager:
                result_dict = {
                    "recommended_tier": result.recommended_tier.value,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "price_point": result.price_point,
                    "upsell_potential": result.upsell_potential,
                    "demographic_factors": result.demographic_factors,
                    "behavioral_signals": result.behavioral_signals,
                    "price_sensitivity": result.price_sensitivity,
                    "detected_archetype": result.detected_archetype.value,
                    "archetype_confidence": result.archetype_confidence,
                    "roi_projection": result.roi_projection
                }
                await self._cache_manager.set_tier_detection(customer_id, cache_key, result_dict)
                logger.debug(f"Tier detection result cached for customer {customer_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error detectando tier óptimo: {e}")
            # Fallback a tier PRO por defecto
            return TierDetectionResult(
                recommended_tier=TierType.PRO,
                confidence=0.5,
                reasoning="Tier por defecto debido a error en análisis",
                price_point="$149/mes",
                upsell_potential="medium",
                demographic_factors={},
                behavioral_signals=[],
                price_sensitivity="medium",
                detected_archetype=ArchetypeType.PRIME,
                archetype_confidence=0.5
            )
    
    def _extract_message_signals(self, message: str) -> List[str]:
        """Extract signals from message content."""
        signals = []
        message_lower = message.lower()
        
        # Performance signals
        if any(word in message_lower for word in ["productividad", "rendimiento", "performance", "eficiencia"]):
            signals.append("performance_focus")
        
        # Health signals
        if any(word in message_lower for word in ["salud", "bienestar", "longevidad", "prevención"]):
            signals.append("health_focus")
        
        # Budget signals
        if any(word in message_lower for word in ["precio", "costo", "presupuesto", "inversión"]):
            signals.append("price_inquiry")
        
        # Urgency signals
        if any(word in message_lower for word in ["urgente", "rápido", "ahora", "inmediato"]):
            signals.append("urgency")
        
        return signals
    
    def _extract_behavioral_signals(self, conversation_history: List[Dict[str, str]]) -> List[str]:
        """Extract behavioral signals from conversation history."""
        signals = []
        
        if len(conversation_history) > 5:
            signals.append("engaged_conversation")
        
        if len(conversation_history) > 10:
            signals.append("highly_engaged")
        
        # Check for repeated questions
        questions = [msg for msg in conversation_history if msg.get("role") == "user" and "?" in msg.get("content", "")]
        if len(questions) > 3:
            signals.append("high_interest")
        
        return signals
    
    def _analyze_demographics(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar factores demográficos del usuario."""
        try:
            age = user_profile.get('age', 0)
            occupation = user_profile.get('occupation', '').lower()
            location = user_profile.get('location', '').lower()
            income_bracket = user_profile.get('income_bracket', 'medium')
            
            # Análisis por ocupación
            occupation_analysis = {}
            for prof, data in self.income_indicators.items():
                if prof in occupation:
                    occupation_analysis = {
                        'detected_profession': prof,
                        'suggested_tier': data['tier'],
                        'budget_category': data['budget'],
                        'estimated_hourly_rate': data['hourly_rate']
                    }
                    break
            
            # Análisis por edad y arquetipo
            age_analysis = {}
            archetype = None
            if age > 0:
                if age < 25:
                    age_analysis = {'tier_preference': TierType.ESSENTIAL, 'budget_impact': 'low'}
                    archetype = ArchetypeType.PRIME  # Jóvenes generalmente buscan performance
                elif age < 35:
                    age_analysis = {'tier_preference': TierType.PRO, 'budget_impact': 'medium'}
                    archetype = ArchetypeType.PRIME
                elif age < 45:
                    age_analysis = {'tier_preference': TierType.ELITE, 'budget_impact': 'high'}
                    archetype = ArchetypeType.PRIME
                elif age >= 45 and age <= 55:
                    # Rango híbrido - necesita análisis adicional
                    age_analysis = {'tier_preference': TierType.ELITE, 'budget_impact': 'high'}
                    archetype = ArchetypeType.HYBRID
                else:
                    age_analysis = {'tier_preference': TierType.LONGEVITY_PREMIUM, 'budget_impact': 'very_high'}
                    archetype = ArchetypeType.LONGEVITY
            
            # Análisis por ubicación (simplificado)
            location_analysis = {}
            if any(city in location for city in ['mexico', 'cdmx', 'guadalajara', 'monterrey']):
                location_analysis = {'market': 'mexico', 'purchasing_power': 'medium'}
            elif any(city in location for city in ['madrid', 'barcelona', 'españa']):
                location_analysis = {'market': 'spain', 'purchasing_power': 'high'}
            else:
                location_analysis = {'market': 'other', 'purchasing_power': 'medium'}
            
            return {
                'occupation_analysis': occupation_analysis,
                'age_analysis': age_analysis,
                'location_analysis': location_analysis,
                'declared_income_bracket': income_bracket,
                'detected_archetype': archetype.value if archetype else None
            }
            
        except Exception as e:
            logger.error(f"Error analizando demografía: {e}")
            return {}
    
    def _analyze_message_content(self, message: str) -> Dict[str, Any]:
        """Analizar contenido del mensaje para detectar señales de tier."""
        try:
            message_lower = message.lower()
            
            # Señales de presupuesto alto
            high_budget_signals = [
                "empresa propia", "mi empresa", "soy ceo", "soy director",
                "resultados máximos", "lo mejor", "no importa el precio",
                "vale la pena", "transformación completa", "premium",
                "exclusivo", "personalizado", "vip"
            ]
            
            # Señales de arquetipo PRIME (Optimizador)
            prime_signals = [
                "productividad", "rendimiento", "optimización", "eficiencia",
                "ejecutivo", "liderazgo", "empresa", "negocio", "estrés laboral",
                "falta de energía", "focus", "decisiones rápidas", "agenda ocupada",
                "viajes de trabajo", "competitivo", "resultados medibles", "roi"
            ]
            
            # Señales de arquetipo LONGEVITY (Arquitecto de Vida)
            longevity_signals = [
                "envejecimiento", "longevidad", "prevención", "salud a largo plazo",
                "vitalidad", "calidad de vida", "independencia", "jubilación",
                "dolores", "movilidad", "memoria", "energía sostenible",
                "nietos", "familia", "bienestar integral", "antiaging"
            ]
            
            # Señales de presupuesto medio
            medium_budget_signals = [
                "profesional", "gerente", "trabajo en", "freelancer",
                "razonable", "dentro del presupuesto", "inversión inteligente",
                "vale la pena la inversión", "buen precio", "competitivo"
            ]
            
            # Señales de presupuesto bajo
            low_budget_signals = [
                "estudiante", "presupuesto limitado", "barato", "económico",
                "no tengo mucho", "más barato", "descuento", "oferta",
                "precio bajo", "ahorro"
            ]
            
            # Señales de urgencia
            urgency_signals = [
                "urgente", "rápido", "pronto", "inmediato", "ya",
                "hoy", "esta semana", "no puedo esperar"
            ]
            
            # Señales de comparación
            comparison_signals = [
                "vs", "comparado con", "otros", "alternativas",
                "competencia", "mejor que", "diferente a"
            ]
            
            # Detectar señales
            detected_signals = []
            budget_score = 0
            prime_score = 0
            longevity_score = 0
            
            for signal in high_budget_signals:
                if signal in message_lower:
                    detected_signals.append(f"high_budget: {signal}")
                    budget_score += 3
            
            for signal in medium_budget_signals:
                if signal in message_lower:
                    detected_signals.append(f"medium_budget: {signal}")
                    budget_score += 2
            
            for signal in low_budget_signals:
                if signal in message_lower:
                    detected_signals.append(f"low_budget: {signal}")
                    budget_score -= 1
            
            for signal in urgency_signals:
                if signal in message_lower:
                    detected_signals.append(f"urgency: {signal}")
                    budget_score += 1
            
            for signal in comparison_signals:
                if signal in message_lower:
                    detected_signals.append(f"comparison: {signal}")
            
            # Detectar señales de arquetipo
            for signal in prime_signals:
                if signal in message_lower:
                    detected_signals.append(f"prime: {signal}")
                    prime_score += 1
            
            for signal in longevity_signals:
                if signal in message_lower:
                    detected_signals.append(f"longevity: {signal}")
                    longevity_score += 1
            
            return {
                'signals': detected_signals,
                'budget_score': budget_score,
                'prime_score': prime_score,
                'longevity_score': longevity_score,
                'message_length': len(message),
                'sophistication_level': self._calculate_sophistication(message)
            }
            
        except Exception as e:
            logger.error(f"Error analizando mensaje: {e}")
            return {'signals': [], 'budget_score': 0}
    
    def _analyze_behavioral_patterns(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analizar patrones de comportamiento en la conversación."""
        try:
            if not conversation_history:
                return {}
            
            user_messages = [msg['content'] for msg in conversation_history if msg['role'] == 'user']
            
            # Análisis de engagement
            engagement_score = len(user_messages)
            avg_message_length = sum(len(msg) for msg in user_messages) / len(user_messages) if user_messages else 0
            
            # Análisis de preguntas específicas
            questions_asked = sum(1 for msg in user_messages if '?' in msg)
            
            # Análisis de menciones de precio
            price_mentions = sum(1 for msg in user_messages if any(word in msg.lower() for word in ['precio', 'costo', 'cuánto', 'pago']))
            
            # Análisis de objeciones
            objections = sum(1 for msg in user_messages if any(word in msg.lower() for word in ['pero', 'sin embargo', 'no estoy seguro']))
            
            return {
                'engagement_score': engagement_score,
                'avg_message_length': avg_message_length,
                'questions_asked': questions_asked,
                'price_mentions': price_mentions,
                'objections_raised': objections,
                'conversation_depth': 'high' if engagement_score > 5 else 'medium' if engagement_score > 2 else 'low'
            }
            
        except Exception as e:
            logger.error(f"Error analizando patrones: {e}")
            return {}
    
    def _analyze_price_sensitivity(self, message: str, user_profile: Dict[str, Any]) -> str:
        """Analizar sensibilidad al precio del usuario."""
        try:
            message_lower = message.lower()
            
            # Indicadores de baja sensibilidad al precio
            if any(phrase in message_lower for phrase in [
                "no importa el precio", "vale la pena", "inversión",
                "calidad", "premium", "lo mejor"
            ]):
                return "low"
            
            # Indicadores de alta sensibilidad al precio
            if any(phrase in message_lower for phrase in [
                "barato", "económico", "presupuesto limitado",
                "descuento", "oferta", "precio bajo"
            ]):
                return "high"
            
            # Análisis demográfico
            age = user_profile.get('age', 0)
            occupation = user_profile.get('occupation', '').lower()
            
            if age > 45 and any(prof in occupation for prof in ['ceo', 'director', 'médico', 'abogado']):
                return "low"
            elif age < 25 or 'estudiante' in occupation:
                return "high"
            
            return "medium"
            
        except Exception as e:
            logger.error(f"Error analizando sensibilidad al precio: {e}")
            return "medium"
    
    def _calculate_sophistication(self, message: str) -> str:
        """Calcular nivel de sofisticación del mensaje."""
        try:
            # Palabras técnicas o sofisticadas
            sophisticated_words = [
                "optimización", "eficiencia", "productividad", "estrategia",
                "metodología", "sistemático", "integral", "holístico",
                "personalizado", "algoritmo", "análisis", "métricas"
            ]
            
            sophisticated_count = sum(1 for word in sophisticated_words if word in message.lower())
            
            if sophisticated_count >= 3:
                return "high"
            elif sophisticated_count >= 1:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"Error calculando sofisticación: {e}")
            return "medium"
    
    def _determine_final_archetype(
        self,
        demographic_score: Dict[str, Any],
        message_analysis: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determinar el arquetipo final del usuario basado en múltiples señales."""
        try:
            age = user_profile.get('age', 0)
            detected_archetype_demo = demographic_score.get('detected_archetype')
            prime_score = message_analysis.get('prime_score', 0)
            longevity_score = message_analysis.get('longevity_score', 0)
            
            # Si está en rango híbrido (45-55), usar señales del mensaje
            if detected_archetype_demo == ArchetypeType.HYBRID.value:
                if prime_score > longevity_score:
                    archetype = ArchetypeType.PRIME
                    confidence = 0.7 + (0.3 * min(prime_score / 5, 1))
                elif longevity_score > prime_score:
                    archetype = ArchetypeType.LONGEVITY
                    confidence = 0.7 + (0.3 * min(longevity_score / 5, 1))
                else:
                    # Si no hay señales claras, usar edad como desempate
                    archetype = ArchetypeType.PRIME if age < 50 else ArchetypeType.LONGEVITY
                    confidence = 0.5
            else:
                # Para edades fuera del rango híbrido, usar el arquetipo demográfico
                if detected_archetype_demo == ArchetypeType.PRIME.value:
                    archetype = ArchetypeType.PRIME
                    confidence = 0.9 if prime_score > 0 else 0.8
                else:
                    archetype = ArchetypeType.LONGEVITY
                    confidence = 0.9 if longevity_score > 0 else 0.8
            
            return {
                'archetype': archetype,
                'confidence': confidence,
                'reasoning': f"Basado en edad ({age}), señales PRIME ({prime_score}) y LONGEVITY ({longevity_score})"
            }
            
        except Exception as e:
            logger.error(f"Error determinando arquetipo: {e}")
            return {
                'archetype': ArchetypeType.PRIME,
                'confidence': 0.5,
                'reasoning': "Arquetipo por defecto debido a error"
            }
    
    def _calculate_tier_recommendation(
        self,
        demographic_score: Dict[str, Any],
        message_analysis: Dict[str, Any],
        behavioral_analysis: Dict[str, Any],
        price_sensitivity: str,
        archetype: ArchetypeType
    ) -> Dict[str, Any]:
        """Calcular recomendación de tier basada en todos los factores."""
        try:
            # Puntajes por tier
            tier_scores = {
                TierType.ESSENTIAL: 0,
                TierType.PRO: 0,
                TierType.ELITE: 0,
                TierType.PRIME_PREMIUM: 0,
                TierType.LONGEVITY_PREMIUM: 0
            }
            
            # Factor demográfico
            occupation_analysis = demographic_score.get('occupation_analysis', {})
            if occupation_analysis:
                suggested_tier = occupation_analysis.get('suggested_tier')
                if suggested_tier:
                    tier_scores[suggested_tier] += 5
            
            # Factor de edad
            age_analysis = demographic_score.get('age_analysis', {})
            if age_analysis:
                age_tier = age_analysis.get('tier_preference')
                if age_tier:
                    tier_scores[age_tier] += 3
            
            # Factor de mensaje y arquetipo
            budget_score = message_analysis.get('budget_score', 0)
            
            # Ajustar scores basados en el arquetipo detectado
            if archetype == ArchetypeType.PRIME:
                # PRIME tiende hacia Elite o Premium
                if budget_score >= 6:
                    tier_scores[TierType.PRIME_PREMIUM] += 6  # Más peso para PRIME Premium
                    tier_scores[TierType.ELITE] += 2
                elif budget_score >= 3:
                    tier_scores[TierType.ELITE] += 4
                    tier_scores[TierType.PRO] += 1
                else:
                    tier_scores[TierType.PRO] += 3
                    tier_scores[TierType.ESSENTIAL] += 1
            elif archetype == ArchetypeType.LONGEVITY:
                # LONGEVITY tiende hacia tiers más accesibles o Premium
                if budget_score >= 6:
                    tier_scores[TierType.LONGEVITY_PREMIUM] += 6  # Más peso para LONGEVITY Premium
                    tier_scores[TierType.ELITE] += 2
                elif budget_score >= 3:
                    tier_scores[TierType.ELITE] += 3
                    tier_scores[TierType.PRO] += 2
                else:
                    tier_scores[TierType.PRO] += 3
                    tier_scores[TierType.ESSENTIAL] += 2
            
            # Factor de sensibilidad al precio
            if price_sensitivity == "low":
                tier_scores[TierType.PRIME_PREMIUM] += 2
                tier_scores[TierType.ELITE] += 1
            elif price_sensitivity == "high":
                tier_scores[TierType.ESSENTIAL] += 2
                tier_scores[TierType.PRO] += 1
            
            # Factor de sofisticación
            sophistication = message_analysis.get('sophistication_level', 'medium')
            if sophistication == "high":
                tier_scores[TierType.ELITE] += 1
                tier_scores[TierType.PRIME_PREMIUM] += 1
            
            # Factor de engagement
            engagement = behavioral_analysis.get('conversation_depth', 'medium')
            if engagement == "high":
                tier_scores[TierType.ELITE] += 1
                tier_scores[TierType.PRIME_PREMIUM] += 1
            
            # Determinar tier ganador
            recommended_tier = max(tier_scores, key=tier_scores.get)
            max_score = tier_scores[recommended_tier]
            
            # Calcular confianza
            total_score = sum(tier_scores.values())
            confidence = max_score / total_score if total_score > 0 else 0.5
            
            # Determinar potencial de upsell
            upsell_potential = "high" if confidence > 0.7 else "medium" if confidence > 0.5 else "low"
            
            # Generar reasoning
            reasoning_parts = []
            if occupation_analysis:
                reasoning_parts.append(f"Profesión: {occupation_analysis.get('detected_profession', 'detectada')}")
            if budget_score > 0:
                reasoning_parts.append(f"Señales de presupuesto: {budget_score}")
            if price_sensitivity != "medium":
                reasoning_parts.append(f"Sensibilidad al precio: {price_sensitivity}")
            
            reasoning = f"Recomendado por: {', '.join(reasoning_parts) if reasoning_parts else 'análisis general'}"
            
            return {
                'tier': recommended_tier,
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'upsell_potential': upsell_potential,
                'tier_scores': tier_scores
            }
            
        except Exception as e:
            logger.error(f"Error calculando recomendación: {e}")
            return {
                'tier': TierType.PRO,
                'confidence': 0.5,
                'reasoning': 'Tier por defecto',
                'upsell_potential': 'medium',
                'tier_scores': {}
            }
    
    def _calculate_roi_projection(self, user_profile: Dict[str, Any], tier_recommendation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calcular proyección de ROI para el tier recomendado."""
        try:
            occupation = user_profile.get('occupation', '').lower()
            
            # Buscar tarifa por hora estimada
            hourly_rate = None
            for prof, data in self.income_indicators.items():
                if prof in occupation:
                    hourly_rate = data['hourly_rate']
                    break
            
            if not hourly_rate or hourly_rate == 0:
                return None
            
            recommended_tier = tier_recommendation['tier']
            monthly_cost = self.tier_pricing[recommended_tier]
            
            # Calcular ROI conservador
            if recommended_tier in [TierType.ESSENTIAL, TierType.PRO, TierType.ELITE]:
                # Para suscripciones mensuales
                productivity_hours_gain = 2 if recommended_tier == TierType.ESSENTIAL else 3 if recommended_tier == TierType.PRO else 4
                working_days_month = 22
                
                monthly_productivity_value = hourly_rate * productivity_hours_gain * working_days_month
                monthly_roi = ((monthly_productivity_value - monthly_cost) / monthly_cost) * 100
                payback_days = monthly_cost / (hourly_rate * productivity_hours_gain)
                
                return {
                    'monthly_cost': monthly_cost,
                    'productivity_hours_gain': productivity_hours_gain,
                    'monthly_productivity_value': monthly_productivity_value,
                    'monthly_roi': round(monthly_roi, 0),
                    'payback_days': round(payback_days, 1),
                    'annual_value': monthly_productivity_value * 12
                }
            else:
                # Para programas premium
                productivity_hours_gain = 5
                working_days_year = 250
                
                annual_productivity_value = hourly_rate * productivity_hours_gain * working_days_year
                annual_roi = ((annual_productivity_value - monthly_cost) / monthly_cost) * 100
                payback_days = monthly_cost / (hourly_rate * productivity_hours_gain)
                
                return {
                    'program_cost': monthly_cost,
                    'productivity_hours_gain': productivity_hours_gain,
                    'annual_productivity_value': annual_productivity_value,
                    'annual_roi': round(annual_roi, 0),
                    'payback_days': round(payback_days, 1),
                    'monthly_equivalent_value': annual_productivity_value / 12
                }
            
        except Exception as e:
            logger.error(f"Error calculando ROI: {e}")
            return None
    
    async def adjust_tier_based_on_objection(
        self,
        current_tier: TierType,
        objection_message: str,
        user_profile: Dict[str, Any]
    ) -> TierDetectionResult:
        """Ajustar tier basado en objeciones del usuario."""
        try:
            objection_lower = objection_message.lower()
            
            # Detectar tipo de objeción
            if any(word in objection_lower for word in ['caro', 'precio', 'costoso', 'mucho dinero']):
                # Objeción de precio - bajar tier
                tier_hierarchy = [
                    TierType.PRIME_PREMIUM, TierType.LONGEVITY_PREMIUM,
                    TierType.ELITE, TierType.PRO, TierType.ESSENTIAL
                ]
                
                current_index = tier_hierarchy.index(current_tier)
                if current_index < len(tier_hierarchy) - 1:
                    adjusted_tier = tier_hierarchy[current_index + 1]
                else:
                    adjusted_tier = current_tier
                
                return TierDetectionResult(
                    recommended_tier=adjusted_tier,
                    confidence=0.8,
                    reasoning=f"Ajustado de {current_tier.value} a {adjusted_tier.value} por objeción de precio",
                    price_point=f"${self.tier_pricing[adjusted_tier]}/mes" if adjusted_tier in [TierType.ESSENTIAL, TierType.PRO, TierType.ELITE] else f"${self.tier_pricing[adjusted_tier]}",
                    upsell_potential="medium",
                    demographic_factors={},
                    behavioral_signals=["price_objection"],
                    price_sensitivity="high"
                )
            
            # Si no hay objeción de precio, mantener tier actual
            return TierDetectionResult(
                recommended_tier=current_tier,
                confidence=0.7,
                reasoning="Tier mantenido - objeción no relacionada con precio",
                price_point=f"${self.tier_pricing[current_tier]}/mes" if current_tier in [TierType.ESSENTIAL, TierType.PRO, TierType.ELITE] else f"${self.tier_pricing[current_tier]}",
                upsell_potential="medium",
                demographic_factors={},
                behavioral_signals=["objection_handled"],
                price_sensitivity="medium"
            )
            
        except Exception as e:
            logger.error(f"Error ajustando tier por objeción: {e}")
            return TierDetectionResult(
                recommended_tier=current_tier,
                confidence=0.5,
                reasoning="Error en ajuste, tier mantenido",
                price_point=f"${self.tier_pricing[current_tier]}/mes" if current_tier in [TierType.ESSENTIAL, TierType.PRO, TierType.ELITE] else f"${self.tier_pricing[current_tier]}",
                upsell_potential="low",
                demographic_factors={},
                behavioral_signals=["error"],
                price_sensitivity="unknown"
            )
    
    async def track_tier_progression(self, conversation_id: str, tier_progression: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Trackear progresión de tier durante la conversación."""
        try:
            if not tier_progression:
                return {
                    'conversation_id': conversation_id,
                    'tier_progression': [],
                    'final_tier': None,
                    'progression_score': 0.0
                }
            
            # Analizar progresión
            initial_tier = tier_progression[0]['tier']
            final_tier = tier_progression[-1]['tier']
            
            # Calcular score de progresión
            tier_values = {
                TierType.ESSENTIAL: 1,
                TierType.PRO: 2,
                TierType.ELITE: 3,
                TierType.PRIME_PREMIUM: 4,
                TierType.LONGEVITY_PREMIUM: 4
            }
            
            initial_value = tier_values.get(initial_tier, 1)
            final_value = tier_values.get(final_tier, 1)
            
            progression_score = min(final_value / initial_value, 2.0)  # Max 2.0 para upgrade significativo
            
            return {
                'conversation_id': conversation_id,
                'tier_progression': tier_progression,
                'final_tier': final_tier,
                'progression_score': round(progression_score, 2),
                'tier_upgrades': final_value - initial_value,
                'progression_analysis': 'upgraded' if final_value > initial_value else 'maintained' if final_value == initial_value else 'downgraded'
            }
            
        except Exception as e:
            logger.error(f"Error tracking tier progression: {e}")
            return {
                'conversation_id': conversation_id,
                'tier_progression': [],
                'final_tier': None,
                'progression_score': 0.0,
                'error': str(e)
            }
    
    async def detect_tier(
        self,
        messages: List[str],
        customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Método wrapper para compatibilidad con el test.
        Mapea a detect_optimal_tier con la interfaz correcta.
        
        Args:
            messages: Lista de mensajes del usuario
            customer_data: Datos del cliente
            
        Returns:
            Dict con tier detectado y metadata
        """
        # Tomar el último mensaje o crear uno genérico
        user_message = messages[-1] if messages else "Hola, busco información"
        
        # Crear historial de conversación si hay múltiples mensajes
        conversation_history = []
        if len(messages) > 1:
            for i, msg in enumerate(messages):
                conversation_history.append({
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": msg
                })
        
        # Llamar al método principal
        result = await self.detect_optimal_tier(
            user_message=user_message,
            user_profile=customer_data,
            conversation_history=conversation_history
        )
        
        # Convertir resultado a formato esperado por el test
        return {
            "tier": result.recommended_tier.value if hasattr(result.recommended_tier, 'value') else str(result.recommended_tier),
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "price_point": result.price_point,
            "upsell_potential": result.upsell_potential,
            "detected_archetype": result.detected_archetype.value if hasattr(result.detected_archetype, 'value') else str(result.detected_archetype),
            "archetype_confidence": result.archetype_confidence
        }
    
    async def cleanup(self):
        """
        Cleanup resources and stop background tasks.
        
        This should be called when shutting down the service.
        """
        logger.info("Cleaning up TierDetectionService")
        
        try:
            # Unregister from task registry
            if self.task_manager:
                registry = get_task_registry()
                await registry.unregister_service("tier_detection")
                self.task_manager = None
            
            logger.info("TierDetectionService cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during TierDetectionService cleanup: {e}")