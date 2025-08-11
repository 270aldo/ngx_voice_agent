# 🧪 TESTS CON API REAL - NGX Voice Sales Agent

## RESUMEN EJECUTIVO

Este documento explica TODOS los tests que funcionan con la API real en entorno real, NO mocks.

## 🔥 TESTS DE INTELIGENCIA (NUEVOS)

### 1. **test_conversation_quality.py** ✅ FUNCIONA PARCIALMENTE
- **QUÉ HACE**: Usa GPT-4 para evaluar la calidad de las respuestas del agente
- **CÓMO FUNCIONA**:
  1. Inicia conversación real con `/conversations/start`
  2. Envía mensajes de prueba
  3. GPT-4 evalúa cada respuesta en 7 categorías:
     - Calidad general (1-10)
     - Conocimiento del producto (1-10)
     - Técnica de venta (1-10)
     - Empatía (1-10)
     - Claridad (1-10)
     - Acción (1-10)
     - Brand voice (1-10)
- **RESULTADO ACTUAL**: 
  - Score promedio: 8.1/10
  - PASA el inicio de conversación ✅
  - FALLA al enviar mensajes subsecuentes (Error 500) ❌

### 2. **test_product_knowledge.py** ❌ NO FUNCIONA
- **QUÉ HACE**: Verifica que el agente conozca correctamente los productos
- **PRUEBAS**:
  - Precios exactos de PRIME ($79-$199)
  - Nombres de los 11 agentes HIE
  - No inventa información (hallucination detection)
  - Diferencia entre programas
- **RESULTADO**: Falla con Error 500 al enviar mensajes

## 📊 TESTS EXISTENTES QUE USAN API REAL

### 3. **tests/integration/test_conversation_api.py** 
- **ENDPOINTS PROBADOS**:
  ```python
  POST /conversations/start
  POST /conversations/{id}/message  
  GET /conversations/{id}
  DELETE /conversations/{id}
  ```
- **ESTADO**: Parcialmente funcional

### 4. **tests/integration/test_auth_api.py**
- **ENDPOINTS PROBADOS**:
  ```python
  POST /auth/register
  POST /auth/login
  POST /auth/refresh
  GET /auth/me
  ```
- **ESTADO**: Funcional si JWT está configurado

### 5. **tests/integration/test_analytics_api.py**
- **ENDPOINTS PROBADOS**:
  ```python
  GET /analytics/conversations/{id}
  GET /analytics/aggregate
  POST /analytics/export
  ```

### 6. **tests/integration/test_predictive_api.py**
- **ENDPOINTS PROBADOS**:
  ```python
  POST /predictive/objection
  POST /predictive/needs
  POST /predictive/conversion
  ```

## 🚀 TESTS DE CARGA Y RENDIMIENTO

### 7. **tests/performance/test_load.py**
- **QUÉ HACE**: Simula múltiples usuarios concurrentes
- **CONFIGURACIÓN**:
  ```python
  # 20, 50, 100+ usuarios simultáneos
  # Mide respuestas por segundo
  # Detecta errores bajo carga
  ```
- **RESULTADO ANTERIOR**: 447.2 requests/segundo con 0% error

### 8. **tests/performance/test_stress.py**
- **QUÉ HACE**: Prueba límites del sistema
- **PRUEBAS**:
  - Mensajes muy largos
  - Ráfagas de requests
  - Conexiones simultáneas

## 🔒 TESTS DE SEGURIDAD

### 9. **tests/security/test_auth_security.py**
- **PRUEBAS**:
  - SQL injection
  - XSS attempts
  - JWT manipulation
  - Rate limiting

### 10. **tests/security/penetration_test.py**
- **PRUEBAS**:
  - OWASP Top 10
  - Authentication bypass
  - Data exposure

## 🎯 CÓMO EJECUTAR LOS TESTS

```bash
# 1. Asegurarse que la API esté corriendo
export $(cat .env | grep -v '^#' | xargs)
python run.py

# 2. Tests de inteligencia (NUEVOS)
python tests/intelligence/test_conversation_quality.py
python tests/intelligence/test_product_knowledge.py

# 3. Tests de integración
pytest tests/integration/

# 4. Tests de carga
python tests/performance/test_load.py

# 5. Todos los tests
./run_tests.sh all
```

## ❌ POR QUÉ FALLAN ALGUNOS TESTS

### ERRORES ACTUALES:

1. **Error 500 "fromisoformat: argument must be str"**
   - Ocurre al procesar mensajes
   - Problema de serialización de fechas

2. **Métodos faltantes en servicios**:
   ```python
   # ESTOS MÉTODOS NO EXISTEN:
   EmpathyEngineService.generate_empathic_response()
   TierDetectionService.detect_tier()
   EmotionalIntelligenceService.analyze_emotional_state(message_text=...)
   AdaptivePersonalityService.analyze_personality(text=...)
   ```

3. **Incompatibilidad de interfaces**:
   - Los servicios esperan diferentes parámetros
   - MockAgentWrapper recibe argumentos incorrectos

## ✅ QUÉ SÍ FUNCIONA

1. **Crear conversaciones** ✅
2. **Guardar en Supabase** ✅
3. **Recuperar conversaciones** ✅
4. **Autenticación JWT** ✅
5. **Rate limiting** ✅
6. **Estructura base de la API** ✅

## 🔧 PLAN DE CORRECCIÓN

### OPCIÓN A: Arreglar los servicios (Recomendado)
1. Implementar los métodos faltantes
2. Ajustar interfaces para que coincidan
3. Corregir serialización de fechas
4. Verificar que todos los servicios estén inicializados

### OPCIÓN B: Modo degradado (Rápido)
1. Deshabilitar servicios problemáticos temporalmente
2. Usar respuestas fallback
3. Enfocarse en funcionalidad core

## 📈 MÉTRICAS OBJETIVO

Para considerar el sistema LISTO para BETA:

1. **Test de calidad**: >= 9.0/10 en todas las categorías
2. **Test de conocimiento**: >= 95% precisión
3. **Carga**: 500+ usuarios concurrentes sin errores
4. **Seguridad**: 0 vulnerabilidades críticas
5. **Disponibilidad**: 99.9% uptime

## 🚨 ESTADO ACTUAL: NO LISTO PARA BETA

**Razón principal**: Los errores 500 impiden que el agente responda correctamente a los mensajes.

**Siguiente paso**: Ejecutar el plan de corrección para arreglar los servicios problemáticos.