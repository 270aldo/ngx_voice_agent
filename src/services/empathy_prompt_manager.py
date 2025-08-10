"""
Empathy Prompt Manager para NGX Voice Sales Agent.

Este servicio gestiona y optimiza los prompts para maximizar la empatía
en las respuestas del agente, usando técnicas avanzadas de prompt engineering.

OBJETIVO: Alcanzar 10/10 en empatía manteniendo efectividad en ventas.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.services.emotional_intelligence_service import EmotionalProfile, EmotionalState
# from src.conversation.prompts.unified_prompts import NGXUnifiedPrompts  # Not needed for current implementation

logger = logging.getLogger(__name__)


class EmpathyLevel(str, Enum):
    """Niveles de empatía para ajustar respuestas."""
    ULTRA_HIGH = "ultra_high"      # Para situaciones críticas
    VERY_HIGH = "very_high"        # Estados emocionales negativos
    HIGH = "high"                   # Confusión o escepticismo
    MODERATE = "moderate"           # Estado normal
    ADAPTIVE = "adaptive"           # Se ajusta dinámicamente


@dataclass
class EmpathyContext:
    """Contexto para generar respuestas empáticas."""
    emotional_state: EmotionalState
    empathy_level: EmpathyLevel
    conversation_phase: str
    customer_concerns: List[str]
    previous_interactions: int
    emotional_velocity: float
    triggers_detected: List[str]


class EmpathyPromptManager:
    """
    Gestor de prompts empáticos para maximizar conexión emocional.
    
    Características:
    - Prompts dinámicos basados en estado emocional
    - Técnicas de mirror empathy y validación
    - Ajuste de tono según contexto
    - Frases de conexión emocional
    - Balance entre empatía y objetivos de venta
    """
    
    def __init__(self):
        # self.base_prompts = NGXUnifiedPrompts()  # Not needed for current implementation
        self.empathy_enhancers = self._initialize_empathy_enhancers()
        self.emotional_validators = self._initialize_emotional_validators()
        self.connection_phrases = self._initialize_connection_phrases()
        
    def _initialize_empathy_enhancers(self) -> Dict[EmotionalState, List[str]]:
        """Inicializa mejoradores de empatía por estado emocional."""
        return {
            EmotionalState.ANXIOUS: [
                "Reconoce explícitamente sus preocupaciones y valídalas",
                "Usa un tono calmante y tranquilizador",
                "Ofrece seguridad y claridad en cada punto",
                "Menciona que es normal sentirse así y que estás para ayudar",
                "Divide la información en pasos pequeños y manejables"
            ],
            
            EmotionalState.FRUSTRATED: [
                "Valida completamente su frustración sin minimizarla",
                "Muestra que entiendes exactamente por qué se siente así",
                "Ofrece soluciones concretas e inmediatas",
                "Usa frases como 'Entiendo perfectamente tu frustración'",
                "Demuestra que estás de su lado para resolver esto juntos"
            ],
            
            EmotionalState.CONFUSED: [
                "Simplifica tu lenguaje al máximo",
                "Usa analogías y ejemplos concretos",
                "Verifica comprensión en cada paso",
                "Ofrece clarificar cualquier punto las veces necesarias",
                "Muestra paciencia infinita y disposición para explicar"
            ],
            
            EmotionalState.SKEPTICAL: [
                "Respeta su escepticismo como señal de inteligencia",
                "Proporciona pruebas y datos concretos",
                "Comparte historias reales de éxito",
                "Reconoce que es bueno que haga preguntas difíciles",
                "Ofrece garantías y formas de verificar lo que dices"
            ],
            
            EmotionalState.INTERESTED: [
                "Refleja y amplifica su entusiasmo",
                "Profundiza en los aspectos que más le interesan",
                "Comparte tu propia pasión por ayudar",
                "Conecta sus intereses con beneficios específicos",
                "Mantén el momentum positivo con energía contagiosa"
            ],
            
            EmotionalState.DECISIVE: [
                "Facilita su decisión sin presionar",
                "Resume los puntos clave de valor",
                "Muestra confianza en que es la decisión correcta",
                "Ofrece apoyo total en el proceso",
                "Celebra su decisión de tomar acción"
            ]
        }
    
    def _initialize_emotional_validators(self) -> Dict[str, List[str]]:
        """Inicializa frases de validación emocional."""
        return {
            "understanding": [
                "Entiendo completamente cómo te sientes",
                "Es totalmente comprensible que pienses eso",
                "Tienes toda la razón en sentirte así",
                "Me hace mucho sentido lo que me compartes",
                "Aprecio mucho que me compartas esto"
            ],
            
            "empathy": [
                "Me imagino que debe ser {situación} para ti",
                "Puedo ver por qué esto es importante para ti",
                "Muchas personas en tu situación sienten lo mismo",
                "Es natural sentirse así cuando {contexto}",
                "Valoro mucho tu honestidad al compartir esto"
            ],
            
            "support": [
                "Estoy aquí para ayudarte en cada paso",
                "Vamos a encontrar la mejor solución juntos",
                "Mi objetivo es que te sientas completamente cómodo",
                "No hay prisa, tomemos el tiempo que necesites",
                "Quiero asegurarme de que esto funcione perfectamente para ti"
            ]
        }
    
    def _initialize_connection_phrases(self) -> Dict[str, List[str]]:
        """Inicializa frases de conexión emocional."""
        return {
            "opening": [
                "Me da mucho gusto poder platicar contigo",
                "Qué bueno que te tomaste el tiempo para explorar esto",
                "Es un placer poder ayudarte hoy",
                "Me alegra mucho que hayas decidido contactarnos",
                "Gracias por darme la oportunidad de conocerte",
                "Es genial que estés buscando mejorar tu vida",
                "Me emociona mucho poder compartir esto contigo",
                "Qué alegría poder conversar contigo sobre tu bienestar",
                "Valoro mucho que confíes en nosotros para esto",
                "Es inspirador ver tu interés en optimizar tu potencial"
            ],
            
            "transition": [
                "Antes de continuar, ¿cómo te sientes hasta ahora?",
                "¿Hay algo que te gustaría que aclare antes de seguir?",
                "Me encantaría saber qué piensas sobre esto",
                "¿Esto resuena contigo o hay algo que ajustar?",
                "Tu opinión es muy importante para mí",
                "¿Qué es lo que más te preocupa en este momento?",
                "Me gustaría asegurarme de que estamos en la misma página",
                "¿Cómo te suena todo esto que hemos conversado?",
                "Quiero estar seguro de que esto tiene sentido para ti",
                "¿Qué preguntas tienes? No hay pregunta tonta, todas son importantes"
            ],
            
            "closing": [
                "Ha sido un verdadero placer conversar contigo",
                "Aprecio mucho el tiempo que me has dedicado",
                "Me emociona mucho poder acompañarte en este journey",
                "Estoy aquí para lo que necesites, cuando lo necesites",
                "Gracias por la confianza que me has mostrado",
                "Me da mucha alegría saber que podré ayudarte",
                "Es un honor poder ser parte de tu transformación",
                "Cuenta conmigo como tu aliado en este proceso",
                "Me llena de satisfacción poder apoyarte en esto",
                "Será increíble ver todo lo que vas a lograr"
            ],
            
            "reassurance": [
                "No estás solo en esto, estamos juntos",
                "Entiendo que puede parecer abrumador, pero iremos paso a paso",
                "Es completamente normal tener dudas, estoy aquí para resolverlas todas",
                "Tu bienestar es mi prioridad número uno",
                "Vamos a asegurarnos de que esto funcione perfectamente para ti",
                "No hay prisa, tomemos el tiempo que necesites para sentirte cómodo",
                "Cada persona es única y adaptaremos todo a tus necesidades",
                "Has tomado una decisión valiente al buscar mejorar, te admiro por eso",
                "Estoy comprometido a que tengas la mejor experiencia posible",
                "Tu éxito es mi éxito, estamos en el mismo equipo"
            ],
            
            "celebration": [
                "¡Me alegra muchísimo escuchar eso!",
                "¡Qué emocionante! Esto va a ser transformador para ti",
                "¡Es genial ver tu entusiasmo! Me contagias",
                "¡Wow! Tu actitud es exactamente lo que necesitas para triunfar",
                "¡Me encanta tu energía! Vas a lograr cosas increíbles",
                "¡Qué alegría me da verte tan motivado!",
                "¡Esto es exactamente lo que esperaba escuchar!",
                "¡Tu determinación es inspiradora!",
                "¡Me emociona mucho ser parte de tu journey!",
                "¡Vas a sorprenderte de todo lo que puedes lograr!"
            ]
        }
    
    def generate_empathetic_prompt(self,
                                 context: EmpathyContext,
                                 base_message: str,
                                 conversation_history: List[Dict]) -> str:
        """
        Genera un prompt optimizado para máxima empatía.
        
        Args:
            context: Contexto de empatía actual
            base_message: Mensaje base a mejorar
            conversation_history: Historial de conversación
            
        Returns:
            Prompt mejorado con máxima empatía
        """
        # Obtener mejoradores específicos para el estado emocional
        enhancers = self.empathy_enhancers.get(
            context.emotional_state, 
            self.empathy_enhancers[EmotionalState.NEUTRAL]
        )
        
        # Construir prompt empático
        empathy_prompt = f"""
CONTEXTO EMOCIONAL CRÍTICO:
- Estado emocional del cliente: {context.emotional_state.value}
- Nivel de empatía requerido: {context.empathy_level.value}
- Preocupaciones detectadas: {', '.join(context.customer_concerns)}
- Velocidad emocional: {'Alta - requiere estabilización' if context.emotional_velocity > 0.5 else 'Normal'}

INSTRUCCIONES EMPÁTICAS ESPECÍFICAS:
{chr(10).join(f'- {enhancer}' for enhancer in enhancers)}

ELEMENTOS OBLIGATORIOS EN TU RESPUESTA:
1. Inicia con validación emocional genuina
2. Muestra comprensión profunda de su situación específica
3. Usa lenguaje cálido y personal (tuteo respetuoso)
4. Incluye al menos una frase de conexión emocional
5. Mantén un tono de apoyo incondicional
6. Si hay frustración o ansiedad, abórdala directamente
7. Termina con una pregunta abierta que invite a compartir más

FRASES DE CONEXIÓN SUGERIDAS:
- "{self._get_connection_phrase(context)}"
- "{self._get_validation_phrase(context)}"

RESPUESTA BASE A MEJORAR:
{base_message}

IMPORTANTE: La empatía debe sentirse GENUINA, no forzada. Habla como un amigo profesional que realmente se preocupa por ayudar. Evita sonar robótico o con frases hechas. Cada palabra debe transmitir calidez humana real.

Genera una respuesta que maximize la conexión emocional mientras mantienes el objetivo de ayudar al cliente con NGX.
"""
        
        return empathy_prompt
    
    def enhance_response_with_empathy(self,
                                    response: str,
                                    emotional_profile: EmotionalProfile) -> str:
        """
        Mejora una respuesta existente con elementos empáticos.
        
        Args:
            response: Respuesta original
            emotional_profile: Perfil emocional del cliente
            
        Returns:
            Respuesta mejorada con mayor empatía
        """
        # Identificar puntos de inserción de empatía
        empathy_insertions = self._identify_empathy_opportunities(response)
        
        # Añadir validadores emocionales
        if emotional_profile.primary_emotion in [EmotionalState.ANXIOUS, EmotionalState.FRUSTRATED]:
            response = self._add_emotional_validation(response, emotional_profile)
        
        # Suavizar lenguaje técnico
        response = self._soften_technical_language(response)
        
        # Añadir elementos de conexión personal
        response = self._add_personal_connection(response, emotional_profile)
        
        return response
    
    def _get_connection_phrase(self, context: EmpathyContext) -> str:
        """Obtiene frase de conexión apropiada."""
        if context.previous_interactions == 0:
            phrases = self.connection_phrases["opening"]
        elif context.conversation_phase == "closing":
            phrases = self.connection_phrases["closing"]
        else:
            phrases = self.connection_phrases["transition"]
            
        import random
        return random.choice(phrases)
    
    def _get_validation_phrase(self, context: EmpathyContext) -> str:
        """Obtiene frase de validación emocional."""
        if context.emotional_state in [EmotionalState.ANXIOUS, EmotionalState.FRUSTRATED]:
            phrases = self.emotional_validators["empathy"]
        else:
            phrases = self.emotional_validators["understanding"]
            
        import random
        return random.choice(phrases)
    
    def _identify_empathy_opportunities(self, response: str) -> List[Tuple[int, str]]:
        """Identifica oportunidades para insertar empatía."""
        opportunities = []
        
        # Buscar transiciones donde añadir empatía
        transitions = ["Además", "Por otro lado", "También", "Ahora bien"]
        for transition in transitions:
            if transition in response:
                opportunities.append((response.index(transition), "transition"))
        
        # Buscar preguntas donde añadir validación
        if "?" in response:
            opportunities.append((response.index("?"), "question"))
            
        return opportunities
    
    def _add_emotional_validation(self, response: str, profile: EmotionalProfile) -> str:
        """Añade validación emocional al inicio de la respuesta."""
        validations = {
            EmotionalState.ANXIOUS: "Entiendo que esto puede generar algunas dudas, y es completamente normal. ",
            EmotionalState.FRUSTRATED: "Comprendo tu frustración y tienes toda la razón en sentirte así. ",
            EmotionalState.CONFUSED: "Sé que puede parecer mucha información, déjame simplificarlo. ",
            EmotionalState.SKEPTICAL: "Aprecio tu escepticismo, es señal de que tomas decisiones inteligentes. "
        }
        
        validation = validations.get(profile.primary_emotion, "")
        return validation + response
    
    def _soften_technical_language(self, response: str) -> str:
        """Suaviza lenguaje técnico para mayor calidez."""
        replacements = {
            "El sistema": "Nuestro programa",
            "La plataforma": "Tu espacio personal",
            "Los algoritmos": "Nuestra tecnología",
            "La implementación": "Cómo lo ponemos en práctica",
            "La metodología": "Nuestra forma de trabajo",
            "El protocolo": "Tu plan personalizado",
            "La optimización": "Mejorar tu bienestar",
            "Los parámetros": "Tus necesidades específicas"
        }
        
        for technical, warm in replacements.items():
            response = response.replace(technical, warm)
            
        return response
    
    def _add_personal_connection(self, response: str, profile: EmotionalProfile) -> str:
        """Añade elementos de conexión personal."""
        if profile.stability_score < 0.7:
            # Cliente emocionalmente volátil - añadir más soporte
            response += " Quiero que sepas que estoy aquí para apoyarte en cada paso del camino."
        
        return response
    
    def get_empathy_metrics(self, response: str) -> Dict[str, float]:
        """
        Calcula métricas de empatía en una respuesta.
        
        Args:
            response: Respuesta a analizar
            
        Returns:
            Métricas de empatía
        """
        metrics = {
            "validation_count": 0,
            "personal_pronouns": 0,
            "emotional_words": 0,
            "support_phrases": 0,
            "warmth_score": 0,
            "connection_phrases": 0,
            "empathy_indicators": 0
        }
        
        # Contar elementos empáticos
        response_lower = response.lower()
        
        # Validaciones emocionales
        validation_keywords = [
            "entiendo", "comprendo", "es normal", "tienes razón", 
            "aprecio", "valoro", "respeto", "admiro", "me imagino"
        ]
        for keyword in validation_keywords:
            if keyword in response_lower:
                metrics["validation_count"] += 1
        
        # Pronombres personales (conexión)
        personal_pronouns = ["tu", "tus", "ti", "contigo", "te"]
        for pronoun in personal_pronouns:
            metrics["personal_pronouns"] += response_lower.count(pronoun)
        
        # Palabras emocionales
        emotional_words = [
            "siento", "emociona", "alegra", "preocupa", "importa",
            "corazón", "genuino", "sincero", "auténtico", "especial"
        ]
        for word in emotional_words:
            if word in response_lower:
                metrics["emotional_words"] += 1
        
        # Frases de apoyo
        support_phrases = [
            "estoy aquí", "estamos juntos", "te apoyo", "cuenta conmigo",
            "mi prioridad", "para ayudarte", "a tu lado", "tu bienestar"
        ]
        for phrase in support_phrases:
            if phrase in response_lower:
                metrics["support_phrases"] += 1
        
        # Calcular warmth score
        total_elements = sum([
            metrics["validation_count"],
            min(metrics["personal_pronouns"], 10) / 10,  # Normalizar
            metrics["emotional_words"],
            metrics["support_phrases"]
        ])
        
        metrics["warmth_score"] = min(total_elements / 10, 1.0)  # Score 0-1
        
        return metrics
    
    def create_empathy_enhanced_instruction(self, 
                                          customer_age: int,
                                          customer_profession: str,
                                          emotional_state: EmotionalState) -> str:
        """
        Crea instrucción específica para maximizar empatía según perfil.
        
        Args:
            customer_age: Edad del cliente
            customer_profession: Profesión del cliente
            emotional_state: Estado emocional actual
            
        Returns:
            Instrucción personalizada de empatía
        """
        # Ajustes por edad
        age_adjustments = {
            (18, 30): "Usa un tono enérgico y optimista, con referencias a lograr el máximo potencial",
            (31, 45): "Enfócate en balance vida-trabajo y optimización del tiempo limitado",
            (46, 60): "Habla de prevención, longevidad y mantener la vitalidad",
            (61, 100): "Usa un tono respetuoso, enfatiza calidad de vida y bienestar"
        }
        
        age_instruction = ""
        for (min_age, max_age), instruction in age_adjustments.items():
            if min_age <= customer_age <= max_age:
                age_instruction = instruction
                break
        
        # Ajustes por profesión
        profession_empathy = {
            "CEO": "Reconoce la presión del liderazgo y la importancia de estar al 100%",
            "Entrepreneur": "Valida el estrés de construir un negocio y la necesidad de energía constante",
            "Doctor": "Aprecia su dedicación a otros y la importancia de su propio cuidado",
            "Athlete": "Conecta con su búsqueda de excelencia y mejora continua",
            "Executive": "Entiende las demandas corporativas y la necesidad de rendimiento sostenible"
        }
        
        profession_instruction = profession_empathy.get(
            customer_profession,
            "Reconoce sus desafíos únicos y valida su búsqueda de mejora personal"
        )
        
        return f"""
PERFIL DE EMPATÍA PERSONALIZADO:
- Edad: {customer_age} años - {age_instruction}
- Profesión: {customer_profession} - {profession_instruction}
- Estado Emocional: {emotional_state.value}

NIVEL DE EMPATÍA OBJETIVO: 10/10

ELEMENTOS CRÍTICOS:
1. Usa el nombre del cliente al menos una vez (si lo conoces)
2. Refleja su lenguaje y nivel de energía
3. Muestra comprensión genuina de SU situación específica
4. Incluye al menos 2 frases de validación emocional
5. Mantén un balance 70% escucha/comprensión - 30% información
6. Termina cada respuesta invitando a compartir más
7. Usa humor apropiado si el estado emocional lo permite
8. Nunca minimices sus preocupaciones
9. Siempre ofrece opciones, nunca presiones
10. Demuestra que realmente te importa su bienestar

RECORDATORIO: Tu objetivo no es solo vender, es crear una conexión humana genuina que naturalmente lleve a una decisión positiva."""
    
    def suggest_empathy_improvements(self, 
                                   response: str,
                                   target_score: float = 10.0) -> List[str]:
        """
        Sugiere mejoras específicas para alcanzar el puntaje objetivo.
        
        Args:
            response: Respuesta actual
            target_score: Puntaje objetivo de empatía
            
        Returns:
            Lista de sugerencias de mejora
        """
        current_metrics = self.get_empathy_metrics(response)
        suggestions = []
        
        if current_metrics["validation_count"] < 2:
            suggestions.append("Añade más validación emocional al inicio")
        
        if current_metrics["personal_pronouns"] < 5:
            suggestions.append("Usa más pronombres personales (tú, contigo, para ti)")
        
        if current_metrics["emotional_words"] < 3:
            suggestions.append("Incluye más vocabulario emocional")
        
        if current_metrics["support_phrases"] < 1:
            suggestions.append("Añade al menos una frase de apoyo incondicional")
        
        if "?" not in response:
            suggestions.append("Termina con una pregunta abierta para invitar diálogo")
        
        return suggestions