"""
Fallback Predictor for NGX Voice Sales Agent.

This module provides immediate predictions using rule-based heuristics
while the ML models are being trained. It ensures the predictive services
always return meaningful results.
"""

from typing import Dict, List, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)

class FallbackPredictor:
    """
    Provides fallback predictions using rule-based heuristics.
    
    This class implements simple but effective pattern matching to provide
    predictions when ML models are not yet trained or unavailable.
    """
    
    def __init__(self):
        """Initialize the fallback predictor with rule sets."""
        self._initialize_rules()
        
    def _initialize_rules(self) -> None:
        """Initialize rule-based patterns for predictions."""
        
        # Objection detection rules
        self.objection_rules = {
            "price": {
                "keywords": ["caro", "precio", "costo", "presupuesto", "económico", "descuento", "oferta", "pagar", "$"],
                "weight": 0.8
            },
            "need": {
                "keywords": ["no necesito", "no creo", "ya tengo", "estoy bien", "no veo", "para qué"],
                "weight": 0.7
            },
            "urgency": {
                "keywords": ["después", "luego", "más adelante", "pensarlo", "consultar", "no es momento"],
                "weight": 0.6
            },
            "trust": {
                "keywords": ["confiable", "seguro", "garantía", "referencias", "quien usa", "testimonios"],
                "weight": 0.7
            },
            "features": {
                "keywords": ["falta", "no tiene", "incluye", "puede hacer", "características", "funciones"],
                "weight": 0.6
            },
            "competition": {
                "keywords": ["otros", "competencia", "comparar", "alternativas", "mejor opción"],
                "weight": 0.7
            }
        }
        
        # Need detection rules
        self.need_rules = {
            "information": {
                "keywords": ["información", "saber más", "explicar", "cómo funciona", "detalles", "entender"],
                "questions": ["qué es", "cómo", "cuándo", "dónde"],
                "weight": 0.7
            },
            "pricing": {
                "keywords": ["precio", "costo", "inversión", "planes", "paquetes", "mensualidad", "pago"],
                "questions": ["cuánto", "precio", "costo"],
                "weight": 0.8
            },
            "features": {
                "keywords": ["funciones", "características", "incluye", "puede", "hace", "capacidades"],
                "questions": ["qué incluye", "qué hace", "puede"],
                "weight": 0.7
            },
            "support": {
                "keywords": ["ayuda", "soporte", "asistencia", "capacitación", "entrenamiento", "apoyo"],
                "questions": ["ayuda", "soporte", "asistencia"],
                "weight": 0.6
            },
            "integration": {
                "keywords": ["integrar", "conectar", "compatible", "trabajar con", "sincronizar", "API"],
                "questions": ["se integra", "compatible", "conecta"],
                "weight": 0.6
            },
            "implementation": {
                "keywords": ["implementar", "instalar", "configurar", "tiempo", "proceso", "pasos"],
                "questions": ["cuánto tiempo", "cómo implementar", "proceso"],
                "weight": 0.6
            }
        }
        
        # Conversion signal rules
        self.conversion_rules = {
            "high_interest": {
                "keywords": ["quiero", "me interesa", "vamos", "empezar", "contratar", "comprar", "adquirir"],
                "sentiment": "positive",
                "weight": 0.9
            },
            "medium_interest": {
                "keywords": ["suena bien", "me gusta", "podría", "tal vez", "posiblemente", "considerando"],
                "sentiment": "neutral",
                "weight": 0.6
            },
            "low_interest": {
                "keywords": ["no estoy seguro", "dudas", "pensar", "no sé", "quizás", "veremos"],
                "sentiment": "negative",
                "weight": 0.3
            },
            "engagement": {
                "indicators": ["questions_asked", "response_length", "response_time"],
                "weight": 0.5
            }
        }
        
    def predict_objections(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict potential objections using rule-based patterns.
        
        Args:
            messages: Conversation messages
            
        Returns:
            Predicted objections with confidence scores
        """
        if not messages:
            return {"objections": [], "confidence": 0.0, "signals": {}}
            
        predicted_objections = []
        signals = {}
        
        # Extract customer messages
        customer_messages = [
            msg.get("content", "") 
            for msg in messages 
            if msg.get("role") in ["user", "customer"]
        ]
        
        if not customer_messages:
            return {"objections": [], "confidence": 0.0, "signals": {}}
            
        # Combine all customer text
        full_text = " ".join(customer_messages).lower()
        
        # Check each objection type
        for objection_type, rule in self.objection_rules.items():
            score = 0.0
            matched_keywords = []
            
            # Check for keyword matches
            for keyword in rule["keywords"]:
                if keyword in full_text:
                    score += rule["weight"]
                    matched_keywords.append(keyword)
                    
            # Normalize score
            if matched_keywords:
                confidence = min(score / len(rule["keywords"]), 0.95)
                signals[objection_type] = matched_keywords
                
                if confidence >= 0.5:  # Threshold for prediction
                    predicted_objections.append({
                        "type": objection_type,
                        "confidence": confidence,
                        "matched_keywords": matched_keywords,
                        "suggested_responses": self._get_objection_responses(objection_type)
                    })
                    
        # Sort by confidence
        predicted_objections.sort(key=lambda x: x["confidence"], reverse=True)
        
        overall_confidence = max([obj["confidence"] for obj in predicted_objections], default=0.0)
        
        return {
            "objections": predicted_objections[:3],  # Top 3 objections
            "confidence": overall_confidence,
            "signals": signals
        }
        
    def predict_needs(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict customer needs using rule-based patterns.
        
        Args:
            messages: Conversation messages
            
        Returns:
            Predicted needs with confidence scores
        """
        if not messages:
            return {"needs": [], "confidence": 0.0, "features": {}}
            
        predicted_needs = []
        features = {"detected_keywords": {}, "questions": []}
        
        # Extract customer messages
        customer_messages = [
            msg.get("content", "") 
            for msg in messages 
            if msg.get("role") in ["user", "customer"]
        ]
        
        if not customer_messages:
            return {"needs": [], "confidence": 0.0, "features": features}
            
        # Combine all customer text
        full_text = " ".join(customer_messages).lower()
        
        # Extract questions
        questions = re.findall(r'[^.!?]*\?', full_text)
        features["questions"] = questions
        
        # Check each need category
        for need_category, rule in self.need_rules.items():
            score = 0.0
            matched_keywords = []
            matched_questions = []
            
            # Check for keyword matches
            for keyword in rule["keywords"]:
                if keyword in full_text:
                    score += rule["weight"]
                    matched_keywords.append(keyword)
                    
            # Check for question patterns
            if "questions" in rule:
                for question_pattern in rule["questions"]:
                    for question in questions:
                        if question_pattern in question:
                            score += rule["weight"] * 0.5
                            matched_questions.append(question_pattern)
                            
            # Normalize score
            if matched_keywords or matched_questions:
                confidence = min(score / (len(rule["keywords"]) + len(rule.get("questions", []))), 0.9)
                features["detected_keywords"][need_category] = matched_keywords
                
                if confidence >= 0.4:  # Lower threshold for needs
                    predicted_needs.append({
                        "category": need_category,
                        "confidence": confidence,
                        "matched_keywords": matched_keywords,
                        "matched_questions": matched_questions,
                        "suggested_actions": self._get_need_actions(need_category)
                    })
                    
        # Sort by confidence
        predicted_needs.sort(key=lambda x: x["confidence"], reverse=True)
        
        overall_confidence = max([need["confidence"] for need in predicted_needs], default=0.0)
        
        return {
            "needs": predicted_needs[:3],  # Top 3 needs
            "confidence": overall_confidence,
            "features": features
        }
        
    def predict_conversion(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict conversion probability using rule-based patterns.
        
        Args:
            messages: Conversation messages
            
        Returns:
            Conversion prediction with probability
        """
        if not messages:
            return {
                "probability": 0.0,
                "confidence": 0.0,
                "category": "low",
                "signals": {},
                "recommendations": []
            }
            
        signals = {
            "positive_signals": 0,
            "negative_signals": 0,
            "engagement_level": 0,
            "questions_asked": 0
        }
        
        # Extract customer messages
        customer_messages = [
            msg for msg in messages 
            if msg.get("role") in ["user", "customer"]
        ]
        
        if not customer_messages:
            return {
                "probability": 0.0,
                "confidence": 0.0,
                "category": "low",
                "signals": signals,
                "recommendations": []
            }
            
        # Analyze each message
        total_score = 0.0
        
        for msg in customer_messages:
            content = msg.get("content", "").lower()
            
            # Check high interest signals
            for keyword in self.conversion_rules["high_interest"]["keywords"]:
                if keyword in content:
                    total_score += self.conversion_rules["high_interest"]["weight"]
                    signals["positive_signals"] += 1
                    
            # Check medium interest signals
            for keyword in self.conversion_rules["medium_interest"]["keywords"]:
                if keyword in content:
                    total_score += self.conversion_rules["medium_interest"]["weight"]
                    signals["positive_signals"] += 1
                    
            # Check low interest signals
            for keyword in self.conversion_rules["low_interest"]["keywords"]:
                if keyword in content:
                    total_score -= self.conversion_rules["low_interest"]["weight"] * 0.5
                    signals["negative_signals"] += 1
                    
            # Count questions
            if "?" in content:
                signals["questions_asked"] += 1
                total_score += 0.1  # Questions show engagement
                
        # Calculate engagement level
        signals["engagement_level"] = min(len(customer_messages) / 10.0, 1.0)
        total_score += signals["engagement_level"] * 0.3
        
        # Normalize probability (0-1)
        probability = max(0.0, min(1.0, total_score / (len(customer_messages) + 1)))
        
        # Determine category
        if probability >= 0.7:
            category = "high"
        elif probability >= 0.4:
            category = "medium"
        else:
            category = "low"
            
        # Generate recommendations
        recommendations = self._get_conversion_recommendations(category, signals)
        
        # Calculate confidence based on signal strength
        confidence = min(0.9, (signals["positive_signals"] + signals["questions_asked"]) / 10.0)
        
        return {
            "probability": probability,
            "confidence": confidence,
            "category": category,
            "signals": signals,
            "recommendations": recommendations
        }
        
    def _get_objection_responses(self, objection_type: str) -> List[str]:
        """Get suggested responses for objection type."""
        responses = {
            "price": [
                "Entiendo tu preocupación por el precio. Consideremos el ROI que obtendrás...",
                "Tenemos planes flexibles que se adaptan a diferentes presupuestos.",
                "La inversión se recupera típicamente en 3-4 meses gracias al aumento en conversiones."
            ],
            "need": [
                "Te comprendo. Muchos de nuestros clientes pensaban lo mismo hasta que vieron...",
                "¿Qué desafíos específicos enfrentas actualmente en tu negocio?",
                "Permíteme mostrarte cómo esto resuelve problemas que quizás no has identificado aún."
            ],
            "urgency": [
                "Por supuesto, tómate el tiempo que necesites. ¿Hay algo específico que te ayudaría a decidir?",
                "Entiendo. ¿Cuándo sería un buen momento para retomar esta conversación?",
                "Mientras lo piensas, te comparto algunos casos de éxito para que veas resultados reales."
            ],
            "trust": [
                "Excelente pregunta. Trabajamos con más de 500 gimnasios y estudios en toda la región.",
                "Te puedo compartir testimonios y casos de éxito de negocios similares al tuyo.",
                "Ofrecemos una garantía de satisfacción de 30 días para que pruebes sin riesgo."
            ],
            "features": [
                "Las funcionalidades que mencionas están en nuestro roadmap. Mientras tanto...",
                "Aunque no tenemos esa característica específica, logramos el mismo resultado con...",
                "Constantemente añadimos nuevas funciones basadas en feedback de clientes como tú."
            ],
            "competition": [
                "Me alegra que estés evaluando opciones. Nuestra ventaja principal es...",
                "A diferencia de otros, nosotros nos especializamos específicamente en fitness.",
                "Muchos clientes vienen de la competencia porque con nosotros obtienen..."
            ]
        }
        return responses.get(objection_type, ["Entiendo tu punto. ¿Puedes contarme más sobre tu preocupación?"])
        
    def _get_need_actions(self, need_category: str) -> List[Dict[str, Any]]:
        """Get suggested actions for need category."""
        actions = {
            "information": [
                {"type": "content", "action": "Compartir presentación general de NGX", "priority": "high"},
                {"type": "demo", "action": "Ofrecer demostración personalizada", "priority": "medium"}
            ],
            "pricing": [
                {"type": "content", "action": "Enviar tabla de precios actualizada", "priority": "high"},
                {"type": "calculator", "action": "Usar calculadora de ROI", "priority": "high"}
            ],
            "features": [
                {"type": "content", "action": "Compartir lista detallada de funcionalidades", "priority": "high"},
                {"type": "demo", "action": "Mostrar funciones específicas en vivo", "priority": "medium"}
            ],
            "support": [
                {"type": "content", "action": "Explicar niveles de soporte disponibles", "priority": "high"},
                {"type": "contact", "action": "Ofrecer llamada con equipo de soporte", "priority": "medium"}
            ],
            "integration": [
                {"type": "content", "action": "Compartir documentación de integraciones", "priority": "high"},
                {"type": "technical", "action": "Consulta técnica sobre compatibilidad", "priority": "medium"}
            ],
            "implementation": [
                {"type": "content", "action": "Compartir cronograma típico de implementación", "priority": "high"},
                {"type": "consultation", "action": "Agendar consultoría de implementación", "priority": "medium"}
            ]
        }
        return actions.get(need_category, [{"type": "general", "action": "Proporcionar información relevante", "priority": "medium"}])
        
    def _get_conversion_recommendations(self, category: str, signals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recommendations based on conversion category."""
        recommendations = []
        
        if category == "high":
            recommendations.extend([
                {
                    "action": "close_sale",
                    "description": "Proceder con el cierre de venta",
                    "priority": "high",
                    "script": "¡Excelente! Veo que estás listo para comenzar. Te guío con los siguientes pasos..."
                },
                {
                    "action": "create_urgency",
                    "description": "Mencionar oferta por tiempo limitado",
                    "priority": "medium",
                    "script": "Aprovecha nuestra promoción de este mes: 20% de descuento en el primer año."
                }
            ])
        elif category == "medium":
            recommendations.extend([
                {
                    "action": "address_concerns",
                    "description": "Resolver dudas pendientes",
                    "priority": "high",
                    "script": "Noto que tienes algunas dudas. ¿Qué aspecto específico te gustaría aclarar?"
                },
                {
                    "action": "social_proof",
                    "description": "Compartir casos de éxito",
                    "priority": "medium",
                    "script": "Te comparto cómo Studio Fitness aumentó sus ventas 40% en 3 meses..."
                }
            ])
        else:  # low
            recommendations.extend([
                {
                    "action": "nurture",
                    "description": "Mantener relación a largo plazo",
                    "priority": "high",
                    "script": "Entiendo que no es el momento. ¿Te gustaría recibir información periódica?"
                },
                {
                    "action": "value_education",
                    "description": "Educar sobre el valor del producto",
                    "priority": "medium",
                    "script": "Te comparto algunos recursos gratuitos sobre automatización en fitness..."
                }
            ])
            
        # Add recommendations based on signals
        if signals["questions_asked"] > 3:
            recommendations.append({
                "action": "detailed_explanation",
                "description": "Proporcionar explicaciones detalladas",
                "priority": "high",
                "script": "Veo que tienes varias preguntas. Permíteme explicarte en detalle..."
            })
            
        if signals["negative_signals"] > signals["positive_signals"]:
            recommendations.append({
                "action": "rebuild_trust",
                "description": "Reconstruir confianza y credibilidad",
                "priority": "high",
                "script": "Comprendo tus preocupaciones. Muchos clientes exitosos comenzaron con las mismas dudas..."
            })
            
        return recommendations[:3]  # Return top 3 recommendations