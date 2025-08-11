-- =====================================================================
-- MIGRACIÓN 011: AGREGAR COLUMNA CONTEXT A CONVERSATIONS
-- =====================================================================
-- La columna 'context' es necesaria para guardar el contexto de la conversación

-- Agregar columna context si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'conversations' 
        AND column_name = 'context'
    ) THEN
        ALTER TABLE conversations 
        ADD COLUMN context JSONB DEFAULT '{}';
        
        COMMENT ON COLUMN conversations.context IS 'Contexto adicional de la conversación (metadata, configuraciones, etc)';
    END IF;
END $$;

-- Crear índice para búsquedas en context si no existe
CREATE INDEX IF NOT EXISTS idx_conversations_context 
ON conversations USING GIN (context);