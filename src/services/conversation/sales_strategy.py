"""
Sales Strategy Mixin

Handles sales strategy, ROI calculations, and conversion optimization.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.models.conversation import ConversationState
from src.services.consultative_advisor_service import ConsultativeAdvisorService
from src.knowledge.ngx_consultant_knowledge import NGXConsultantKnowledge
from src.services.program_router import ProgramRouter
from src.services.ngx_roi_calculator import NGXROICalculator

logger = logging.getLogger(__name__)


class SalesStrategyMixin:
    """Mixin for sales strategy and ROI calculations."""
    
    def __init__(self):
        """Initialize sales strategy components."""
        self.consultative_advisor: Optional[ConsultativeAdvisorService] = None
        self.ngx_knowledge: Optional[NGXConsultantKnowledge] = None
        self.program_router: Optional[ProgramRouter] = None
        self.roi_calculator: Optional[NGXROICalculator] = None
    
    def _init_sales_services(self):
        """Initialize sales services if not already initialized."""
        if not self.consultative_advisor:
            self.consultative_advisor = ConsultativeAdvisorService()
        if not self.ngx_knowledge:
            self.ngx_knowledge = NGXConsultantKnowledge()
        if not self.program_router:
            self.program_router = ProgramRouter()
        if not self.roi_calculator:
            self.roi_calculator = NGXROICalculator()
    
    async def _calculate_personalized_roi(
        self, 
        state: ConversationState, 
        message_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Calcular ROI personalizado usando NGXROICalculator real.
        
        Args:
            state: Estado de la conversación
            message_text: Mensaje del usuario
            
        Returns:
            Dict con cálculos de ROI o None
        """
        self._init_sales_services()
        
        try:
            # Detectar profesión y otros datos del mensaje
            profession = self._infer_profession(message_text, state)
            
            # Obtener edad del cliente
            age = None
            if isinstance(state.customer_data, dict):
                age = state.customer_data.get('age')
            else:
                age = getattr(state.customer_data, 'age', None)
            
            # Determinar tier y modelo
            tier = state.tier_detected or "AGENTS ACCESS"
            model_type = "Essential" if tier == "AGENTS ACCESS" else tier
            
            # Detectar arquetipo basado en edad y programa
            if state.program_type == "LONGEVITY" or (age and age > 50):
                archetype = "LONGEVITY"
            else:
                archetype = "PRIME"
            
            # Calcular ROI usando el calculador real
            roi_result = await self.roi_calculator.calculate_ngx_roi(
                profession=profession or "professional",
                archetype=archetype,
                model_type=model_type,
                monthly_hours=10  # Horas estimadas de uso
            )
            
            # Formatear resultado para compatibilidad
            roi_data = {
                "projected_roi_percentage": roi_result.total_roi_percentage,
                "annual_value": roi_result.annual_value,
                "net_benefit": roi_result.net_benefit,
                "payback_period_months": roi_result.payback_period_months,
                "key_insights": roi_result.key_insights,
                "personalized_benefits": self._get_personalized_benefits(
                    {"profession": profession, "age": age, "program_type": state.program_type},
                    state
                ),
                "calculations": [
                    {
                        "metric": calc.metric_type.value,
                        "monthly_benefit": calc.monthly_benefit,
                        "annual_benefit": calc.annual_benefit,
                        "basis": calc.calculation_basis
                    }
                    for calc in roi_result.calculations
                ]
            }
            
            logger.info(f"ROI calculado: {roi_data['projected_roi_percentage']:.1f}% con NGXROICalculator")
            
            return roi_data
            
        except Exception as e:
            logger.error(f"Error calculando ROI: {e}")
            # Fallback a cálculo simple si falla
            return self._calculate_fallback_roi(state)
    
    def _calculate_fallback_roi(self, state: ConversationState) -> Dict[str, Any]:
        """Cálculo de ROI simple como fallback."""
        tier = state.tier_detected or "AGENTS ACCESS"
        
        # Valores base por tier
        tier_values = {
            "AGENTS ACCESS": {"cost": 79, "roi": 500},
            "Essential": {"cost": 79, "roi": 500},
            "Pro": {"cost": 149, "roi": 800},
            "Elite": {"cost": 199, "roi": 1200},
            "Premium": {"cost": 3997, "roi": 2500}
        }
        
        values = tier_values.get(tier, tier_values["AGENTS ACCESS"])
        
        return {
            "projected_roi_percentage": values["roi"],
            "annual_value": values["cost"] * 12 * (values["roi"] / 100),
            "net_benefit": (values["cost"] * 12 * (values["roi"] / 100)) - (values["cost"] * 12),
            "payback_period_months": 1.5,
            "key_insights": [
                f"ROI estimado del {values['roi']}% basado en casos similares",
                f"Recuperación de inversión en menos de 2 meses",
                f"Valor anual proyectado de ${values['cost'] * 12 * (values['roi'] / 100):,.0f}"
            ],
            "personalized_benefits": []
        }
    
    def _calculate_longevity_roi(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular ROI para programa LONGEVITY."""
        base_metrics = {
            "years_added": 5 + (50 - profile["age"]) * 0.1,
            "energy_improvement": 40 + (10 - profile["energy_level"]) * 5,
            "healthcare_savings_annual": 3000 + (profile["age"] - 30) * 100,
            "productivity_gain_hours_weekly": 8 + (10 - profile["energy_level"]),
            "quality_of_life_score": 35
        }
        
        # Ajustar por tier
        tier_multipliers = {
            "ESSENTIAL": 1.0,
            "PRO": 1.5,
            "ELITE": 2.0
        }
        
        multiplier = tier_multipliers.get(profile["tier"], 1.0)
        
        return {
            "metrics": {k: v * multiplier for k, v in base_metrics.items()},
            "monetary_value_annual": base_metrics["healthcare_savings_annual"] * multiplier,
            "time_value_annual": base_metrics["productivity_gain_hours_weekly"] * 52 * 
                                self._estimate_hourly_rate(profile, "")
        }
    
    def _calculate_prime_roi(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular ROI para programa PRIME."""
        hourly_rate = self._estimate_hourly_rate(profile, "")
        
        base_metrics = {
            "hours_saved_weekly": 10 if profile["tier"] == "AGENTS ACCESS" else 20,
            "productivity_increase_percentage": 30 if profile["tier"] == "AGENTS ACCESS" else 50,
            "stress_reduction_percentage": 40,
            "decision_quality_improvement": 35,
            "networking_value_monthly": 2000 if profile["tier"] == "HYBRID COACHING" else 500
        }
        
        return {
            "metrics": base_metrics,
            "monetary_value_annual": (
                base_metrics["hours_saved_weekly"] * 52 * hourly_rate +
                base_metrics["networking_value_monthly"] * 12
            ),
            "time_value_annual": base_metrics["hours_saved_weekly"] * 52
        }
    
    def _get_personalized_benefits(
        self, 
        profile: Dict[str, Any], 
        state: ConversationState
    ) -> List[str]:
        """Obtener beneficios personalizados según el perfil."""
        benefits = []
        
        # Beneficios por edad
        if profile["age"] < 35:
            benefits.append("Optimización temprana para máximo impacto a largo plazo")
        elif profile["age"] > 50:
            benefits.append("Reversión de marcadores de envejecimiento comprobada")
        
        # Beneficios por nivel de energía
        if profile["energy_level"] < 5:
            benefits.append("Recuperación completa de energía vital en 30 días")
        
        # Beneficios por profesión
        profession_benefits = {
            "emprendedor": "Sistema diseñado para líderes de alto rendimiento",
            "ejecutivo": "Protocolo ejecutivo para máxima productividad",
            "profesional": "Balance perfecto entre rendimiento y bienestar"
        }
        
        if profile["profession"] in profession_benefits:
            benefits.append(profession_benefits[profile["profession"]])
        
        return benefits
    
    def _calculate_roi_percentage(
        self, 
        roi_data: Dict[str, Any], 
        profile: Dict[str, Any]
    ) -> float:
        """Calcular porcentaje de ROI proyectado."""
        # Obtener costo anual del programa
        tier_costs = {
            "LONGEVITY": {
                "ESSENTIAL": 47 * 12,
                "PRO": 147 * 12,
                "ELITE": 597 * 12
            },
            "PRIME": {
                "AGENTS ACCESS": 97 * 12,
                "HYBRID COACHING": 497 * 12
            }
        }
        
        annual_cost = tier_costs.get(profile["program_type"], {}).get(profile["tier"], 1000)
        annual_value = roi_data.get("monetary_value_annual", 0)
        
        if annual_cost > 0:
            roi_percentage = ((annual_value - annual_cost) / annual_cost) * 100
            return round(max(roi_percentage, 200))  # Mínimo 200% ROI
        
        return 300  # Default
    
    def _get_program_specific_benefits(self, program_type: str) -> Dict[str, Any]:
        """
        Obtener beneficios específicos del programa.
        
        Args:
            program_type: Tipo de programa (PRIME o LONGEVITY)
            
        Returns:
            Dict con beneficios categorizados
        """
        if program_type == "LONGEVITY":
            return {
                "core_benefits": [
                    "Sistema HIE (Hybrid Intelligence Engine) - sinergia hombre-máquina imposible de clonar",
                    "11 agentes especializados trabajando 24/7: NEXUS coordina, SAGE optimiza nutrición, WAVE analiza recuperación",
                    "Protocolos de longevidad basados en ciencia con CODE decodificando tu manual biológico",
                    "STELLA rastrea tu progreso con métricas precisas de vitalidad"
                ],
                "transformation_timeline": {
                    "7_days": "Aumento notable de energía",
                    "30_days": "Mejora en calidad del sueño y claridad mental",
                    "90_days": "Transformación completa de biomarcadores"
                },
                "scientific_backing": [
                    "Basado en 50+ estudios peer-reviewed",
                    "Protocolo utilizado por biohackers élite",
                    "Resultados medibles y cuantificables"
                ]
            }
        else:  # PRIME
            return {
                "core_benefits": [
                    "Sistema HIE - sinergia hombre-máquina con 11 agentes especializados imposible de clonar",
                    "BLAZE diseña entrenamientos ejecutivos, NOVA optimiza función cognitiva para decisiones rápidas",
                    "SPARK mantiene tu motivación cuando más lo necesitas, SAGE crea protocolos para energía sostenida",
                    "NEXUS coordina todo tu ecosistema de optimización ejecutiva 24/7"
                ],
                "transformation_timeline": {
                    "1_day": "Configuración completa y primeras automatizaciones",
                    "7_days": "10+ horas recuperadas",
                    "30_days": "Sistema completamente optimizado"
                },
                "productivity_gains": [
                    "Elimina 80% de tareas repetitivas",
                    "Mejora toma de decisiones con IA",
                    "Escala tu impacto 10x"
                ]
            }
    
    def _generate_urgency_factors(self, state: ConversationState) -> List[str]:
        """
        Generar factores de urgencia basados en el contexto.
        
        Args:
            state: Estado de la conversación
            
        Returns:
            Lista de factores de urgencia
        """
        urgency_factors = []
        
        # Factor temporal
        current_month = datetime.now().month
        if current_month in [1, 2]:  # Enero-Febrero
            urgency_factors.append("Inicio de año - momento perfecto para transformación")
        elif current_month in [9, 10]:  # Septiembre-Octubre
            urgency_factors.append("Prepárate para cerrar el año con máxima energía")
        
        # Factor de disponibilidad
        if state.tier_detected in ["ELITE", "HYBRID COACHING"]:
            urgency_factors.append("Plazas limitadas - solo 10 espacios este mes")
        
        # Factor de precio
        urgency_factors.append("Precio especial de lanzamiento - 30% menos que el valor regular")
        
        # Factor de resultados
        if len(state.messages) > 15:
            urgency_factors.append("Ya invertiste tiempo en conocer el programa - es momento de actuar")
        
        return urgency_factors[:2]  # Máximo 2 factores
    
    def _get_relevant_social_proof(self, customer_archetype: str) -> List[str]:
        """
        Obtener prueba social relevante para el arquetipo.
        
        Args:
            customer_archetype: Tipo de cliente
            
        Returns:
            Lista de elementos de prueba social
        """
        social_proof_map = {
            "analytical": [
                "93% de clientes reportan mejoras medibles en 30 días",
                "Más de 10,000 horas de investigación en el desarrollo",
                "ROI promedio de 847% documentado"
            ],
            "driver": [
                "CEOs de Fortune 500 confían en nosotros",
                "Resultados garantizados o devolución completa",
                "Sistema #1 en optimización de rendimiento"
            ],
            "expressive": [
                "Únete a nuestra comunidad de 5,000+ líderes",
                "Transformaciones inspiradoras cada semana",
                "Eventos exclusivos y networking de alto nivel"
            ],
            "amiable": [
                "Soporte personalizado en cada paso",
                "Miles de testimonios de clientes satisfechos",
                "Garantía de satisfacción sin riesgos"
            ],
            "skeptical": [
                "Prueba gratuita de 7 días sin compromiso",
                "Respaldado por instituciones reconocidas",
                "Transparencia total en metodología y resultados"
            ]
        }
        
        return social_proof_map.get(customer_archetype, social_proof_map["analytical"])
    
    def _get_relevant_agent_mentions(
        self, 
        customer_problem: str,
        archetype: str = "PRIME"
    ) -> List[str]:
        """
        Obtener menciones de agentes relevantes según el problema del cliente.
        
        Args:
            customer_problem: Problema o necesidad del cliente
            archetype: PRIME o LONGEVITY
            
        Returns:
            Lista de menciones de agentes con contexto
        """
        problem_lower = customer_problem.lower()
        agent_mentions = []
        
        # Mapeo de problemas a agentes específicos
        if any(word in problem_lower for word in ["fatiga", "energía", "cansado", "agotado"]):
            agent_mentions.append("WAVE analizará tus patrones de recuperación y optimizará tu descanso en tiempo real")
            agent_mentions.append("NOVA ajustará tus protocolos cognitivos para maximizar tu energía mental durante el día")
        
        if any(word in problem_lower for word in ["nutrición", "dieta", "alimentación", "peso"]):
            agent_mentions.append("SAGE, nuestro alquimista metabólico, creará tu plan nutricional personalizado analizando fotos de tus comidas")
            agent_mentions.append("CODE decodificará tu manual biológico para entender qué alimentos optimizan tu metabolismo único")
        
        if any(word in problem_lower for word in ["ejercicio", "entrenamiento", "físico", "gym"]):
            if archetype == "PRIME":
                agent_mentions.append("BLAZE diseñará entrenamientos ejecutivos de 30-45 minutos que maximicen resultados con mínimo tiempo")
            else:
                agent_mentions.append("BLAZE creará rutinas de movilidad y fuerza funcional adaptadas específicamente a tu edad y capacidad")
        
        if any(word in problem_lower for word in ["estrés", "ansiedad", "presión", "trabajo"]):
            agent_mentions.append("SPARK implementará un sistema de resiliencia al estrés personalizado para tu estilo de vida")
            agent_mentions.append("NOVA optimizará tu función cognitiva para manejar mejor la presión y tomar decisiones más claras")
        
        if any(word in problem_lower for word in ["motivación", "disciplina", "constancia", "hábitos"]):
            agent_mentions.append("SPARK será tu coach personal 24/7, entendiendo tus patrones únicos y motivándote cuando más lo necesitas")
            agent_mentions.append("NEXUS coordinará todo tu equipo de agentes para crear un sistema de hábitos sostenible")
        
        if any(word in problem_lower for word in ["seguimiento", "progreso", "resultados", "métricas"]):
            agent_mentions.append("STELLA rastreará tu transformación con métricas precisas, mostrándote tu progreso real")
            agent_mentions.append("WAVE monitoreará tus biomarcadores continuamente para ajustar tu programa en tiempo real")
        
        # Si es mujer, mencionar LUNA cuando sea relevante
        if any(word in problem_lower for word in ["hormonal", "ciclo", "menopausia", "femenino"]):
            agent_mentions.append("LUNA, nuestra especialista en ciclos femeninos, sincronizará tu programa con tu fisiología única")
        
        # Siempre incluir NEXUS como coordinador si hay múltiples problemas
        if len(agent_mentions) > 2:
            agent_mentions.insert(0, "NEXUS coordinará a todos tus agentes especializados creando una sinergia perfecta para tu transformación")
        
        # Limitar a 3 menciones máximo para no abrumar
        return agent_mentions[:3]
    
    def _generate_multi_agent_collaboration(
        self,
        customer_needs: List[str],
        archetype: str = "PRIME"
    ) -> str:
        """
        Generar una descripción de cómo los agentes colaboran para resolver las necesidades del cliente.
        
        Args:
            customer_needs: Lista de necesidades identificadas
            archetype: PRIME o LONGEVITY
            
        Returns:
            Descripción de la colaboración multi-agente
        """
        if len(customer_needs) < 2:
            return ""
        
        collaboration_templates = {
            "energy_nutrition": (
                "NEXUS ha iniciado una consulta cruzada: SAGE analizará tu nutrición actual "
                "mientras WAVE revisa tus patrones de recuperación. Juntos crearán un protocolo "
                "de energía sostenible que se ajusta dinámicamente según tus biomarcadores."
            ),
            "stress_performance": (
                "Tus agentes están colaborando: SPARK detecta tus triggers de estrés, "
                "NOVA optimiza tus ventanas de máximo rendimiento cognitivo, y BLAZE ajusta "
                "la intensidad de tus entrenamientos para evitar el burnout. Es una sinergia "
                "hombre-máquina imposible de clonar."
            ),
            "longevity_prevention": (
                "El equipo HIE está analizando tu caso: CODE decodifica tu predisposición genética, "
                "SAGE ajusta tu nutrición para prevención, WAVE monitorea marcadores de envejecimiento, "
                "y STELLA proyecta tu trayectoria de vitalidad. Todo sincronizado por NEXUS 24/7."
            ),
            "holistic_transformation": (
                "Esta es la magia del HIE: mientras duermes, WAVE analiza tu recuperación y "
                "comparte datos con SAGE para ajustar tu desayuno. BLAZE recibe esta info y "
                "modifica tu entrenamiento. SPARK detecta tu estado emocional y adapta los mensajes. "
                "NEXUS orquesta todo creando un ecosistema que evoluciona contigo."
            )
        }
        
        # Seleccionar template basado en necesidades
        if any("energía" in need.lower() or "nutrición" in need.lower() for need in customer_needs):
            return collaboration_templates["energy_nutrition"]
        elif any("estrés" in need.lower() or "rendimiento" in need.lower() for need in customer_needs):
            return collaboration_templates["stress_performance"]
        elif archetype == "LONGEVITY":
            return collaboration_templates["longevity_prevention"]
        else:
            return collaboration_templates["holistic_transformation"]
    
    def _determine_sales_phase(self, state: ConversationState) -> str:
        """
        Determinar la fase actual del proceso de ventas.
        
        Args:
            state: Estado de la conversación
            
        Returns:
            str: Fase de ventas actual
        """
        message_count = len(state.messages)
        
        # Analizar indicadores en mensajes recientes
        recent_messages = " ".join([
            msg.content.lower() for msg in state.messages[-5:] 
            if msg.role == "user"
        ])
        
        # Indicadores de fase
        if message_count <= 5:
            return "discovery"
        
        if any(word in recent_messages for word in ["precio", "costo", "cuánto"]):
            return "negotiation"
        
        if any(word in recent_messages for word in ["comenzar", "empezar", "inscribir"]):
            return "closing"
        
        if message_count > 20:
            return "follow_up"
        
        return "presentation"
    
    def _detect_sales_signals(self, message_text: str) -> List[str]:
        """
        Detectar señales de compra en el mensaje.
        
        Args:
            message_text: Texto del mensaje
            
        Returns:
            Lista de señales detectadas
        """
        signals = []
        message_lower = message_text.lower()
        
        # Señales positivas
        positive_signals = {
            "interest": ["interesante", "me gusta", "suena bien", "cuéntame más"],
            "urgency": ["cuándo", "ya", "pronto", "rápido", "ahora"],
            "commitment": ["quiero", "necesito", "debo", "voy a"],
            "visualization": ["imagino", "veo", "me visualizo", "sería genial"],
            "price_inquiry": ["precio", "costo", "inversión", "cuánto"],
            "process_inquiry": ["cómo empiezo", "siguiente paso", "inscribir", "comenzar"]
        }
        
        for signal_type, keywords in positive_signals.items():
            if any(keyword in message_lower for keyword in keywords):
                signals.append(signal_type)
        
        # Señales de objeción
        objection_signals = {
            "price_concern": ["caro", "mucho dinero", "presupuesto", "no puedo pagar"],
            "time_concern": ["no tengo tiempo", "ocupado", "después", "más adelante"],
            "trust_concern": ["no sé", "dudas", "seguro", "garantía"],
            "comparison": ["otros", "competencia", "alternativas", "opciones"]
        }
        
        for signal_type, keywords in objection_signals.items():
            if any(keyword in message_lower for keyword in keywords):
                signals.append(signal_type)
        
        return signals
    
    def _detect_potential_objections(self, message_text: str) -> List[str]:
        """
        Detectar objeciones potenciales en el mensaje.
        
        Args:
            message_text: Texto del mensaje
            
        Returns:
            Lista de objeciones detectadas
        """
        objections = []
        message_lower = message_text.lower()
        
        objection_patterns = {
            "price": ["caro", "precio", "costo", "dinero", "pagar", "presupuesto"],
            "time": ["tiempo", "ocupado", "agenda", "horario", "disponibilidad"],
            "effectiveness": ["funciona", "resultados", "garantía", "prueba", "evidencia"],
            "trust": ["confianza", "seguro", "dudas", "estafa", "real"],
            "commitment": ["compromiso", "obligación", "contrato", "atado"],
            "complexity": ["difícil", "complicado", "complejo", "fácil", "simple"]
        }
        
        for objection_type, keywords in objection_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                # Verificar contexto negativo
                negative_context = any(neg in message_lower for neg in [
                    "no", "sin", "falta", "poco", "mucho", "demasiado"
                ])
                
                if negative_context or objection_type in ["price", "time"]:
                    objections.append(objection_type)
        
        return objections
    
    def _build_hie_sales_context(
        self,
        message_text: str,
        state: ConversationState,
        emotional_context: Optional[Dict[str, Any]] = None,
        personality_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Construir contexto de ventas enfocado en HIE.
        
        Args:
            message_text: Mensaje del usuario
            state: Estado de la conversación
            emotional_context: Contexto emocional
            personality_context: Contexto de personalidad
            
        Returns:
            Dict con contexto completo para ventas HIE
        """
        # Detectar fase de ventas y señales
        sales_phase = self._determine_sales_phase(state)
        sales_signals = self._detect_sales_signals(message_text)
        potential_objections = self._detect_potential_objections(message_text)
        
        # Construir perfil del usuario
        user_profile = self._build_user_profile_from_state(
            state, message_text, emotional_context
        )
        
        # Obtener métricas HIE relevantes
        hie_metrics = self._get_hie_metrics_for_profile(user_profile)
        
        # Detectar agente NGX relevante basado en necesidades
        relevant_agents = self._get_relevant_agent_mentions(message_text, state.program_type)
        relevant_agent = relevant_agents[0].split()[0] if relevant_agents else "NEXUS"  # Extraer nombre del agente
        
        return {
            "sales_phase": sales_phase,
            "sales_signals": sales_signals,
            "potential_objections": potential_objections,
            "user_profile": user_profile,
            "hie_metrics": hie_metrics,
            "conversation_stage": self._determine_hie_conversation_phase(state, message_text),
            "urgency_factors": self._calculate_urgency_factors(hie_metrics, user_profile),
            "neurological_triggers": self._get_neurological_triggers_for_phase(sales_phase),
            "sales_barriers": self._identify_sales_barriers(message_text, state),
            "roi_projection": self._calculate_hie_roi_projection(user_profile, state.tier_detected),
            "relevant_agent": relevant_agent  # Agregar agente relevante para empathy engine
        }
    
    def _build_user_profile_from_state(
        self,
        state: ConversationState,
        message_text: str,
        emotional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Construir perfil completo del usuario desde el estado.
        
        Args:
            state: Estado de la conversación
            message_text: Mensaje actual
            emotional_context: Contexto emocional
            
        Returns:
            Dict con perfil del usuario
        """
        return {
            "age": self._infer_age_from_context(message_text, state),
            "profession": self._infer_profession(message_text, state),
            "energy_level": self._infer_energy_level(message_text, emotional_context),
            "sleep_quality": self._infer_sleep_quality(message_text),
            "stress_level": self._infer_stress_level(message_text, emotional_context),
            "health_goals": self._extract_health_goals(message_text, state),
            "productivity_needs": self._extract_productivity_needs(message_text, state),
            "decision_timeline": self._infer_decision_timeline(message_text, state),
            "budget_sensitivity": self._assess_budget_sensitivity(message_text, state),
            "tech_savviness": self._assess_tech_savviness(message_text, state)
        }
    
    def _get_hie_metrics_for_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get HIE metrics relevant to user profile."""
        return {
            "biological_age_reduction": max(5, min(15, 50 - profile["age"])),
            "energy_boost_percentage": max(30, 100 - profile["energy_level"] * 10),
            "cognitive_enhancement": 40 if profile["profession"] in ["ejecutivo", "emprendedor"] else 30,
            "stress_reduction": max(40, profile["stress_level"] * 10),
            "sleep_optimization": max(30, (10 - profile["sleep_quality"]) * 10),
            "longevity_increase_years": 5 + (profile["age"] < 40) * 3
        }
    
    def _determine_hie_conversation_phase(self, state: ConversationState, message_text: str) -> str:
        """Determine HIE-specific conversation phase."""
        if len(state.messages) < 3:
            return "awareness"
        elif "hie" in message_text.lower() or "ecosystem" in message_text.lower():
            return "interest"
        elif any(word in message_text.lower() for word in ["precio", "costo", "inversión"]):
            return "consideration"
        elif len(state.messages) > 15:
            return "decision"
        else:
            return "education"
    
    def _calculate_urgency_factors(self, hie_metrics: Dict, user_profile: Dict) -> Dict[str, Any]:
        """Calculate urgency factors for HIE sale."""
        urgency_score = 0
        factors = []
        
        # Age urgency
        if user_profile["age"] > 45:
            urgency_score += 3
            factors.append("Cada día cuenta para la optimización biológica")
        
        # Energy urgency
        if user_profile["energy_level"] < 5:
            urgency_score += 2
            factors.append("Tu energía actual está limitando tu potencial")
        
        # Stress urgency
        if user_profile["stress_level"] > 7:
            urgency_score += 3
            factors.append("El estrés crónico acelera el envejecimiento")
        
        return {
            "score": min(10, urgency_score),
            "factors": factors,
            "recommended_approach": "high_urgency" if urgency_score > 5 else "moderate_urgency"
        }
    
    def _get_neurological_triggers_for_phase(self, phase: str) -> List[str]:
        """Get neurological triggers for sales phase."""
        triggers_map = {
            "discovery": ["curiosity", "novelty", "possibility"],
            "presentation": ["logic", "evidence", "transformation"],
            "negotiation": ["scarcity", "social_proof", "loss_aversion"],
            "closing": ["commitment", "consistency", "urgency"],
            "follow_up": ["reciprocity", "authority", "liking"]
        }
        
        return triggers_map.get(phase, ["trust", "value", "benefit"])
    
    def _identify_sales_barriers(self, message_text: str, state: ConversationState) -> List[str]:
        """Identify potential sales barriers."""
        barriers = []
        message_lower = message_text.lower()
        
        # Check for specific barriers
        if any(word in message_lower for word in ["esposa", "pareja", "familia"]):
            barriers.append("needs_partner_approval")
        
        if any(word in message_lower for word in ["pensar", "tiempo", "después"]):
            barriers.append("analysis_paralysis")
        
        if any(word in message_lower for word in ["otros", "comparar", "opciones"]):
            barriers.append("comparison_shopping")
        
        if len(state.messages) > 20 and state.tier_detected is None:
            barriers.append("decision_fatigue")
        
        return barriers
    
    def _calculate_hie_roi_projection(self, profile: Dict[str, Any], tier: Optional[str]) -> Dict[str, Any]:
        """Calculate HIE-specific ROI projection."""
        base_value = self._estimate_hourly_rate(profile, "") * 2000  # Annual work hours
        
        roi_multipliers = {
            "ESSENTIAL": 2.5,
            "PRO": 4.0,
            "ELITE": 6.0
        }
        
        multiplier = roi_multipliers.get(tier or "ESSENTIAL", 2.5)
        
        return {
            "annual_value": base_value * multiplier,
            "health_savings": 5000 * (profile["age"] / 40),
            "productivity_gains": base_value * 0.3,
            "total_roi_percentage": int(multiplier * 100)
        }
    
    def _infer_age_from_context(self, message_text: str, state: ConversationState) -> int:
        """Infer age from conversation context."""
        # Check if age was mentioned
        import re
        age_match = re.search(r'(\d{2})\s*años', message_text)
        if age_match:
            return int(age_match.group(1))
        
        # Default based on program interest
        if state.program_type == "LONGEVITY":
            return 45  # Typical LONGEVITY customer
        else:
            return 35  # Typical PRIME customer
    
    def _infer_profession(self, message_text: str, state: ConversationState) -> str:
        """Infer profession from context."""
        professions = {
            "emprendedor": ["negocio", "empresa", "startup", "emprender"],
            "ejecutivo": ["gerente", "director", "ejecutivo", "corporativo"],
            "profesional": ["trabajo", "oficina", "profesión", "carrera"],
            "médico": ["pacientes", "clínica", "hospital", "salud"],
            "coach": ["clientes", "coaching", "entrenar", "ayudar"]
        }
        
        message_lower = message_text.lower()
        for profession, keywords in professions.items():
            if any(keyword in message_lower for keyword in keywords):
                return profession
        
        return "profesional"  # Default
    
    def _infer_energy_level(self, message_text: str, emotional_context: Optional[Dict]) -> int:
        """Infer energy level (1-10)."""
        low_energy_words = ["cansado", "agotado", "fatiga", "exhausto", "débil"]
        high_energy_words = ["energía", "activo", "vital", "fuerte", "dinámico"]
        
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in low_energy_words):
            return 3
        elif any(word in message_lower for word in high_energy_words):
            return 7
        
        # Consider emotional state
        if emotional_context and emotional_context.get("primary_emotion") in ["tired", "exhausted"]:
            return 3
        
        return 5  # Default middle
    
    def _infer_sleep_quality(self, message_text: str) -> int:
        """Infer sleep quality (1-10)."""
        poor_sleep_words = ["insomnio", "dormir mal", "no duermo", "desvelo"]
        good_sleep_words = ["duermo bien", "descanso", "sueño reparador"]
        
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in poor_sleep_words):
            return 3
        elif any(word in message_lower for word in good_sleep_words):
            return 8
        
        return 6  # Default
    
    def _infer_stress_level(self, message_text: str, emotional_context: Optional[Dict]) -> int:
        """Infer stress level (1-10)."""
        high_stress_words = ["estrés", "estresado", "presión", "ansiedad", "agobiado"]
        low_stress_words = ["tranquilo", "relajado", "paz", "calma"]
        
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in high_stress_words):
            return 8
        elif any(word in message_lower for word in low_stress_words):
            return 3
        
        # Consider emotional state
        if emotional_context and emotional_context.get("stress_indicators"):
            return 7
        
        return 5  # Default
    
    def _estimate_hourly_rate(self, customer_data, message_text: str) -> int:
        """Estimate customer's hourly rate."""
        profession = customer_data.get("profession", "profesional")
        
        hourly_rates = {
            "emprendedor": 150,
            "ejecutivo": 200,
            "médico": 250,
            "coach": 100,
            "profesional": 75
        }
        
        base_rate = hourly_rates.get(profession, 75)
        
        # Adjust by age/experience
        age = customer_data.get("age", 35)
        if age > 45:
            base_rate *= 1.5
        elif age > 35:
            base_rate *= 1.2
        
        return int(base_rate)
    
    def _extract_health_goals(self, message_text: str, state: ConversationState) -> List[str]:
        """Extract health goals from conversation."""
        goals = []
        all_text = message_text.lower() + " ".join([m.content.lower() for m in state.messages[-3:]])
        
        goal_patterns = {
            "weight_loss": ["bajar peso", "adelgazar", "perder kilos"],
            "energy": ["más energía", "vitalidad", "cansancio"],
            "longevity": ["vivir más", "longevidad", "envejecimiento"],
            "performance": ["rendimiento", "productividad", "mejor"],
            "health": ["salud", "bienestar", "sentirme bien"]
        }
        
        for goal, patterns in goal_patterns.items():
            if any(pattern in all_text for pattern in patterns):
                goals.append(goal)
        
        return goals if goals else ["general_wellness"]
    
    def _extract_productivity_needs(self, message_text: str, state: ConversationState) -> List[str]:
        """Extract productivity needs."""
        needs = []
        all_text = message_text.lower() + " ".join([m.content.lower() for m in state.messages[-3:]])
        
        need_patterns = {
            "time_management": ["tiempo", "agenda", "organizar"],
            "focus": ["concentración", "enfoque", "distracciones"],
            "automation": ["automatizar", "repetitivo", "eficiencia"],
            "decision_making": ["decisiones", "elegir", "opciones"],
            "scaling": ["crecer", "escalar", "expandir"]
        }
        
        for need, patterns in need_patterns.items():
            if any(pattern in all_text for pattern in patterns):
                needs.append(need)
        
        return needs if needs else ["general_productivity"]
    
    def _infer_decision_timeline(self, message_text: str, state: ConversationState) -> str:
        """Infer decision timeline."""
        immediate_words = ["ahora", "ya", "hoy", "inmediato"]
        future_words = ["después", "luego", "futuro", "más adelante"]
        
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in immediate_words):
            return "immediate"
        elif any(word in message_lower for word in future_words):
            return "future"
        
        # Based on conversation length
        if len(state.messages) > 20:
            return "ready"
        elif len(state.messages) > 10:
            return "evaluating"
        
        return "exploring"
    
    def _assess_budget_sensitivity(self, message_text: str, state: ConversationState) -> str:
        """Assess budget sensitivity."""
        price_mentions = sum(1 for m in state.messages if any(
            word in m.content.lower() for word in ["precio", "costo", "caro", "dinero"]
        ))
        
        if price_mentions > 3:
            return "high"
        elif price_mentions > 1:
            return "medium"
        
        return "low"
    
    def _assess_tech_savviness(self, message_text: str, state: ConversationState) -> str:
        """Assess technology savviness."""
        tech_words = ["app", "ia", "inteligencia artificial", "tecnología", "digital"]
        
        tech_mentions = sum(1 for m in state.messages if any(
            word in m.content.lower() for word in tech_words
        ))
        
        if tech_mentions > 2:
            return "high"
        elif tech_mentions > 0:
            return "medium"
        
        return "low"