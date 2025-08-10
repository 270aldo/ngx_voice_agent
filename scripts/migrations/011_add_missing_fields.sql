-- =====================================================================
-- MIGRACIÓN 011: AGREGAR CAMPOS FALTANTES A CONVERSATIONS
-- =====================================================================
-- Este script agrega los campos que el código está intentando guardar
-- pero que no existen en la tabla conversations

DO $$ 
BEGIN
    -- Agregar columna customer_name si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'customer_name') THEN
        ALTER TABLE conversations 
        ADD COLUMN customer_name VARCHAR(255);
    END IF;

    -- Agregar columna customer_email si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'customer_email') THEN
        ALTER TABLE conversations 
        ADD COLUMN customer_email VARCHAR(255);
    END IF;

    -- Agregar columna customer_phone si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'customer_phone') THEN
        ALTER TABLE conversations 
        ADD COLUMN customer_phone VARCHAR(50);
    END IF;

    -- Agregar columna customer_age si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'customer_age') THEN
        ALTER TABLE conversations 
        ADD COLUMN customer_age INTEGER;
    END IF;

    -- Agregar columna initial_message si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'initial_message') THEN
        ALTER TABLE conversations 
        ADD COLUMN initial_message TEXT;
    END IF;

    -- Agregar columna context si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'context') THEN
        ALTER TABLE conversations 
        ADD COLUMN context JSONB DEFAULT '{}';
    END IF;

    -- Agregar columna lead_score si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'lead_score') THEN
        ALTER TABLE conversations 
        ADD COLUMN lead_score FLOAT DEFAULT 0.0;
    END IF;

    -- Agregar columna intent si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'intent') THEN
        ALTER TABLE conversations 
        ADD COLUMN intent VARCHAR(100);
    END IF;

    -- Agregar columna human_transfer_needed si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'human_transfer_needed') THEN
        ALTER TABLE conversations 
        ADD COLUMN human_transfer_needed BOOLEAN DEFAULT FALSE;
    END IF;

    -- Agregar columna status si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' 
                   AND column_name = 'status') THEN
        ALTER TABLE conversations 
        ADD COLUMN status VARCHAR(50) DEFAULT 'active';
    END IF;
END $$;

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_conversations_customer_email ON conversations(customer_email);
CREATE INDEX IF NOT EXISTS idx_conversations_lead_score ON conversations(lead_score);
CREATE INDEX IF NOT EXISTS idx_conversations_intent ON conversations(intent);

-- Agregar comentarios para documentación
COMMENT ON COLUMN conversations.context IS 'Contexto adicional de la conversación (metadata, configuraciones, etc)';
COMMENT ON COLUMN conversations.customer_name IS 'Nombre del cliente';
COMMENT ON COLUMN conversations.customer_email IS 'Email del cliente';
COMMENT ON COLUMN conversations.customer_phone IS 'Teléfono del cliente';
COMMENT ON COLUMN conversations.customer_age IS 'Edad del cliente';
COMMENT ON COLUMN conversations.initial_message IS 'Mensaje inicial del cliente';
COMMENT ON COLUMN conversations.lead_score IS 'Puntuación del lead (0-100)';
COMMENT ON COLUMN conversations.intent IS 'Intención detectada del cliente';
COMMENT ON COLUMN conversations.human_transfer_needed IS 'Si se requiere transferencia a agente humano';
COMMENT ON COLUMN conversations.status IS 'Estado de la conversación (active, completed, abandoned)';