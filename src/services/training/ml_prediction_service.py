"""
Unified ML Prediction Service for NGX Voice Sales Agent.

This service integrates the trained ML models with the existing predictive services,
providing a seamless interface for making predictions.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.services.training.ml_model_trainer import MLModelTrainer
from src.services.training.training_data_generator import TrainingDataGenerator

logger = logging.getLogger(__name__)

class MLPredictionService:
    """
    Unified service for ML predictions using trained models.
    """
    
    def __init__(self, models_dir: str = "models"):
        """
        Initialize the ML prediction service.
        
        Args:
            models_dir: Directory where trained models are stored
        """
        self.trainer = MLModelTrainer(models_dir)
        self.models_loaded = False
        self._load_all_models()
        
    def _load_all_models(self) -> None:
        """Load all available models."""
        try:
            models = ["objection", "needs", "conversion"]
            loaded_count = 0
            
            for model_name in models:
                if self.trainer.load_model(model_name):
                    loaded_count += 1
                    logger.info(f"Loaded {model_name} model successfully")
                else:
                    logger.warning(f"Could not load {model_name} model")
            
            self.models_loaded = loaded_count > 0
            
            if not self.models_loaded:
                logger.warning("No trained models found. Training with synthetic data...")
                self._train_initial_models()
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.models_loaded = False
    
    def _train_initial_models(self) -> None:
        """Train initial models with synthetic data if no models exist."""
        try:
            logger.info("Generating synthetic training data...")
            generator = TrainingDataGenerator()
            dataset = generator.generate_complete_training_dataset()
            
            # Train objection model
            if "objection" in dataset:
                logger.info("Training objection model...")
                result = self.trainer.train_objection_model(dataset["objection"])
                if result["success"]:
                    logger.info(f"Objection model trained with {result['accuracy']:.2f} accuracy")
            
            # Train needs model
            if "needs" in dataset:
                logger.info("Training needs model...")
                result = self.trainer.train_needs_model(dataset["needs"])
                if result["success"]:
                    logger.info(f"Needs model trained with {result['accuracy']:.2f} accuracy")
            
            # Train conversion model
            if "conversion" in dataset:
                logger.info("Training conversion model...")
                result = self.trainer.train_conversion_model(dataset["conversion"])
                if result["success"]:
                    logger.info(f"Conversion model trained with {result['accuracy']:.2f} accuracy")
            
            self.models_loaded = True
            
        except Exception as e:
            logger.error(f"Error training initial models: {e}")
            self.models_loaded = False
    
    async def predict_objections(self, messages: List[Dict[str, Any]], 
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict potential objections from conversation.
        
        Args:
            messages: Conversation messages
            context: Additional context (customer profile, etc.)
            
        Returns:
            Prediction results with objection types and responses
        """
        try:
            if not self.models_loaded:
                return {
                    "objections": [],
                    "confidence": 0,
                    "error": "Models not loaded"
                }
            
            # Get ML predictions
            ml_prediction = self.trainer.predict_objection(messages)
            
            if "error" in ml_prediction:
                return {
                    "objections": [],
                    "confidence": 0,
                    "error": ml_prediction["error"]
                }
            
            # Enhance with response suggestions based on NGX context
            objections = []
            for pred in ml_prediction.get("all_predictions", []):
                objection_type = pred["type"]
                confidence = pred["confidence"]
                
                # Get suggested responses for this objection type
                responses = self._get_objection_responses(objection_type)
                
                objections.append({
                    "type": objection_type,
                    "confidence": confidence,
                    "suggested_responses": responses
                })
            
            return {
                "objections": objections,
                "primary_objection": ml_prediction.get("primary_objection"),
                "confidence": ml_prediction.get("confidence", 0),
                "signals": self._extract_objection_signals(messages)
            }
            
        except Exception as e:
            logger.error(f"Error predicting objections: {e}")
            return {
                "objections": [],
                "confidence": 0,
                "error": str(e)
            }
    
    async def predict_needs(self, messages: List[Dict[str, Any]], 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict customer needs from conversation.
        
        Args:
            messages: Conversation messages
            context: Additional context
            
        Returns:
            Prediction results with need categories and recommendations
        """
        try:
            if not self.models_loaded:
                return {
                    "needs": [],
                    "confidence": 0,
                    "error": "Models not loaded"
                }
            
            # Get ML predictions
            ml_prediction = self.trainer.predict_needs(messages)
            
            if "error" in ml_prediction:
                return {
                    "needs": [],
                    "confidence": 0,
                    "error": ml_prediction["error"]
                }
            
            # Enhance with NGX-specific recommendations
            needs = []
            for need_pred in ml_prediction.get("all_needs", []):
                need_type = need_pred["need"]
                confidence = need_pred["confidence"]
                
                # Get recommendations for this need
                recommendations = self._get_need_recommendations(need_type)
                
                needs.append({
                    "type": need_type,
                    "confidence": confidence,
                    "recommendations": recommendations
                })
            
            return {
                "needs": needs,
                "primary_need": ml_prediction.get("primary_need"),
                "confidence": ml_prediction.get("confidence", 0),
                "next_questions": self._generate_discovery_questions(needs)
            }
            
        except Exception as e:
            logger.error(f"Error predicting needs: {e}")
            return {
                "needs": [],
                "confidence": 0,
                "error": str(e)
            }
    
    async def predict_conversion(self, messages: List[Dict[str, Any]], 
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict conversion probability from conversation.
        
        Args:
            messages: Conversation messages
            context: Additional context
            
        Returns:
            Prediction results with conversion probability and recommendations
        """
        try:
            if not self.models_loaded:
                return {
                    "probability": 0,
                    "conversion_level": "low",
                    "error": "Models not loaded"
                }
            
            # Get ML predictions
            ml_prediction = self.trainer.predict_conversion(messages)
            
            if "error" in ml_prediction:
                return {
                    "probability": 0,
                    "conversion_level": "low",
                    "error": ml_prediction["error"]
                }
            
            probability = ml_prediction.get("probability", 0)
            level = ml_prediction.get("conversion_level", "low")
            
            # Get conversion strategies based on level
            strategies = self._get_conversion_strategies(level, messages)
            
            # Determine optimal next action
            next_action = self._determine_next_action(level, probability)
            
            return {
                "will_convert": ml_prediction.get("will_convert", False),
                "probability": probability,
                "conversion_level": level,
                "positive_signals": ml_prediction.get("positive_signals", 0),
                "engagement_score": ml_prediction.get("engagement_score", 0),
                "recommended_strategies": strategies,
                "next_action": next_action,
                "urgency_level": self._calculate_urgency(probability, messages)
            }
            
        except Exception as e:
            logger.error(f"Error predicting conversion: {e}")
            return {
                "probability": 0,
                "conversion_level": "low",
                "error": str(e)
            }
    
    def _get_objection_responses(self, objection_type: str) -> List[str]:
        """Get NGX-specific responses for objection types."""
        responses = {
            "price": [
                "Entiendo tu preocupación por el precio. Considera que NGX reemplaza a 3-4 empleados trabajando 24/7. Un empleado cuesta mínimo $8,000 MXN al mes, mientras que NGX cuesta solo $2,700.",
                "El ROI promedio de nuestros clientes es de 10x en 6 meses. Es decir, por cada peso invertido, recuperan 10.",
                "Ofrecemos garantía de satisfacción de 30 días. Si no ves resultados, te devolvemos tu dinero."
            ],
            "need": [
                "Muchos de nuestros clientes pensaban lo mismo hasta que vieron cómo perdían 5-10 leads diarios por no responder a tiempo.",
                "¿Sabías que el 78% de los clientes compran al primero que les responde? NGX te garantiza ser siempre el primero.",
                "Déjame mostrarte cómo gimnasios similares al tuyo aumentaron sus ventas 3x con NGX."
            ],
            "trust": [
                "Trabajamos con más de 500 gimnasios y centros fitness en México. Te puedo compartir casos de éxito específicos.",
                "Iniciamos con una prueba piloto de 30 días con garantía de devolución. Cero riesgo para ti.",
                "Te puedo conectar con Juan de FitLife Gym que triplicó sus membresías en 3 meses con NGX."
            ],
            "urgency": [
                "Entiendo que necesites tiempo. Mientras tanto, estás perdiendo aproximadamente 10 leads por día. Eso son 300 clientes potenciales al mes.",
                "Perfecto, tómate el tiempo que necesites. Solo considera que cada día sin NGX es dinero que dejas en la mesa.",
                "Claro, consúltalo. Mientras tanto, ¿te gustaría ver una demo en vivo de 15 minutos?"
            ],
            "features": [
                "NGX incluye 11 agentes especializados: Ventas, Nutrición, Seguimiento, Social Media, y más. Todo incluido sin costo extra.",
                "Sí, se integra perfectamente con WhatsApp, Instagram, Facebook y tu sistema actual. La configuración toma menos de 24 horas.",
                "Cada agente está entrenado específicamente para fitness. Por ejemplo, el agente de nutrición conoce más de 1,000 planes alimenticios."
            ],
            "competition": [
                "A diferencia de otras soluciones genéricas, NGX está 100% especializado en fitness. Conocemos tu industria.",
                "NGX es el único con 11 agentes trabajando en conjunto. La competencia ofrece chatbots básicos, nosotros ofrecemos un equipo completo.",
                "Nuestros clientes que migraron de la competencia reportan 5x más conversiones con NGX."
            ]
        }
        
        return responses.get(objection_type, [
            "Entiendo tu punto. ¿Qué específicamente te preocupa?",
            "Es una preocupación válida. Déjame explicarte cómo NGX aborda ese tema.",
            "Muchos clientes tenían la misma duda. Te comparto cómo lo resolvimos."
        ])
    
    def _get_need_recommendations(self, need_type: str) -> List[str]:
        """Get recommendations based on identified needs."""
        recommendations = {
            "information": [
                "Compartir video demo de 5 minutos mostrando NGX en acción",
                "Enviar PDF con casos de éxito de gimnasios similares",
                "Ofrecer llamada de 15 minutos para responder preguntas específicas"
            ],
            "pricing": [
                "Mostrar calculadora de ROI personalizada",
                "Explicar modelo de pricing y qué incluye cada peso invertido",
                "Ofrecer descuento por pago anual (20% de ahorro)"
            ],
            "features": [
                "Demo en vivo de los 11 agentes trabajando",
                "Mostrar integraciones disponibles con sus sistemas actuales",
                "Compartir roadmap de nuevas funcionalidades"
            ],
            "support": [
                "Explicar programa de onboarding de 7 días",
                "Mostrar canales de soporte 24/7 en español",
                "Ofrecer sesión de entrenamiento personalizada gratis"
            ],
            "integration": [
                "Realizar auditoría gratuita de compatibilidad",
                "Mostrar documentación de API y webhooks",
                "Ofrecer implementación llave en mano sin costo"
            ],
            "roi": [
                "Compartir caso de estudio detallado con métricas reales",
                "Calcular ROI proyectado basado en su volumen actual",
                "Mostrar garantía de resultados o devolución"
            ]
        }
        
        return recommendations.get(need_type, [
            "Proporcionar información detallada",
            "Ofrecer consultoría personalizada",
            "Compartir recursos relevantes"
        ])
    
    def _generate_discovery_questions(self, needs: List[Dict[str, Any]]) -> List[str]:
        """Generate discovery questions based on identified needs."""
        questions = []
        
        for need in needs[:2]:  # Focus on top 2 needs
            need_type = need["type"]
            
            if need_type == "pricing":
                questions.extend([
                    "¿Cuál es tu presupuesto mensual para herramientas de marketing y ventas?",
                    "¿Cuánto te cuesta actualmente perder un lead?"
                ])
            elif need_type == "features":
                questions.extend([
                    "¿Cuál es tu mayor reto operativo actualmente?",
                    "¿Qué proceso te gustaría automatizar primero?"
                ])
            elif need_type == "roi":
                questions.extend([
                    "¿Cuántos leads recibes al mes actualmente?",
                    "¿Cuál es tu tasa de conversión actual?"
                ])
            elif need_type == "integration":
                questions.extend([
                    "¿Qué sistemas utilizas actualmente para gestionar tu negocio?",
                    "¿Tienes algún requisito técnico específico?"
                ])
        
        return questions[:3]  # Return max 3 questions
    
    def _get_conversion_strategies(self, level: str, messages: List[Dict[str, Any]]) -> List[str]:
        """Get conversion strategies based on probability level."""
        strategies = {
            "high": [
                "Crear urgencia mencionando la oferta limitada del mes",
                "Ofrecer bono exclusivo por cerrar hoy (mes gratis de soporte premium)",
                "Enviar link de pago directo con descuento aplicado",
                "Proponer llamada de cierre en los próximos 30 minutos"
            ],
            "medium": [
                "Ofrecer prueba gratuita de 14 días sin compromiso",
                "Compartir testimonio en video de cliente similar",
                "Proponer demo personalizada enfocada en su problema principal",
                "Enviar comparativa detallada NGX vs competencia"
            ],
            "low": [
                "Nutrir con contenido educativo sobre automatización en fitness",
                "Invitar a webinar gratuito sobre crecimiento de gimnasios",
                "Mantener seguimiento suave con tips semanales",
                "Ofrecer auditoría gratuita de su proceso de ventas actual"
            ]
        }
        
        return strategies.get(level, strategies["low"])
    
    def _determine_next_action(self, level: str, probability: float) -> str:
        """Determine the optimal next action based on conversion probability."""
        if level == "high" or probability > 0.8:
            return "Proceder al cierre inmediato - enviar link de pago y agendar onboarding"
        elif level == "medium" or probability > 0.5:
            return "Ofrecer incentivo adicional - demo personalizada o período de prueba extendido"
        else:
            return "Continuar educando - enviar casos de éxito y mantener seguimiento semanal"
    
    def _calculate_urgency(self, probability: float, messages: List[Dict[str, Any]]) -> str:
        """Calculate urgency level for follow-up."""
        message_count = len(messages)
        
        if probability > 0.7 and message_count > 5:
            return "alta"
        elif probability > 0.5 or message_count > 10:
            return "media"
        else:
            return "baja"
    
    def _extract_objection_signals(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract objection signals from conversation."""
        signals = {
            "price_sensitivity": False,
            "competitor_mentions": False,
            "hesitation_detected": False,
            "needs_more_info": False
        }
        
        for msg in messages:
            content = msg["content"].lower()
            
            if any(word in content for word in ["caro", "precio", "costo", "presupuesto", "$"]):
                signals["price_sensitivity"] = True
            
            if any(word in content for word in ["otro", "competencia", "comparar", "opciones"]):
                signals["competitor_mentions"] = True
            
            if any(word in content for word in ["no sé", "tal vez", "quizás", "pensarlo", "dudas"]):
                signals["hesitation_detected"] = True
            
            if any(word in content for word in ["cómo", "qué", "cuándo", "explicar", "detalles"]):
                signals["needs_more_info"] = True
        
        return signals