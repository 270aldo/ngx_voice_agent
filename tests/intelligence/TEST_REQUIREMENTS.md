# Requisitos para Tests de Inteligencia del Agente

## Verificaciones Realizadas

### 1. Estructura de Conversación
- **Endpoint Start**: POST `/conversations/start`
- **Datos requeridos**: 
  - name (sin números, solo letras)
  - email (válido)
  - age (18-120)
  - gender (opcional)
  - occupation (opcional)
  - goals (dict)
  - fitness_metrics (dict)
  - lifestyle (dict)

### 2. Endpoint de Mensajes
- **Endpoint**: POST `/conversations/{conversation_id}/message`
- **Request**: `{"message": "texto del usuario"}`
- **Response**: Incluye message con la respuesta del agente

### 3. Información de Productos NGX
- **PRIME**: $79-$199 mensual, target 25-50 años
- **LONGEVITY**: Para 50+ años
- **AGENTS ACCESS**: Tier básico
- **Hybrid Coaching**: Tier premium con humano + IA

### 4. HIE - 11 Agentes
El agente debe conocer y mencionar:
- NEXUS, BLAZE, SAGE, WAVE, SPARK, NOVA, LUNA, STELLA, CODE, GUARDIAN, NODE

### 5. OpenAI Client
- Ya existe wrapper con circuit breaker
- Podemos usar para evaluar calidad

## Tests a Crear

### 1. test_conversation_quality.py
**Verificará**:
- Calidad de respuestas usando GPT-4 como evaluador
- Conocimiento correcto de productos
- Técnicas de venta apropiadas
- Coherencia con brand voice

### 2. test_product_knowledge.py
**Verificará**:
- Precios correctos
- Diferencias entre PRIME/LONGEVITY
- Mención apropiada de HIE
- No inventar features

### 3. test_sales_effectiveness.py
**Verificará**:
- Intento de cierre
- Manejo de objeciones
- Creación de urgencia
- ROI mencionado

### 4. test_objection_handling.py
**Verificará**:
- Respuesta a "es muy caro"
- Respuesta a "no tengo tiempo"
- Respuesta a "necesito pensarlo"
- No ser agresivo

### 5. test_conversation_coherence.py
**Verificará**:
- Mantener contexto en 50+ mensajes
- No contradecirse
- Recordar información del cliente
- Progresión lógica de fases

### 6. test_edge_cases_nlp.py
**Verificará**:
- Cliente grosero
- Preguntas médicas
- Intentos de jailbreak
- Información contradictoria