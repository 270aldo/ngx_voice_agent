# NGX Voice Sales Agent - Capability Test Report

**Fecha:** 2025-07-25 20:06:06

**Duración total:** 62.5 segundos

## Resumen Ejecutivo

- **Tests totales:** 7
- **Exitosos:** 0 ✅
- **Fallidos:** 7 ❌
- **Tasa de éxito:** 0.0%

## Estado de Capacidades

| Capacidad | Estado | Descripción |
|-----------|--------|-------------|
| Ml Adaptive Learning | ❌ | Aprendizaje adaptativo con auto-deployment |
| Archetype Detection | ❌ | Detección de 5 arquetipos de cliente |
| Roi Personalization | ❌ | Cálculos ROI personalizados por profesión |
| Empathy Excellence | ❌ | Empatía de nivel 9+/10 con GPT-4o |
| Ab Testing | ❌ | A/B testing con Multi-Armed Bandit |
| Voice Adaptation | ❌ | 7 personalidades de voz adaptativas |
| Hie Integration | ❌ | Integración de 11 agentes HIE |

## Detalles de Tests

### ❌ test_ml_adaptive_evolution.py

- **Exit code:** 1
- **Error:** Traceback (most recent call last):
  File "/Users/aldoolivas/Desktop/NGX_Ecosystem/ngx_closer.Agent/tests/capabilities/test_ml_adaptive_evolution.py", line 356, in <module>
    exit_code = asyncio.run...

### ❌ test_archetype_detection.py

- **Exit code:** 1

### ❌ test_roi_personalization.py

- **Exit code:** 1

### ❌ test_empathy_excellence.py

- **Exit code:** 1
- **Error:** Traceback (most recent call last):
  File "/Users/aldoolivas/Desktop/NGX_Ecosystem/ngx_closer.Agent/tests/capabilities/test_empathy_excellence.py", line 25, in <module>
    raise ValueError("OPENAI_AP...

### ❌ test_ab_testing_bandit.py

- **Exit code:** 1
- **Error:** Traceback (most recent call last):
  File "/Users/aldoolivas/Desktop/NGX_Ecosystem/ngx_closer.Agent/tests/capabilities/test_ab_testing_bandit.py", line 418, in <module>
    exit_code = asyncio.run(mai...

### ❌ test_voice_adaptation.py

- **Exit code:** 1

### ❌ test_hie_agents_mention.py

- **Exit code:** 1
- **Error:** Traceback (most recent call last):
  File "/Users/aldoolivas/Desktop/NGX_Ecosystem/ngx_closer.Agent/tests/capabilities/test_hie_agents_mention.py", line 520, in <module>
    exit_code = asyncio.run(ma...

## ⚠️ Conclusión

Algunas capacidades requieren revisión antes de producción.
