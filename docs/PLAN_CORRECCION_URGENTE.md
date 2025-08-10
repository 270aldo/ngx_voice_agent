# 🚨 PLAN DE CORRECCIÓN URGENTE - NGX Voice Sales Agent

## OBJETIVO: Sistema funcional en 4 horas

## FASE 1: DIAGNÓSTICO RÁPIDO (30 min)

### 1.1 Encontrar el error de datetime
```bash
# Buscar dónde se usa fromisoformat
grep -r "fromisoformat" src/

# Buscar campos datetime en modelos
grep -r "datetime" src/models/
```

### 1.2 Mapear métodos faltantes
```bash
# Buscar las llamadas a métodos que no existen
grep -r "generate_empathic_response" src/
grep -r "detect_tier" src/
grep -r "analyze_emotional_state" src/
```

## FASE 2: CORRECCIONES CRÍTICAS (2 horas)

### 2.1 Arreglar serialización de datetime

**ARCHIVO**: `src/models/conversation.py`
```python
# CAMBIAR todos los campos datetime a str
class Message(BaseModel):
    timestamp: str  # NO datetime
    
# O agregar serializer personalizado
class Message(BaseModel):
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### 2.2 Crear métodos faltantes o stubs

**OPCIÓN A - Stubs rápidos**:
```python
# src/services/empathy_engine_service.py
def generate_empathic_response(self, *args, **kwargs):
    # STUB temporal
    return {
        "empathic_response": "Entiendo cómo te sientes.",
        "confidence": 0.8
    }

# src/services/tier_detection_service.py  
def detect_tier(self, *args, **kwargs):
    # STUB temporal
    return {
        "tier": "STANDARD",
        "confidence": 0.7
    }
```

**OPCIÓN B - Deshabilitar servicios problemáticos**:
```python
# src/services/conversation/emotional_processing.py
async def _analyze_emotional_state(self, message_text: str, state: ConversationState):
    # TEMPORAL - bypass
    return {
        "primary_emotion": "neutral",
        "confidence": 0.5
    }
```

### 2.3 Ajustar interfaces

**MockAgentWrapper**:
```python
# Verificar cuántos argumentos espera realmente
# Ajustar la llamada o el método
def process_message(self, message, context, extra_context=None):
    # Aceptar el parámetro extra
```

## FASE 3: TESTING RÁPIDO (1 hora)

### 3.1 Test mínimo de funcionamiento
```python
# test_basico.py
import requests

# 1. Crear conversación
# 2. Enviar "Hola"
# 3. Verificar respuesta 200
# 4. Enviar "¿Cuánto cuesta?"
# 5. Verificar respuesta 200
```

### 3.2 Verificar logs limpios
```bash
# No debe haber NINGÚN error 500
tail -f logs/api.log | grep -E "ERROR|500"
```

## FASE 4: VALIDACIÓN (30 min)

### 4.1 Ejecutar tests de inteligencia
```bash
python tests/intelligence/test_conversation_quality.py
# Debe pasar con score > 7
```

### 4.2 Test de carga básico
```bash
# 10 usuarios concurrentes por 1 minuto
python tests/performance/test_load.py --users 10 --duration 60
```

## ALTERNATIVA: MODO DEGRADADO INMEDIATO (1 hora)

Si no hay tiempo para arreglar todo:

### 1. Crear archivo de configuración
```python
# src/config/feature_flags.py
FEATURES = {
    "emotional_intelligence": False,  # Deshabilitar
    "tier_detection": False,         # Deshabilitar  
    "ml_tracking": False,            # Deshabilitar
    "empathy_engine": False          # Deshabilitar
}
```

### 2. Modificar orchestrator
```python
# src/services/conversation/orchestrator.py
if FEATURES["emotional_intelligence"]:
    emotional_analysis = await self._analyze_emotional_state(...)
else:
    emotional_analysis = {"primary_emotion": "neutral"}
```

### 3. Respuesta básica funcional
```python
# Asegurar que AL MENOS responda algo coherente
response = "Gracias por tu mensaje. " + basic_response
```

## CRITERIOS DE ÉXITO

1. **Sin errores 500** ✅
2. **Conversaciones completas** ✅
3. **Respuestas coherentes** ✅
4. **Tests básicos pasan** ✅

## NOTAS IMPORTANTES

- **NO** intentar arreglar todo perfectamente
- **SÍ** hacer que funcione lo básico
- **DOCUMENTAR** todos los cambios temporales
- **PLANEAR** corrección completa post-BETA

## COMANDO DE EMERGENCIA

Si todo falla, revertir a versión estable:
```bash
git checkout last-stable-tag
docker-compose up -d
```