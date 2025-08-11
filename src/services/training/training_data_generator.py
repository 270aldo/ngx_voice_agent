"""
Training Data Generator for NGX Voice Sales Agent Predictive Services.

This module generates synthetic training data to bootstrap the predictive models
with baseline knowledge about common objections, needs, and conversion patterns.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import random
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class TrainingDataGenerator:
    """
    Generates synthetic training data for bootstrapping predictive models.
    
    This class creates realistic training scenarios based on NGX's business domain,
    including common objections, customer needs, and conversion patterns.
    """
    
    def __init__(self):
        """Initialize the training data generator with domain knowledge."""
        self._initialize_domain_knowledge()
        
    def _initialize_domain_knowledge(self) -> None:
        """Initialize domain-specific knowledge for NGX services."""
        
        # Common objections in fitness/training industry
        self.objection_patterns = {
            "price": [
                "es muy caro",
                "no tengo presupuesto",
                "cuánto cuesta",
                "hay algo más económico",
                "no puedo pagar tanto",
                "comparado con otros",
                "descuento",
                "precio muy alto",
                "$2700 al mes es mucho",
                "no puedo justificar ese gasto",
                "otros cobran menos",
                "es demasiada inversión",
                "mi gym no genera tanto"
            ],
            "need": [
                "no lo necesito",
                "ya tengo un sistema",
                "estoy bien así",
                "no veo el beneficio",
                "para qué lo necesito",
                "no es para mí",
                "ya manejo mis clientes bien",
                "mi asistente hace eso",
                "prefiero hacerlo personal",
                "no creo en la AI",
                "mis clientes prefieren hablar conmigo"
            ],
            "urgency": [
                "lo pensaré",
                "más adelante",
                "no es el momento",
                "hablaré con mi equipo",
                "déjame consultarlo",
                "no tengo prisa",
                "quizás el próximo año",
                "ahora estoy ocupado",
                "después de temporada alta",
                "cuando tenga más clientes",
                "necesito ver resultados primero"
            ],
            "trust": [
                "no los conozco",
                "tienen referencias",
                "quién los usa",
                "es confiable",
                "tienen garantía",
                "qué pasa si no funciona",
                "cómo sé que funciona",
                "han trabajado con gyms",
                "tienen casos de éxito",
                "puedo probarlo primero",
                "y si no me gusta"
            ],
            "features": [
                "le falta",
                "no tiene",
                "necesito que haga",
                "puede hacer",
                "incluye",
                "características",
                "se integra con mi CRM",
                "funciona con WhatsApp",
                "habla varios idiomas",
                "puede agendar clases",
                "maneja pagos"
            ],
            "competition": [
                "ya uso otro sistema",
                "mi competencia usa X",
                "he visto opciones más baratas",
                "qué me ofrece diferente",
                "otros tienen más funciones",
                "prefiero soluciones locales"
            ]
        }
        
        # Common customer needs
        self.need_patterns = {
            "information": [
                "quiero saber más",
                "explícame",
                "cómo funciona",
                "dime más sobre",
                "información sobre",
                "detalles de",
                "cuéntame sobre NGX",
                "qué es exactamente",
                "cómo me ayuda esto",
                "explica los agentes",
                "para qué sirve cada uno"
            ],
            "pricing": [
                "cuáles son los precios",
                "planes disponibles",
                "opciones de pago",
                "cuánto tendría que invertir",
                "presupuesto necesario",
                "hay plan básico",
                "puedo pagar mensual",
                "incluye todo o hay extras",
                "precio por usuario",
                "descuentos por volumen"
            ],
            "features": [
                "qué incluye",
                "funcionalidades",
                "características",
                "qué puede hacer",
                "ventajas",
                "los 11 agentes qué hacen",
                "cómo agenda citas",
                "maneja redes sociales",
                "puede hacer seguimiento",
                "genera reportes"
            ],
            "support": [
                "ayuda",
                "soporte",
                "asistencia",
                "capacitación",
                "entrenamiento",
                "me enseñan a usarlo",
                "soporte en español",
                "responden rápido",
                "ayuda para configurar",
                "videos tutoriales"
            ],
            "integration": [
                "se integra con",
                "compatible con",
                "conectar con",
                "trabajar con otros sistemas",
                "funciona con Mindbody",
                "se conecta a Instagram",
                "exporta a Excel",
                "API disponible",
                "webhooks"
            ],
            "roi": [
                "cuánto puedo ganar",
                "retorno de inversión",
                "en cuánto tiempo recupero",
                "casos de éxito reales",
                "resultados típicos",
                "aumento de ventas"
            ]
        }
        
        # Conversion signals
        self.conversion_signals = {
            "high": [
                "quiero empezar",
                "cómo contrato",
                "siguiente paso",
                "vamos a hacerlo",
                "me interesa mucho",
                "cuándo podemos empezar",
                "dame el link de pago",
                "listo para comenzar",
                "necesito esto ya",
                "perfecto lo quiero",
                "mándame el contrato",
                "donde firmo"
            ],
            "medium": [
                "suena bien",
                "me gusta",
                "podría funcionar",
                "tiene sentido",
                "veo el valor",
                "es interesante",
                "me llama la atención",
                "podría servirme",
                "veo potencial",
                "suena prometedor",
                "me está gustando"
            ],
            "low": [
                "no estoy seguro",
                "tengo dudas",
                "no me convence",
                "hay otras opciones",
                "necesito pensar",
                "no es para mí ahora",
                "tal vez más adelante",
                "voy a evaluarlo",
                "lo consulto y te digo",
                "déjame ver otras opciones"
            ]
        }
        
        # NGX-specific context
        self.ngx_contexts = {
            "services": [
                "NGX AGENTS ACCESS",
                "AI personal trainers",
                "agentes inteligentes",
                "automatización de ventas",
                "gestión de clientes",
                "11 agentes especializados",
                "asistente virtual fitness",
                "bot de WhatsApp",
                "agendamiento automático",
                "seguimiento de leads"
            ],
            "benefits": [
                "ahorro de tiempo",
                "más clientes",
                "mejor conversión",
                "automatización",
                "disponible 24/7",
                "10x más ventas",
                "reduce 80% trabajo manual",
                "atiende 100 clientes a la vez",
                "nunca pierde un lead",
                "respuesta inmediata"
            ],
            "industries": [
                "gimnasio",
                "entrenador personal",
                "centro fitness",
                "estudio de yoga",
                "box de crossfit",
                "centro de nutrición",
                "spa wellness",
                "clínica fisioterapia",
                "academia de baile",
                "centro deportivo"
            ],
            "pain_points": [
                "no tengo tiempo para responder",
                "pierdo clientes por no contestar",
                "mi recepcionista no da abasto",
                "los leads se enfrían",
                "no puedo hacer seguimiento",
                "se me olvidan las citas",
                "no sé qué publicar",
                "mis ventas no crecen",
                "la competencia me gana clientes"
            ]
        }
        
    def generate_objection_training_data(self, num_samples: int = 100) -> List[Dict[str, Any]]:
        """
        Generate training data for objection prediction.
        
        Args:
            num_samples: Number of training samples to generate
            
        Returns:
            List of training samples with features and labels
        """
        training_data = []
        
        for _ in range(num_samples):
            # Select random objection type
            objection_type = random.choice(list(self.objection_patterns.keys()))
            objection_phrases = self.objection_patterns[objection_type]
            
            # Generate conversation context
            messages = self._generate_conversation_with_objection(
                objection_type, objection_phrases
            )
            
            # Extract features
            features = {
                "messages": messages,
                "message_count": len(messages),
                "contains_price_mention": any("precio" in msg["content"].lower() or "costo" in msg["content"].lower() or "$" in msg["content"] for msg in messages),
                "contains_comparison": any("comparar" in msg["content"].lower() or "otro" in msg["content"].lower() or "competencia" in msg["content"].lower() for msg in messages),
                "sentiment_trend": "negative" if objection_type in ["price", "trust", "need"] else "neutral",
                "last_message": messages[-1]["content"] if messages else "",
                "objection_keywords": sum(1 for phrase in objection_phrases if phrase.lower() in messages[-1]["content"].lower()) if messages else 0
            }
            
            # Create training sample
            sample = {
                "features": features,
                "label": objection_type,
                "confidence": random.uniform(0.7, 0.95)
            }
            
            training_data.append(sample)
            
        return training_data
        
    def generate_needs_training_data(self, num_samples: int = 100) -> List[Dict[str, Any]]:
        """
        Generate training data for needs prediction.
        
        Args:
            num_samples: Number of training samples to generate
            
        Returns:
            List of training samples with features and labels
        """
        training_data = []
        
        for _ in range(num_samples):
            # Select random need category
            need_category = random.choice(list(self.need_patterns.keys()))
            need_phrases = self.need_patterns[need_category]
            
            # Generate conversation context
            messages = self._generate_conversation_with_need(
                need_category, need_phrases
            )
            
            # Extract features
            features = {
                "messages": messages,
                "question_count": sum(1 for msg in messages if "?" in msg["content"]),
                "mentions_specific_feature": any(
                    any(feature in msg["content"].lower() for feature in ["función", "característica", "incluye"])
                    for msg in messages
                ),
                "engagement_level": len(messages) / 10.0  # Normalized
            }
            
            # Create training sample
            sample = {
                "features": features,
                "label": need_category,
                "confidence": random.uniform(0.6, 0.9)
            }
            
            training_data.append(sample)
            
        return training_data
        
    def generate_conversion_training_data(self, num_samples: int = 100) -> List[Dict[str, Any]]:
        """
        Generate training data for conversion prediction.
        
        Args:
            num_samples: Number of training samples to generate
            
        Returns:
            List of training samples with features and labels
        """
        training_data = []
        
        for _ in range(num_samples):
            # Select conversion probability level
            conversion_level = random.choice(["high", "medium", "low"])
            conversion_signals = self.conversion_signals[conversion_level]
            
            # Generate conversation context
            messages = self._generate_conversation_with_conversion_signals(
                conversion_level, conversion_signals
            )
            
            # Calculate conversion probability
            if conversion_level == "high":
                probability = random.uniform(0.7, 0.95)
            elif conversion_level == "medium":
                probability = random.uniform(0.4, 0.7)
            else:
                probability = random.uniform(0.1, 0.4)
                
            # Extract features
            features = {
                "messages": messages,
                "positive_signals": sum(1 for msg in messages if any(signal in msg["content"].lower() for signal in ["interesa", "gusta", "quiero"])),
                "questions_asked": sum(1 for msg in messages if "?" in msg["content"]),
                "message_length_avg": sum(len(msg["content"]) for msg in messages) / len(messages),
                "engagement_score": len(messages) * 0.1 + (probability * 0.5)
            }
            
            # Create training sample
            sample = {
                "features": features,
                "label": {
                    "did_convert": probability > 0.6,
                    "probability": probability,
                    "category": conversion_level
                },
                "confidence": random.uniform(0.7, 0.9)
            }
            
            training_data.append(sample)
            
        return training_data
        
    def _generate_conversation_with_objection(self, objection_type: str, 
                                            objection_phrases: List[str]) -> List[Dict[str, Any]]:
        """Generate a conversation that includes specific objection patterns."""
        messages = []
        
        # Initial greeting
        messages.append({
            "role": "assistant",
            "content": "¡Hola! Soy tu asistente de NGX. ¿En qué puedo ayudarte hoy?"
        })
        
        # Customer shows interest with pain point
        pain_point = random.choice(self.ngx_contexts['pain_points'])
        industry = random.choice(self.ngx_contexts['industries'])
        messages.append({
            "role": "user",
            "content": f"Hola, tengo un {industry} y {pain_point}. ¿Me pueden ayudar?"
        })
        
        # Assistant provides targeted solution
        benefit = random.choice(self.ngx_contexts['benefits'])
        messages.append({
            "role": "assistant",
            "content": f"¡Por supuesto! Entiendo perfectamente tu situación. NGX AGENTS ACCESS puede ayudarte a {benefit}. Con nuestros 11 agentes especializados, podrás automatizar completamente la atención a tus clientes."
        })
        
        # Customer asks for more details
        if objection_type == "price":
            messages.append({
                "role": "user",
                "content": "Suena bien, pero ¿cuánto cuesta todo esto?"
            })
            messages.append({
                "role": "assistant",
                "content": "NGX AGENTS ACCESS tiene una inversión de $2,700 MXN al mes, que incluye los 11 agentes trabajando 24/7 para tu negocio."
            })
        elif objection_type == "features":
            messages.append({
                "role": "user",
                "content": "¿Y qué exactamente pueden hacer estos agentes?"
            })
            messages.append({
                "role": "assistant",
                "content": "Los agentes pueden agendar citas, hacer seguimiento a leads, responder en WhatsApp, crear contenido para redes sociales, y mucho más."
            })
        else:
            messages.append({
                "role": "user",
                "content": "Interesante, cuéntame más sobre cómo funciona."
            })
        
        # Customer expresses objection
        objection_phrase = random.choice(objection_phrases)
        if objection_type == "price" and "$" not in objection_phrase:
            messages.append({
                "role": "user",
                "content": f"Uff, {objection_phrase}. Es bastante dinero para mi {industry}."
            })
        else:
            messages.append({
                "role": "user",
                "content": f"{objection_phrase}"
            })
        
        return messages
        
    def _generate_conversation_with_need(self, need_category: str,
                                       need_phrases: List[str]) -> List[Dict[str, Any]]:
        """Generate a conversation that expresses specific needs."""
        messages = []
        
        # Initial interaction
        industry = random.choice(self.ngx_contexts['industries'])
        need_phrase = random.choice(need_phrases)
        messages.append({
            "role": "user",
            "content": f"Hola, tengo un {industry} y {need_phrase}"
        })
        
        # Assistant response
        messages.append({
            "role": "assistant",
            "content": "¡Hola! Me da mucho gusto que estés interesado en NGX. ¿Qué aspectos específicos te gustaría conocer?"
        })
        
        # Customer elaborates on need based on category
        if need_category == "pricing":
            messages.append({
                "role": "user",
                "content": "Principalmente quiero entender la inversión necesaria. Mi negocio es pequeño y necesito saber si puedo pagarlo."
            })
            messages.append({
                "role": "assistant",
                "content": "Entiendo tu preocupación. NGX AGENTS ACCESS cuesta $2,700 MXN al mes, pero considera que reemplaza a varios empleados y trabaja 24/7."
            })
            messages.append({
                "role": "user",
                "content": random.choice(["¿Hay planes más económicos?", "¿Puedo pagar anual con descuento?", "¿Incluye todo o hay costos extra?"])
            })
        elif need_category == "features":
            messages.append({
                "role": "user",
                "content": f"Me gustaría saber qué funcionalidades incluye. Específicamente necesito {random.choice(['agendar citas', 'responder WhatsApp', 'hacer seguimiento', 'generar contenido'])}."
            })
            messages.append({
                "role": "assistant",
                "content": "¡Excelente pregunta! NGX incluye 11 agentes especializados que cubren todas las necesidades de tu negocio fitness."
            })
            messages.append({
                "role": "user",
                "content": random.choice(["¿Pueden trabajar todos al mismo tiempo?", "¿Cómo se configuran?", "¿Qué hace cada agente?"])
            })
        elif need_category == "support":
            messages.append({
                "role": "user",
                "content": "Es importante para mí entender qué tipo de ayuda tendré. No soy muy técnico."
            })
            messages.append({
                "role": "assistant",
                "content": "No te preocupes, nuestro equipo de soporte está para ayudarte en cada paso. Ofrecemos capacitación completa."
            })
            messages.append({
                "role": "user",
                "content": random.choice(["¿El soporte es en español?", "¿Cuánto tardan en responder?", "¿Me ayudan a configurar todo?"])
            })
        elif need_category == "integration":
            messages.append({
                "role": "user",
                "content": f"Necesito saber si se integra con mi sistema actual. Uso {random.choice(['Mindbody', 'Excel', 'Google Calendar', 'mi propio CRM'])}."
            })
            messages.append({
                "role": "assistant",
                "content": "NGX se integra con los principales sistemas del mercado fitness. Podemos conectarnos mediante API o webhooks."
            })
            messages.append({
                "role": "user",
                "content": random.choice(["¿Es complicada la integración?", "¿Ustedes la hacen?", "¿Qué pasa con mis datos actuales?"])
            })
        elif need_category == "roi":
            messages.append({
                "role": "user",
                "content": "Necesito justificar esta inversión. ¿Cuál es el retorno típico?"
            })
            messages.append({
                "role": "assistant",
                "content": "Nuestros clientes típicamente ven un ROI de 10x en los primeros 6 meses, aumentando sus ventas significativamente."
            })
            messages.append({
                "role": "user",
                "content": random.choice(["¿Tienen casos reales?", "¿En cuánto tiempo recupero la inversión?", "¿Qué resultados garantizan?"])
            })
        else:
            messages.append({
                "role": "user",
                "content": "Necesito más información general para evaluar si es para mí."
            })
            
        return messages
        
    def _generate_conversation_with_conversion_signals(self, conversion_level: str,
                                                     signals: List[str]) -> List[Dict[str, Any]]:
        """Generate a conversation with specific conversion signals."""
        messages = []
        industry = random.choice(self.ngx_contexts['industries'])
        
        # Build conversation based on conversion level
        if conversion_level == "high":
            # Positive, engaged conversation - ready to buy
            messages.extend([
                {"role": "user", "content": f"He estado investigando sobre NGX y creo que es justo lo que mi {industry} necesita"},
                {"role": "assistant", "content": "¡Qué alegría escuchar eso! ¿Qué es lo que más te ha convencido de NGX AGENTS ACCESS?"},
                {"role": "user", "content": f"Definitivamente {random.choice(self.ngx_contexts['benefits'])}. Mi competencia está creciendo mucho y no puedo quedarme atrás."},
                {"role": "assistant", "content": "Tienes toda la razón. Con NGX estarás varios pasos adelante. ¿Te gustaría comenzar hoy mismo?"},
                {"role": "user", "content": f"{random.choice(signals)}. Ya hablé con mi socio y estamos listos."}
            ])
        elif conversion_level == "medium":
            # Somewhat interested but needs more convincing
            messages.extend([
                {"role": "user", "content": f"Estoy evaluando diferentes opciones para automatizar mi {industry}"},
                {"role": "assistant", "content": "Excelente que estés buscando automatizar. ¿Qué aspectos son más importantes para tu negocio?"},
                {"role": "user", "content": f"Principalmente {random.choice(self.ngx_contexts['pain_points'])}. Es mi mayor problema ahora."},
                {"role": "assistant", "content": "NGX está diseñado específicamente para resolver ese problema. Nuestros clientes han visto resultados en menos de 30 días."},
                {"role": "user", "content": f"{random.choice(signals)}, pero aún tengo algunas preguntas."}
            ])
        else:
            # Low interest or very skeptical
            messages.extend([
                {"role": "user", "content": f"Vi su publicidad pero no estoy seguro si esto es para mi {industry}"},
                {"role": "assistant", "content": "Entiendo tu escepticismo. ¿Cuál es tu mayor preocupación sobre implementar una solución como NGX?"},
                {"role": "user", "content": f"Es que {random.choice(self.ngx_contexts['pain_points'])}, pero no sé si la tecnología es la solución."},
                {"role": "assistant", "content": "Te entiendo. Muchos de nuestros clientes pensaban lo mismo al principio. ¿Te gustaría ver algunos casos de éxito?"},
                {"role": "user", "content": f"{random.choice(signals)}. No estoy convencido todavía."}
            ])
            
        return messages
        
    def generate_complete_training_dataset(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate a complete training dataset for all predictive services.
        
        Returns:
            Dictionary with training data for each service type
        """
        logger.info("Generating complete training dataset...")
        
        dataset = {
            "objection": self.generate_objection_training_data(200),
            "needs": self.generate_needs_training_data(200),
            "conversion": self.generate_conversion_training_data(200)
        }
        
        logger.info(f"Generated {sum(len(data) for data in dataset.values())} total training samples")
        
        return dataset
        
    def export_training_data(self, dataset: Dict[str, List[Dict[str, Any]]], 
                           output_path: str = "training_data.json") -> None:
        """
        Export training data to a JSON file.
        
        Args:
            dataset: Training dataset to export
            output_path: Path to save the JSON file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            logger.info(f"Training data exported to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting training data: {e}")