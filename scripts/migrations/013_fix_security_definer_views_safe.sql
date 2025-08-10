-- =====================================================================
-- MIGRACIÓN 013 VERSIÓN SEGURA: CORREGIR VISTAS SECURITY DEFINER
-- =====================================================================
-- Esta versión es más robusta y maneja casos donde las tablas pueden no existir
-- Fecha: 2025-07-28

-- =====================================================================
-- PARTE 1: CREAR TABLAS BASE SI NO EXISTEN
-- =====================================================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Asegurar que conversation_outcomes existe
CREATE TABLE IF NOT EXISTS conversation_outcomes (
    outcome_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    client_archetype VARCHAR(100),
    client_demographic_data JSONB DEFAULT '{}',
    initial_intent VARCHAR(255),
    strategies_used JSONB DEFAULT '[]',
    prompts_used JSONB DEFAULT '[]',
    experiment_assignments JSONB DEFAULT '[]',
    outcome VARCHAR(50) NOT NULL,
    total_duration_seconds INTEGER,
    user_messages_count INTEGER,
    agent_messages_count INTEGER,
    average_response_time_seconds FLOAT,
    engagement_score FLOAT CHECK (engagement_score >= 0.0 AND engagement_score <= 10.0),
    satisfaction_score FLOAT CHECK (satisfaction_score IS NULL OR (satisfaction_score >= 0.0 AND satisfaction_score <= 10.0)),
    emotional_journey_stability FLOAT CHECK (emotional_journey_stability >= 0.0 AND emotional_journey_stability <= 1.0),
    conversion_probability FLOAT CHECK (conversion_probability >= 0.0 AND conversion_probability <= 1.0),
    tier_recommended VARCHAR(50),
    final_tier_accepted VARCHAR(50),
    objections_count INTEGER DEFAULT 0,
    objections_resolved_count INTEGER DEFAULT 0,
    questions_asked_by_user INTEGER DEFAULT 0,
    early_adopter_presented BOOLEAN DEFAULT false,
    early_adopter_accepted BOOLEAN DEFAULT false,
    hie_explanation_effectiveness FLOAT CHECK (hie_explanation_effectiveness >= 0.0 AND hie_explanation_effectiveness <= 1.0),
    success_factors JSONB DEFAULT '[]',
    failure_factors JSONB DEFAULT '[]',
    learning_insights JSONB DEFAULT '{}',
    recorded_at TIMESTAMP DEFAULT NOW(),
    agent_version VARCHAR(50) DEFAULT 'ngx_v1.0'
);

-- 2. Agregar columnas necesarias a conversation_outcomes
DO $$
BEGIN
    -- Agregar prompt_variant_id si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_outcomes' 
        AND column_name = 'prompt_variant_id'
    ) THEN
        ALTER TABLE conversation_outcomes 
        ADD COLUMN prompt_variant_id UUID;
    END IF;
    
    -- Agregar converted si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_outcomes' 
        AND column_name = 'converted'
    ) THEN
        ALTER TABLE conversation_outcomes 
        ADD COLUMN converted BOOLEAN DEFAULT false;
        
        -- Actualizar basándose en outcome
        UPDATE conversation_outcomes 
        SET converted = (outcome = 'converted')
        WHERE converted IS NULL;
    END IF;
    
    -- Agregar quality_score si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_outcomes' 
        AND column_name = 'quality_score'
    ) THEN
        ALTER TABLE conversation_outcomes 
        ADD COLUMN quality_score FLOAT DEFAULT 5.0 CHECK (quality_score >= 0.0 AND quality_score <= 10.0);
        
        -- Calcular quality_score inicial
        UPDATE conversation_outcomes 
        SET quality_score = LEAST(
            COALESCE(engagement_score, 5.0) * 0.4 + 
            COALESCE(satisfaction_score, 5.0) * 0.3 + 
            COALESCE(conversion_probability * 10, 5.0) * 0.3,
            10.0
        )
        WHERE quality_score = 5.0;
    END IF;
END $$;

-- 3. Crear tablas stub para vistas que las necesitan
CREATE TABLE IF NOT EXISTS prompt_variants (
    variant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_template TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictive_models (
    model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    is_active BOOLEAN DEFAULT true,
    last_trained TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    training_metrics JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emotional_analyses (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    emotion_category VARCHAR(100),
    intensity FLOAT,
    confidence_score FLOAT DEFAULT 0.0,
    triggers JSONB DEFAULT '[]',
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pattern_recognitions (
    pattern_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_type VARCHAR(100) NOT NULL,
    pattern_name VARCHAR(255) NOT NULL,
    description TEXT,
    pattern_data JSONB DEFAULT '{}',
    conditions JSONB DEFAULT '{}',
    occurrences INTEGER DEFAULT 1,
    confidence_score FLOAT DEFAULT 0.0,
    effectiveness_score FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT true,
    last_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS genetic_evolutions (
    evolution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generation INTEGER DEFAULT 1,
    parent_genome_id UUID,
    genome_data JSONB DEFAULT '{}',
    fitness_score FLOAT DEFAULT 0.0,
    mutation_rate FLOAT DEFAULT 0.01,
    crossover_points JSONB DEFAULT '[]',
    survived BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS free_trials (
    trial_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    converted_to_paid BOOLEAN DEFAULT false,
    engagement_score FLOAT DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS demos (
    demo_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    demo_type VARCHAR(100),
    feature_showcased VARCHAR(255),
    engagement_score FLOAT DEFAULT 0.0,
    completion_rate FLOAT DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS engagement_touchpoints (
    engagement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    touchpoint_type VARCHAR(100),
    touchpoint_name VARCHAR(255),
    engagement_score FLOAT DEFAULT 0.0,
    channel VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS roi_calculations (
    calculation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    projected_roi_percentage FLOAT DEFAULT 0.0,
    time_saved_hours FLOAT DEFAULT 0.0,
    revenue_increase_percentage FLOAT DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS ml_tracking_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    conversation_id UUID,
    experiment_id UUID,
    model_id UUID,
    event_data JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================================
-- PARTE 2: RECREAR VISTAS CON SECURITY INVOKER
-- =====================================================================

-- Función helper para crear vistas de forma segura
CREATE OR REPLACE FUNCTION create_view_safe(view_name TEXT, view_definition TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('DROP VIEW IF EXISTS %I CASCADE', view_name);
    EXECUTE format('CREATE VIEW %I WITH (security_invoker = true) AS %s', view_name, view_definition);
    RAISE NOTICE 'Vista % creada exitosamente', view_name;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Error creando vista %: %', view_name, SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- 1. top_performing_prompts
SELECT create_view_safe('top_performing_prompts', $VIEW$
    SELECT 
        pv.variant_id::text as variant_id,
        pv.prompt_template,
        pv.is_active,
        COUNT(DISTINCT co.conversation_id) as total_conversations,
        AVG(CASE WHEN co.converted THEN 1 ELSE 0 END) * 100 as conversion_rate,
        AVG(co.quality_score) as avg_quality_score,
        pv.created_at,
        pv.updated_at
    FROM prompt_variants pv
    LEFT JOIN conversation_outcomes co ON co.prompt_variant_id = pv.variant_id
    WHERE pv.is_active = true
    GROUP BY pv.variant_id, pv.prompt_template, pv.is_active, pv.created_at, pv.updated_at
    HAVING COUNT(DISTINCT co.conversation_id) > 5
    ORDER BY conversion_rate DESC, avg_quality_score DESC
$VIEW$);

-- 2. model_performance_view
SELECT create_view_safe('model_performance_view', $VIEW$
    SELECT 
        pm.model_id,
        pm.model_name,
        pm.model_type,
        pm.version,
        pm.is_active,
        COUNT(DISTINCT co.conversation_id) as total_predictions,
        AVG(co.quality_score) as avg_quality_score,
        AVG(CASE WHEN co.converted THEN 1 ELSE 0 END) * 100 as conversion_rate,
        pm.last_trained,
        pm.created_at
    FROM predictive_models pm
    LEFT JOIN conversation_outcomes co ON co.conversation_id IN (
        SELECT conversation_id FROM ml_tracking_events WHERE model_id = pm.model_id
    )
    WHERE pm.is_active = true
    GROUP BY pm.model_id, pm.model_name, pm.model_type, pm.version, 
             pm.is_active, pm.last_trained, pm.created_at
    ORDER BY conversion_rate DESC
$VIEW$);

-- 3. training_activity_view
SELECT create_view_safe('training_activity_view', $VIEW$
    SELECT 
        tj.job_id,
        tj.model_type,
        tj.status,
        tj.started_at,
        tj.completed_at,
        tj.training_metrics,
        tj.error_message,
        EXTRACT(EPOCH FROM (tj.completed_at - tj.started_at)) as duration_seconds,
        tj.created_at
    FROM training_jobs tj
    ORDER BY tj.created_at DESC
$VIEW$);

-- 4. emotional_summary_view
SELECT create_view_safe('emotional_summary_view', $VIEW$
    SELECT 
        ea.analysis_id,
        ea.conversation_id,
        ea.emotion_category,
        ea.intensity,
        ea.confidence_score,
        ea.triggers,
        ea.timestamp,
        c.user_id,
        c.tier_detected as tier_id
    FROM emotional_analyses ea
    JOIN conversations c ON c.conversation_id = ea.conversation_id
    WHERE ea.confidence_score > 0.7
    ORDER BY ea.timestamp DESC
$VIEW$);

-- 5. effective_patterns_view
SELECT create_view_safe('effective_patterns_view', $VIEW$
    SELECT 
        pattern_type,
        pattern_name,
        description,
        occurrences,
        confidence_score,
        effectiveness_score,
        last_seen,
        pattern_data,
        conditions
    FROM pattern_recognitions
    WHERE is_active = true
    AND confidence_score > 0.7
    AND effectiveness_score > 0.6
    ORDER BY effectiveness_score DESC, occurrences DESC
$VIEW$);

-- 6. genetic_evolution_view
SELECT create_view_safe('genetic_evolution_view', $VIEW$
    SELECT 
        ge.evolution_id,
        ge.generation,
        ge.parent_genome_id,
        ge.genome_data,
        ge.fitness_score,
        ge.mutation_rate,
        ge.crossover_points,
        ge.survived,
        ge.created_at
    FROM genetic_evolutions ge
    WHERE ge.survived = true
    ORDER BY ge.generation DESC, ge.fitness_score DESC
$VIEW$);

-- 7. trial_performance_by_tier
SELECT create_view_safe('trial_performance_by_tier', $VIEW$
    SELECT 
        COALESCE(c.tier_detected, 'Unknown') as tier_name,
        CASE 
            WHEN c.tier_detected = 'PRIME' THEN 4
            WHEN c.tier_detected = 'ELITE' THEN 3
            WHEN c.tier_detected = 'PRO' THEN 2
            WHEN c.tier_detected = 'ESSENTIAL' THEN 1
            ELSE 0
        END as tier_level,
        COUNT(DISTINCT ft.trial_id) as total_trials,
        AVG(CASE WHEN ft.converted_to_paid THEN 1 ELSE 0 END) * 100 as conversion_rate,
        AVG(ft.engagement_score) as avg_engagement,
        AVG(EXTRACT(EPOCH FROM (ft.ended_at - ft.started_at))/86400) as avg_trial_days
    FROM free_trials ft
    JOIN conversations c ON c.conversation_id = ft.conversation_id
    GROUP BY c.tier_detected
    ORDER BY tier_level
$VIEW$);

-- 8. demo_effectiveness
SELECT create_view_safe('demo_effectiveness', $VIEW$
    SELECT 
        d.demo_id,
        d.demo_type,
        d.feature_showcased,
        COUNT(DISTINCT d.conversation_id) as total_demos,
        AVG(d.engagement_score) as avg_engagement,
        AVG(CASE WHEN co.converted THEN 1 ELSE 0 END) * 100 as conversion_rate,
        AVG(d.completion_rate) as avg_completion_rate
    FROM demos d
    LEFT JOIN conversation_outcomes co ON co.conversation_id = d.conversation_id
    GROUP BY d.demo_id, d.demo_type, d.feature_showcased
    HAVING COUNT(DISTINCT d.conversation_id) > 3
    ORDER BY conversion_rate DESC
$VIEW$);

-- 9. effective_touchpoints
SELECT create_view_safe('effective_touchpoints', $VIEW$
    SELECT 
        et.touchpoint_type,
        et.touchpoint_name,
        COUNT(DISTINCT et.engagement_id) as total_engagements,
        AVG(et.engagement_score) as avg_engagement_score,
        AVG(CASE WHEN co.converted THEN 1 ELSE 0 END) * 100 as conversion_impact,
        et.channel
    FROM engagement_touchpoints et
    LEFT JOIN conversation_outcomes co ON co.conversation_id = et.conversation_id
    GROUP BY et.touchpoint_type, et.touchpoint_name, et.channel
    HAVING COUNT(DISTINCT et.engagement_id) > 10
    ORDER BY conversion_impact DESC, avg_engagement_score DESC
$VIEW$);

-- 10. roi_by_profession_view
SELECT create_view_safe('roi_by_profession_view', $VIEW$
    SELECT 
        'General' as profession_category,
        'All' as specialization,
        COUNT(DISTINCT rc.calculation_id) as total_calculations,
        AVG(rc.projected_roi_percentage) as avg_roi_percentage,
        AVG(rc.time_saved_hours) as avg_time_saved,
        AVG(rc.revenue_increase_percentage) as avg_revenue_increase,
        AVG(CASE WHEN co.converted THEN 1 ELSE 0 END) * 100 as conversion_rate
    FROM roi_calculations rc
    JOIN conversations c ON c.conversation_id = rc.conversation_id
    LEFT JOIN conversation_outcomes co ON co.conversation_id = c.conversation_id
    GROUP BY profession_category, specialization
    HAVING COUNT(DISTINCT rc.calculation_id) > 5
    ORDER BY avg_roi_percentage DESC
$VIEW$);

-- Limpiar función helper
DROP FUNCTION IF EXISTS create_view_safe(TEXT, TEXT);

-- =====================================================================
-- PARTE 3: CREAR ÍNDICES PARA PERFORMANCE
-- =====================================================================

-- Índices para conversation_outcomes
CREATE INDEX IF NOT EXISTS idx_conversation_outcomes_conversation_id 
ON conversation_outcomes(conversation_id);

CREATE INDEX IF NOT EXISTS idx_conversation_outcomes_prompt_variant 
ON conversation_outcomes(prompt_variant_id);

CREATE INDEX IF NOT EXISTS idx_conversation_outcomes_converted 
ON conversation_outcomes(converted);

CREATE INDEX IF NOT EXISTS idx_conversation_outcomes_quality 
ON conversation_outcomes(quality_score);

CREATE INDEX IF NOT EXISTS idx_conversation_outcomes_outcome 
ON conversation_outcomes(outcome);

-- Índices para ml_tracking_events
CREATE INDEX IF NOT EXISTS idx_ml_tracking_events_model_conversation 
ON ml_tracking_events(model_id, conversation_id);

CREATE INDEX IF NOT EXISTS idx_ml_tracking_events_conversation 
ON ml_tracking_events(conversation_id);

-- Índices para emotional_analyses
CREATE INDEX IF NOT EXISTS idx_emotional_analyses_confidence 
ON emotional_analyses(confidence_score) WHERE confidence_score > 0.7;

CREATE INDEX IF NOT EXISTS idx_emotional_analyses_conversation 
ON emotional_analyses(conversation_id);

-- Índices para pattern_recognitions
CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_effectiveness 
ON pattern_recognitions(effectiveness_score) WHERE is_active = true;

-- =====================================================================
-- PARTE 4: GRANTS Y PERMISOS
-- =====================================================================

DO $$
BEGIN
    -- Asegurar que las vistas tengan los permisos correctos
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Error al asignar permisos: %', SQLERRM;
END $$;

-- =====================================================================
-- VERIFICACIÓN FINAL
-- =====================================================================

DO $$
DECLARE
    view_count INTEGER := 0;
    table_count INTEGER := 0;
    index_count INTEGER := 0;
BEGIN
    -- Contar vistas creadas
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public'
    AND view_name IN (
        'top_performing_prompts',
        'model_performance_view',
        'training_activity_view',
        'emotional_summary_view',
        'effective_patterns_view',
        'genetic_evolution_view',
        'trial_performance_by_tier',
        'demo_effectiveness',
        'effective_touchpoints',
        'roi_by_profession_view'
    );
    
    -- Contar tablas necesarias
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN (
        'conversation_outcomes',
        'prompt_variants',
        'predictive_models',
        'training_jobs',
        'emotional_analyses',
        'pattern_recognitions',
        'genetic_evolutions',
        'free_trials',
        'demos',
        'engagement_touchpoints',
        'roi_calculations',
        'ml_tracking_events'
    );
    
    -- Contar índices creados
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND indexname LIKE 'idx_%';
    
    RAISE NOTICE '✅ Migración 013 VERSIÓN SEGURA completada';
    RAISE NOTICE '📊 Vistas creadas: % de 10', view_count;
    RAISE NOTICE '📋 Tablas verificadas: % de 12', table_count;
    RAISE NOTICE '🔍 Índices totales: %', index_count;
    RAISE NOTICE '✅ Todas las vistas usan security_invoker = true';
    
    -- Advertencias específicas
    IF view_count < 10 THEN
        RAISE WARNING '⚠️ No todas las vistas se crearon exitosamente. Revisar logs anteriores.';
    END IF;
    
    IF table_count < 12 THEN
        RAISE WARNING '⚠️ Algunas tablas base no existen. Las vistas relacionadas pueden no funcionar.';
    END IF;
END $$;

-- =====================================================================
-- FIN DE MIGRACIÓN 013 VERSIÓN SEGURA
-- =====================================================================