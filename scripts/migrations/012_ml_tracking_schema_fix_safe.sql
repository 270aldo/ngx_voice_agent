-- =====================================================================
-- MIGRACIÓN 012: CORRECCIÓN DE ESQUEMA ML TRACKING (VERSIÓN SEGURA)
-- =====================================================================
-- Este script corrige y estandariza el esquema de las tablas ML para
-- asegurar la compatibilidad con el sistema de tracking.
-- VERSIÓN SEGURA: Verifica existencia antes de crear objetos
-- Fecha: 2025-07-28

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================================
-- 1. CORREGIR TABLA ml_experiments
-- =====================================================================
-- Agregar columnas faltantes si no existen
DO $$ 
BEGIN
    -- Agregar conversation_id si no existe (para relaciones)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ml_experiments' 
                   AND column_name = 'conversation_id') THEN
        ALTER TABLE ml_experiments 
        ADD COLUMN conversation_id UUID;
    END IF;

    -- Agregar user_id si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ml_experiments' 
                   AND column_name = 'user_id') THEN
        ALTER TABLE ml_experiments 
        ADD COLUMN user_id VARCHAR(255);
    END IF;

    -- Agregar is_active si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ml_experiments' 
                   AND column_name = 'is_active') THEN
        ALTER TABLE ml_experiments 
        ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;

    -- Agregar allocation_method si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ml_experiments' 
                   AND column_name = 'allocation_method') THEN
        ALTER TABLE ml_experiments 
        ADD COLUMN allocation_method VARCHAR(50) DEFAULT 'multi_armed_bandit';
    END IF;

    -- Agregar statistical_confidence si no existe
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ml_experiments' 
                   AND column_name = 'statistical_confidence') THEN
        ALTER TABLE ml_experiments 
        ADD COLUMN statistical_confidence FLOAT;
    END IF;
END $$;

-- =====================================================================
-- 2. CREAR TABLA experiment_results SI NO EXISTE
-- =====================================================================
CREATE TABLE IF NOT EXISTS experiment_results (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    experiment_id UUID NOT NULL,
    variant_id VARCHAR(100) NOT NULL,
    conversation_id UUID,
    user_id VARCHAR(255),
    
    -- Métricas del resultado
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    success BOOLEAN DEFAULT false,
    
    -- Contexto adicional
    context JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices para experiment_results (crear solo si no existen)
CREATE INDEX IF NOT EXISTS idx_experiment_results_experiment_id 
ON experiment_results(experiment_id);

CREATE INDEX IF NOT EXISTS idx_experiment_results_variant_id 
ON experiment_results(variant_id);

CREATE INDEX IF NOT EXISTS idx_experiment_results_conversation_id 
ON experiment_results(conversation_id);

CREATE INDEX IF NOT EXISTS idx_experiment_results_timestamp 
ON experiment_results(timestamp);

-- =====================================================================
-- 3. CREAR TABLA ab_test_variants SI NO EXISTE
-- =====================================================================
CREATE TABLE IF NOT EXISTS ab_test_variants (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    experiment_id UUID NOT NULL,
    variant_id VARCHAR(100) NOT NULL UNIQUE,
    variant_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Configuración de la variante
    variant_config JSONB NOT NULL DEFAULT '{}',
    content JSONB DEFAULT '{}',
    
    -- Control y estado
    is_control BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    allocation_percentage FLOAT DEFAULT 0.0,
    
    -- Estadísticas
    impressions INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    conversion_rate FLOAT DEFAULT 0.0,
    
    -- Multi-Armed Bandit
    arm_value FLOAT DEFAULT 1.0,
    arm_count INTEGER DEFAULT 0,
    ucb_score FLOAT DEFAULT 0.0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_allocation CHECK (allocation_percentage >= 0.0 AND allocation_percentage <= 1.0),
    CONSTRAINT valid_conversion_rate CHECK (conversion_rate >= 0.0 AND conversion_rate <= 1.0)
);

-- Índices para ab_test_variants
CREATE INDEX IF NOT EXISTS idx_ab_test_variants_experiment_id 
ON ab_test_variants(experiment_id);

CREATE INDEX IF NOT EXISTS idx_ab_test_variants_variant_id 
ON ab_test_variants(variant_id);

CREATE INDEX IF NOT EXISTS idx_ab_test_variants_active 
ON ab_test_variants(is_active) WHERE is_active = true;

-- =====================================================================
-- 4. CREAR TABLA ab_test_results SI NO EXISTE
-- =====================================================================
CREATE TABLE IF NOT EXISTS ab_test_results (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    experiment_id UUID NOT NULL,
    variant_id VARCHAR(100) NOT NULL,
    conversation_id UUID,
    
    -- Resultado del test
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    success BOOLEAN DEFAULT false,
    
    -- Contexto
    user_context JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para ab_test_results
CREATE INDEX IF NOT EXISTS idx_ab_test_results_experiment_id 
ON ab_test_results(experiment_id);

CREATE INDEX IF NOT EXISTS idx_ab_test_results_variant_id 
ON ab_test_results(variant_id);

CREATE INDEX IF NOT EXISTS idx_ab_test_results_timestamp 
ON ab_test_results(timestamp);

-- =====================================================================
-- 5. CREAR TABLA pattern_recognitions SI NO EXISTE
-- =====================================================================
CREATE TABLE IF NOT EXISTS pattern_recognitions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    pattern_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Datos del patrón
    pattern_data JSONB NOT NULL DEFAULT '{}',
    conditions JSONB NOT NULL DEFAULT '{}',
    
    -- Estadísticas
    occurrences INTEGER DEFAULT 1,
    confidence_score FLOAT DEFAULT 0.0,
    effectiveness_score FLOAT DEFAULT 0.0,
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    last_seen TIMESTAMP DEFAULT NOW(),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT valid_effectiveness CHECK (effectiveness_score >= 0.0 AND effectiveness_score <= 1.0)
);

-- Índices para pattern_recognitions
CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_type 
ON pattern_recognitions(pattern_type);

CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_active 
ON pattern_recognitions(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_confidence 
ON pattern_recognitions(confidence_score);

-- =====================================================================
-- 6. ACTUALIZAR TABLA conversation_outcomes
-- =====================================================================
DO $$ 
BEGIN
    -- Verificar si la tabla existe antes de agregar columnas
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_name = 'conversation_outcomes' 
               AND table_schema = 'public') THEN
        
        -- Agregar columnas ML tracking si no existen
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'conversation_outcomes' 
                       AND column_name = 'ml_predictions') THEN
            ALTER TABLE conversation_outcomes 
            ADD COLUMN ml_predictions JSONB DEFAULT '{}';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'conversation_outcomes' 
                       AND column_name = 'ml_confidence_scores') THEN
            ALTER TABLE conversation_outcomes 
            ADD COLUMN ml_confidence_scores JSONB DEFAULT '{}';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'conversation_outcomes' 
                       AND column_name = 'ab_test_assignments') THEN
            ALTER TABLE conversation_outcomes 
            ADD COLUMN ab_test_assignments JSONB DEFAULT '[]';
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'conversation_outcomes' 
                       AND column_name = 'pattern_matches') THEN
            ALTER TABLE conversation_outcomes 
            ADD COLUMN pattern_matches JSONB DEFAULT '[]';
        END IF;
    END IF;
END $$;

-- =====================================================================
-- 7. CREAR TABLA ml_tracking_events SI NO EXISTE
-- =====================================================================
CREATE TABLE IF NOT EXISTS ml_tracking_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    
    -- Referencias
    conversation_id UUID,
    experiment_id UUID,
    model_id UUID,
    
    -- Datos del evento
    event_data JSONB NOT NULL DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    
    -- Timestamp
    timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Metadata
    created_by VARCHAR(255) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para ml_tracking_events
CREATE INDEX IF NOT EXISTS idx_ml_tracking_events_type 
ON ml_tracking_events(event_type);

CREATE INDEX IF NOT EXISTS idx_ml_tracking_events_conversation 
ON ml_tracking_events(conversation_id);

CREATE INDEX IF NOT EXISTS idx_ml_tracking_events_timestamp 
ON ml_tracking_events(timestamp);

-- =====================================================================
-- 8. CREAR VISTAS ÚTILES
-- =====================================================================

-- Vista de experimentos activos con métricas
DROP VIEW IF EXISTS active_experiments_metrics;
CREATE VIEW active_experiments_metrics AS
SELECT 
    e.experiment_id,
    e.experiment_name,
    e.experiment_type,
    e.status,
    e.start_date,
    e.target_metric,
    COUNT(DISTINCT er.conversation_id) as total_conversions,
    AVG(er.metric_value) as avg_metric_value,
    e.statistical_confidence,
    e.winning_variant_id
FROM ml_experiments e
LEFT JOIN experiment_results er ON e.experiment_id = er.experiment_id
WHERE e.status IN ('running', 'analyzing')
GROUP BY e.experiment_id, e.experiment_name, e.experiment_type, 
         e.status, e.start_date, e.target_metric, 
         e.statistical_confidence, e.winning_variant_id;

-- Vista de performance de variantes A/B
DROP VIEW IF EXISTS ab_variant_performance;
CREATE VIEW ab_variant_performance AS
SELECT 
    v.experiment_id,
    v.variant_id,
    v.variant_name,
    v.is_control,
    v.impressions,
    v.conversions,
    v.conversion_rate,
    v.ucb_score,
    v.allocation_percentage,
    COUNT(r.id) as total_results,
    AVG(r.metric_value) as avg_metric_value
FROM ab_test_variants v
LEFT JOIN ab_test_results r ON v.variant_id = r.variant_id
WHERE v.is_active = true
GROUP BY v.experiment_id, v.variant_id, v.variant_name, 
         v.is_control, v.impressions, v.conversions, 
         v.conversion_rate, v.ucb_score, v.allocation_percentage;

-- Vista de patrones más efectivos
DROP VIEW IF EXISTS effective_patterns;
CREATE VIEW effective_patterns AS
SELECT 
    pattern_type,
    pattern_name,
    description,
    occurrences,
    confidence_score,
    effectiveness_score,
    last_seen
FROM pattern_recognitions
WHERE is_active = true
AND confidence_score > 0.7
ORDER BY effectiveness_score DESC, occurrences DESC;

-- =====================================================================
-- 9. FUNCIONES HELPER
-- =====================================================================

-- Función para actualizar UCB scores en variantes
CREATE OR REPLACE FUNCTION update_ucb_score(variant_id UUID)
RETURNS VOID AS $$
DECLARE
    total_impressions INTEGER;
    variant_impressions INTEGER;
    variant_conversion_rate FLOAT;
    exploration_factor FLOAT := 2.0;
BEGIN
    -- Obtener total de impresiones del experimento
    SELECT SUM(impressions) INTO total_impressions
    FROM ab_test_variants
    WHERE experiment_id = (
        SELECT experiment_id FROM ab_test_variants WHERE id = variant_id
    );
    
    -- Obtener datos de la variante
    SELECT impressions, conversion_rate 
    INTO variant_impressions, variant_conversion_rate
    FROM ab_test_variants WHERE id = variant_id;
    
    -- Calcular UCB score
    IF variant_impressions > 0 AND total_impressions > 0 THEN
        UPDATE ab_test_variants
        SET ucb_score = variant_conversion_rate + 
            SQRT(exploration_factor * LN(total_impressions) / variant_impressions)
        WHERE id = variant_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 10. TRIGGERS PARA ACTUALIZACIONES AUTOMÁTICAS
-- =====================================================================

-- Función para actualizar updated_at (crear solo si no existe)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar triggers solo si no existen
DO $$
BEGIN
    -- experiment_results
    IF NOT EXISTS (SELECT 1 FROM pg_trigger 
                   WHERE tgname = 'update_experiment_results_updated_at' 
                   AND tgrelid = 'experiment_results'::regclass) THEN
        CREATE TRIGGER update_experiment_results_updated_at
        BEFORE UPDATE ON experiment_results
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- ab_test_variants
    IF NOT EXISTS (SELECT 1 FROM pg_trigger 
                   WHERE tgname = 'update_ab_test_variants_updated_at'
                   AND tgrelid = 'ab_test_variants'::regclass) THEN
        CREATE TRIGGER update_ab_test_variants_updated_at
        BEFORE UPDATE ON ab_test_variants
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- pattern_recognitions
    IF NOT EXISTS (SELECT 1 FROM pg_trigger 
                   WHERE tgname = 'update_pattern_recognitions_updated_at'
                   AND tgrelid = 'pattern_recognitions'::regclass) THEN
        CREATE TRIGGER update_pattern_recognitions_updated_at
        BEFORE UPDATE ON pattern_recognitions
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- predictive_models (si existe la tabla)
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_name = 'predictive_models' 
               AND table_schema = 'public') THEN
        -- Eliminar trigger existente si existe
        DROP TRIGGER IF EXISTS update_predictive_models_updated_at_trigger ON predictive_models;
        
        -- Crear trigger con nombre correcto
        IF NOT EXISTS (SELECT 1 FROM pg_trigger 
                       WHERE tgname = 'update_predictive_models_updated_at'
                       AND tgrelid = 'predictive_models'::regclass) THEN
            CREATE TRIGGER update_predictive_models_updated_at
            BEFORE UPDATE ON predictive_models
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        END IF;
    END IF;
END $$;

-- =====================================================================
-- 11. PERMISOS
-- =====================================================================

-- Dar permisos necesarios (ajustar según roles existentes)
DO $$
BEGIN
    -- Intentar dar permisos solo si el rol existe
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
    END IF;
END $$;

-- =====================================================================
-- 12. COMENTARIOS PARA DOCUMENTACIÓN
-- =====================================================================

COMMENT ON TABLE ml_experiments IS 'Experimentos A/B y ML para optimización continua';
COMMENT ON TABLE experiment_results IS 'Resultados individuales de experimentos';
COMMENT ON TABLE ab_test_variants IS 'Variantes de pruebas A/B con Multi-Armed Bandit';
COMMENT ON TABLE ab_test_results IS 'Resultados de pruebas A/B por conversación';
COMMENT ON TABLE pattern_recognitions IS 'Patrones identificados por el sistema ML';
COMMENT ON TABLE ml_tracking_events IS 'Eventos de tracking para análisis ML';

-- =====================================================================
-- VERIFICACIÓN FINAL
-- =====================================================================
-- Query para verificar que todo está correcto
DO $$
DECLARE
    missing_count INTEGER := 0;
    table_name TEXT;
    required_tables TEXT[] := ARRAY[
        'ml_experiments',
        'experiment_results', 
        'conversation_outcomes',
        'ab_test_variants',
        'ab_test_results',
        'pattern_recognitions',
        'ml_tracking_events'
    ];
BEGIN
    FOREACH table_name IN ARRAY required_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = table_name
        ) THEN
            RAISE NOTICE 'Tabla faltante: %', table_name;
            missing_count := missing_count + 1;
        END IF;
    END LOOP;
    
    IF missing_count = 0 THEN
        RAISE NOTICE '✅ Todas las tablas ML están correctamente configuradas';
    ELSE
        RAISE WARNING '⚠️ Faltan % tablas ML', missing_count;
    END IF;
END $$;

-- =====================================================================
-- LIMPIEZA DE OBJETOS DUPLICADOS
-- =====================================================================
-- Eliminar triggers duplicados o con nombres incorrectos
DO $$
BEGIN
    -- Eliminar trigger con nombre incorrecto si existe
    DROP TRIGGER IF EXISTS update_predictive_models_updated_at_trigger ON predictive_models;
    
    -- Mensaje de confirmación
    RAISE NOTICE '✅ Migración 012 aplicada exitosamente (versión segura)';
END $$;

-- =====================================================================
-- Migración completada exitosamente
-- =====================================================================