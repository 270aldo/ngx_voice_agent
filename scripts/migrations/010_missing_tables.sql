-- =====================================================================
-- MIGRACIÓN 010: TABLAS FALTANTES
-- =====================================================================
-- Este script crea las tablas que faltan en Supabase:
-- - conversation_sessions
-- - ab_test_experiments

-- Habilitar extensión para UUID si no existe
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================================
-- TABLA: conversation_sessions
-- =====================================================================
-- Registra las sesiones de conversación para tracking y analytics

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    conversation_id UUID NOT NULL,
    customer_id VARCHAR(255),
    platform_source VARCHAR(50) DEFAULT 'web',
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices para conversation_sessions
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_conversation_id 
ON conversation_sessions(conversation_id);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_customer_id 
ON conversation_sessions(customer_id);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_status 
ON conversation_sessions(status);

-- =====================================================================
-- TABLA: ab_test_experiments
-- =====================================================================
-- Gestiona los experimentos A/B para optimización continua

CREATE TABLE IF NOT EXISTS ab_test_experiments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    experiment_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    hypothesis TEXT,
    variants JSONB NOT NULL DEFAULT '[]',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    target_metric VARCHAR(100),
    success_criteria JSONB,
    allocation_percentages JSONB DEFAULT '{}',
    results JSONB DEFAULT '{}',
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices para ab_test_experiments
CREATE INDEX IF NOT EXISTS idx_ab_test_experiments_experiment_id 
ON ab_test_experiments(experiment_id);

CREATE INDEX IF NOT EXISTS idx_ab_test_experiments_is_active 
ON ab_test_experiments(is_active);

CREATE INDEX IF NOT EXISTS idx_ab_test_experiments_dates 
ON ab_test_experiments(start_date, end_date);

-- =====================================================================
-- TRIGGERS PARA UPDATED_AT
-- =====================================================================

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para conversation_sessions
DROP TRIGGER IF EXISTS update_conversation_sessions_updated_at ON conversation_sessions;
CREATE TRIGGER update_conversation_sessions_updated_at 
BEFORE UPDATE ON conversation_sessions 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger para ab_test_experiments
DROP TRIGGER IF EXISTS update_ab_test_experiments_updated_at ON ab_test_experiments;
CREATE TRIGGER update_ab_test_experiments_updated_at 
BEFORE UPDATE ON ab_test_experiments 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================================
-- COMENTARIOS DE TABLA
-- =====================================================================

COMMENT ON TABLE conversation_sessions IS 'Registra las sesiones de conversación para tracking, analytics y cooldown management';
COMMENT ON TABLE ab_test_experiments IS 'Gestiona experimentos A/B para optimización continua del sistema';

-- =====================================================================
-- PERMISOS (ajustar según necesidades)
-- =====================================================================

-- Dar permisos de lectura/escritura al rol de servicio
GRANT ALL ON conversation_sessions TO service_role;
GRANT ALL ON ab_test_experiments TO service_role;

-- Dar permisos de lectura al rol anónimo (si es necesario)
GRANT SELECT ON conversation_sessions TO anon;
GRANT SELECT ON ab_test_experiments TO anon;