#!/usr/bin/env python3
"""
NGX Master Knowledge System
Sistema de conocimiento basado en los documentos oficiales de NGX v3.0
Contiene información real sobre NGX AGENTS ACCESS y Coaching Híbrido NGX
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import json
from dataclasses import dataclass, asdict
from datetime import datetime

class NGXArchetype(Enum):
    PRIME = "prime"  # El Optimizador - Performance ejecutivo
    LONGEVITY = "longevity"  # El Arquitecto de Vida - Vitalidad sostenible

class NGXModel(Enum):
    AGENTS_ACCESS = "agents_access"  # Suscripciones $79-$199
    HYBRID_COACHING = "hybrid_coaching"  # Programas $3,997

@dataclass
class NGXTier:
    name: str
    monthly_price: int
    annual_price: int
    daily_consultations: str
    features: List[str]
    upsell_hook: str

@dataclass
class NGXProgram:
    name: str
    archetype: NGXArchetype
    price_full: int
    price_installments: str
    duration_weeks: int
    structure: List[str]
    benefits: List[str]
    target_audience: List[str]


class NGXMasterKnowledge:
    """Sistema de conocimiento real de NGX basado en documentos oficiales"""
    
    def __init__(self):
        self.agents_access_tiers = self._load_agents_access_tiers()
        self.hybrid_programs = self._load_hybrid_programs()
        self.competitive_advantages = self._load_competitive_advantages()
        self.hybrid_intelligence_engine = self._load_hie_info()
        
    def _load_agents_access_tiers(self) -> List[NGXTier]:
        """Carga los tiers reales de NGX AGENTS ACCESS según doc oficial"""
        return [
            NGXTier(
                name="Essential",
                monthly_price=79,
                annual_price=790,
                daily_consultations="12 consultas diarias",
                features=[
                    "Chat con IA avanzada (texto)",
                    "Programas autogenerados inteligentes",
                    "Seguimiento básico de progreso",
                    "Acceso completo al sistema HIE",
                    "Motor de Hibridación Inteligente básico"
                ],
                upsell_hook="Introducción accesible al sistema HIE; +15% en energía diaria. Upgrade: 'Desbloquea biomarcadores en Pro'"
            ),
            NGXTier(
                name="Pro", 
                monthly_price=149,
                annual_price=1490,
                daily_consultations="24 consultas diarias",
                features=[
                    "Todo de Essential +",
                    "Análisis inteligente de imágenes (comidas/equipo)",
                    "Integración completa con wearables", 
                    "Reportes semanales automatizados",
                    "2 análisis PDF detallados/mes"
                ],
                upsell_hook="Optimización avanzada; +20% en vitalidad. Upgrade: 'Tu Motor HIE detecta riesgos - eleva con Elite'"
            ),
            NGXTier(
                name="Elite",
                monthly_price=199, 
                annual_price=1990,
                daily_consultations="Ilimitado",
                features=[
                    "Todo de Pro +",
                    "Audio/voz con ElevenLabs",
                    "Micro-videos formativos personalizados",
                    "Ajustes tiempo real basados en HRV",
                    "Soporte prioritario 2h"
                ],
                upsell_hook="Máxima transformación; +25% en longevidad. Próximo salto: 'Coaching 1:1 Híbrido'"
            )
        ]
    
    def _load_hybrid_programs(self) -> List[NGXProgram]:
        """Carga los programas de Coaching Híbrido reales"""
        return [
            NGXProgram(
                name="NGX PRIME",
                archetype=NGXArchetype.PRIME,
                price_full=3997,
                price_installments="$1,499 x 3 cuotas",
                duration_weeks=20,
                structure=[
                    "Semanas 1-4: Fundación",
                    "Semanas 5-12: Aceleración", 
                    "Semanas 13-20: Maestría"
                ],
                benefits=[
                    "+25% productividad ejecutiva",
                    "ROI ejecutivo demostrable",
                    "Optimización cognitiva pico",
                    "Manejo avanzado de estrés laboral"
                ],
                target_audience=[
                    "Ejecutivos de alto rendimiento",
                    "CEOs y fundadores",
                    "Líderes empresariales",
                    "Profesionales de elite"
                ]
            ),
            NGXProgram(
                name="NGX LONGEVITY",
                archetype=NGXArchetype.LONGEVITY,
                price_full=3997,
                price_installments="$1,499 x 3 cuotas", 
                duration_weeks=20,
                structure=[
                    "Semanas 1-4: Evaluación integral",
                    "Semanas 5-12: Construcción de base",
                    "Semanas 13-20: Sostenibilidad"
                ],
                benefits=[
                    "+25% vitalidad sostenible",
                    "Healthspan extendido 5-10 años",
                    "Prevención proactiva",
                    "Resiliencia a largo plazo"
                ],
                target_audience=[
                    "Adultos 45+ enfocados en longevidad",
                    "Profesionales health-conscious", 
                    "Individuos prevention-focused",
                    "Buscadores de vitalidad sostenible"
                ]
            )
        ]
    
    def _load_competitive_advantages(self) -> List[Dict[str, Any]]:
        """Ventajas competitivas reales de NGX según documentos"""
        return [
            {
                "advantage": "Motor de Hibridación Inteligente",
                "description": "Sistema de 2 capas: adaptación por arquetipo + modulación por data individual",
                "why_unbeatable": "Imposible de clonar - requiere años de desarrollo y training data"
            },
            {
                "advantage": "Inteligencia Simbiótica",
                "description": "Nueva categoría que combina autonomía IA con coaching humano estratégico",
                "why_unbeatable": "Pioneros en esta categoría - competidores están en paradigmas obsoletos"
            },
            {
                "advantage": "Ecosistema de IA Avanzada",
                "description": "Sistema integrado con inteligencia colaborativa y coordinación automática",
                "why_unbeatable": "Complejidad técnica que requiere arquitectura propietaria"
            },
            {
                "advantage": "Coaching Predictivo vs Reactivo", 
                "description": "Briefings de inteligencia pre-sesión con insights profundos",
                "why_unbeatable": "Nivel de sophistication imposible con herramientas genéricas"
            },
            {
                "advantage": "Personalización Radical",
                "description": "200+ puntos de data vs programas genéricos",
                "why_unbeatable": "Database y algoritmos propietarios de años de desarrollo"
            }
        ]
    
    def _load_hie_info(self) -> Dict[str, Any]:
        """Información real del Motor de Hibridación Inteligente"""
        return {
            "name": "Motor de Hibridación Inteligente",
            "description": "Sistema de dos capas que garantiza personalización radical",
            "layer_1": {
                "name": "Capa Estratégica - Adaptación por Arquetipo",
                "function": "Define el 'porqué' y tono de interacción",
                "archetypes": {
                    "PRIME": "El Optimizador - Performance ejecutivo y productividad",
                    "LONGEVITY": "El Arquitecto de Vida - Vitalidad sostenible y prevención"
                }
            },
            "layer_2": {
                "name": "Capa Fisiológica - Modulación por Data Individual", 
                "function": "Ajusta ejecución en tiempo real para seguridad y eficacia",
                "data_points": [
                    "Edad y género",
                    "Biomarcadores de wearables",
                    "Historial de lesiones",
                    "Capacidad de recuperación",
                    "Preferencias individuales",
                    "Métricas de progreso"
                ]
            },
            "key_benefits": [
                "Ninguna experiencia NGX es verdaderamente 'sin acompañamiento'",
                "IA siempre guiando, protegiendo y personalizando",
                "Garantía de seguridad y eficacia en todos los niveles",
                "Adaptación automática que mejora con cada interacción"
            ]
        }
    
    def get_archetype_info(self, archetype: NGXArchetype) -> Dict[str, Any]:
        """Obtiene información específica del arquetipo"""
        archetype_data = {
            NGXArchetype.PRIME: {
                "name": "El Optimizador",
                "target_audience": "Profesionales y ejecutivos 25-50 años",
                "focus": "Performance ejecutivo, productividad, competitive advantage",
                "key_benefits": [
                    "Optimización cognitiva pico",
                    "Sustained energy para jornadas largas", 
                    "Stress management para decisiones críticas",
                    "Recovery optimization para consistency"
                ],
                "ideal_for": [
                    "CEOs y fundadores",
                    "Ejecutivos de alto rendimiento",
                    "Entrepreneurs",
                    "Líderes empresariales"
                ]
            },
            NGXArchetype.LONGEVITY: {
                "name": "El Arquitecto de Vida",
                "target_audience": "Adultos 45+ enfocados en longevidad",
                "focus": "Vitalidad sostenible, prevención, healthspan extension",
                "key_benefits": [
                    "Vitalidad diaria incrementada",
                    "Función cognitiva preservada",
                    "Muscle mass maintenance",
                    "Optimización metabólica"
                ],
                "ideal_for": [
                    "Profesionales health-conscious 45+",
                    "Individuos prevention-focused",
                    "Buscadores de aging saludable",
                    "Optimizadores de healthspan"
                ]
            }
        }
        return archetype_data.get(archetype, {})
    
    def _get_relevant_features_for_archetype(self, archetype: NGXArchetype) -> List[str]:
        """Obtiene características relevantes del HIE para el arquetipo."""
        if archetype == NGXArchetype.PRIME:
            return [
                "Optimización cognitiva basada en ciclos circadianos",
                "Análisis de productividad y gestión de energía ejecutiva",
                "Protocolos de recuperación para alto rendimiento",
                "Adaptación inteligente a viajes y cambios de zona horaria",
                "Monitoreo de estrés y técnicas de resiliencia ejecutiva"
            ]
        else:  # LONGEVITY
            return [
                "Análisis predictivo de marcadores de longevidad",
                "Protocolos personalizados de antiaging",
                "Monitoreo de función metabólica y hormonal",
                "Prevención proactiva basada en genética y estilo de vida",
                "Optimización de sueño y recuperación profunda"
            ]
    
    def get_model_comparison(self) -> Dict[str, Any]:
        """Comparación entre NGX AGENTS ACCESS vs Coaching Híbrido"""
        return {
            "agents_access": {
                "model": "Autonomía Guiada por IA",
                "target": "Individuo autónomo, disciplinado y proactivo",
                "value_prop": "Director de tu propia orquesta biológica",
                "interaction": "Directo 24/7 con sistema HIE completo",
                "price_range": "$79-$199/mes",
                "best_for": "Self-directed optimization con herramientas de vanguardia"
            },
            "hybrid_coaching": {
                "model": "Inteligencia Simbiótica Humano-IA", 
                "target": "Ejecutivos/líderes que buscan máximo nivel",
                "value_prop": "Director de orquesta + mejores músicos del planeta",
                "interaction": "Coach humano estratégico + ejecución IA 24/7",
                "price_range": "$3,997 programa 20 semanas",
                "best_for": "Transformación garantizada con accountability humana"
            }
        }
    
    def generate_ngx_context(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Genera contexto NGX para conversaciones basado en usuario real"""
        
        # Detectar arquetipo probable
        age = user_context.get('age', 35)
        profession = user_context.get('profession', '').lower()
        
        # Lógica de detección de arquetipo
        if age >= 45 or any(keyword in profession for keyword in ['health', 'wellness', 'longevity']):
            suggested_archetype = NGXArchetype.LONGEVITY
        else:
            suggested_archetype = NGXArchetype.PRIME
            
        # Detectar modelo NGX apropiado
        budget_indicator = user_context.get('budget_sensitivity', 'medium')
        executive_level = any(keyword in profession for keyword in ['ceo', 'founder', 'executive', 'director'])
        
        if executive_level and budget_indicator == 'low':
            suggested_model = NGXModel.HYBRID_COACHING
        else:
            suggested_model = NGXModel.AGENTS_ACCESS
        
        return {
            "suggested_archetype": suggested_archetype.value,
            "archetype_info": self.get_archetype_info(suggested_archetype),
            "suggested_model": suggested_model.value,
            "model_comparison": self.get_model_comparison(),
            "relevant_features": self._get_relevant_features_for_archetype(suggested_archetype),
            "hie_explanation": self.hybrid_intelligence_engine,
            "competitive_advantages": self.competitive_advantages[:3],  # Top 3
            "pricing_context": {
                "agents_access_tiers": self.agents_access_tiers,
                "hybrid_programs": [p for p in self.hybrid_programs if p.archetype == suggested_archetype]
            }
        }

# Global instance
_ngx_knowledge = None

def get_ngx_knowledge() -> NGXMasterKnowledge:
    """Get global NGX knowledge instance"""
    global _ngx_knowledge
    if _ngx_knowledge is None:
        _ngx_knowledge = NGXMasterKnowledge()
    return _ngx_knowledge

if __name__ == "__main__":
    # Demo del sistema NGX real
    ngx_knowledge = NGXMasterKnowledge()
    
    print("🚀 NGX Master Knowledge System (REAL)")
    print("=" * 50)
    
    # Demo context generation
    test_context = {
        'age': 42,
        'profession': 'CEO',
        'budget_sensitivity': 'low'
    }
    
    ngx_context = ngx_knowledge.generate_ngx_context(test_context)
    print(f"📊 NGX Context for CEO (42):")
    print(f"   Suggested archetype: {ngx_context['suggested_archetype']}")
    print(f"   Suggested model: {ngx_context['suggested_model']}")
    print(f"   Relevant features: {len(ngx_context['relevant_features'])}")
    print()
    
    print("✅ NGX Real Knowledge System ready!")