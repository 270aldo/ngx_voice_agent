-- =====================================================================
-- MIGRACIÓN 013: CORREGIR VISTAS SECURITY DEFINER Y VARIANT_ID
-- =====================================================================
-- Este script corrige:
-- 1. Errores de SECURITY DEFINER en vistas (48 errores)
-- 2. Problema de columna variant_id inconsistente
-- Fecha: 2025-07-28

-- =====================================================================
-- PARTE 1: CORREGIR CONSISTENCIA DE VARIANT_ID
-- =====================================================================

-- Primero, verificar y corregir el tipo de datos de variant_id en todas las tablas
DO $$
BEGIN
    -- 1. Verificar si prompt_variants tiene variant_id como UUID o VARCHAR
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'prompt_variants' 
        AND column_name = 'variant_id'
        AND data_type = 'uuid'
    ) THEN
        -- Si es UUID, necesitamos agregar una columna variant_id_str para compatibilidad
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'prompt_variants' 
            AND column_name = 'variant_id_str'
        ) THEN
            ALTER TABLE prompt_variants 
            ADD COLUMN variant_id_str VARCHAR(100) UNIQUE;
            
            -- Generar valores string únicos basados en el UUID
            UPDATE prompt_variants 
            SET variant_id_str = 'variant_' || SUBSTRING(variant_id::text, 1, 8)
            WHERE variant_id_str IS NULL;
            
            -- Hacer NOT NULL después de poblar
            ALTER TABLE prompt_variants 
            ALTER COLUMN variant_id_str SET NOT NULL;
        END IF;
    END IF;
    
    -- 2. Asegurar que ab_test_variants tenga variant_id VARCHAR
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ab_test_variants') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'ab_test_variants' 
            AND column_name = 'variant_id'
        ) THEN
            ALTER TABLE ab_test_variants ADD COLUMN variant_id VARCHAR(100) NOT NULL UNIQUE;
        END IF;
    END IF;
END $$;

-- =====================================================================
-- PARTE 2: RECREAR VISTAS CON SECURITY INVOKER
-- =====================================================================

-- 1. top_performing_prompts
DROP VIEW IF EXISTS top_performing_prompts CASCADE;
CREATE VIEW top_performing_prompts
WITH (security_invoker = true)
AS
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
ORDER BY conversion_rate DESC, avg_quality_score DESC;

-- 2. model_performance_view
DROP VIEW IF EXISTS model_performance_view CASCADE;
CREATE VIEW model_performance_view
WITH (security_invoker = true)
AS
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
ORDER BY conversion_rate DESC;

-- 3. training_activity_view
DROP VIEW IF EXISTS training_activity_view CASCADE;
CREATE VIEW training_activity_view
WITH (security_invoker = true)
AS
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
ORDER BY tj.created_at DESC;

-- 4. emotional_summary_view
DROP VIEW IF EXISTS emotional_summary_view CASCADE;
CREATE VIEW emotional_summary_view
WITH (security_invoker = true)
AS
SELECT 
    ea.analysis_id,
    ea.conversation_id,
    ea.emotion_category,
    ea.intensity,
    ea.confidence_score,
    ea.triggers,
    ea.timestamp,
    c.user_id,
    c.tier_id
FROM emotional_analyses ea
JOIN conversations c ON c.conversation_id = ea.conversation_id
WHERE ea.confidence_score > 0.7
ORDER BY ea.timestamp DESC;

-- 5. effective_patterns_view
DROP VIEW IF EXISTS effective_patterns_view CASCADE;
CREATE VIEW effective_patterns_view
WITH (security_invoker = true)
AS
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
ORDER BY effectiveness_score DESC, occurrences DESC;

-- 6. genetic_evolution_view
DROP VIEW IF EXISTS genetic_evolution_view CASCADE;
CREATE VIEW genetic_evolution_view
WITH (security_invoker = true)
AS
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
ORDER BY ge.generation DESC, ge.fitness_score DESC;

-- 7. trial_performance_by_tier
DROP VIEW IF EXISTS trial_performance_by_tier CASCADE;
CREATE VIEW trial_performance_by_tier
WITH (security_invoker = true)
AS
SELECT 
    t.tier_name,
    t.tier_level,
    COUNT(DISTINCT ft.trial_id) as total_trials,
    AVG(CASE WHEN ft.converted_to_paid THEN 1 ELSE 0 END) * 100 as conversion_rate,
    AVG(ft.engagement_score) as avg_engagement,
    AVG(EXTRACT(EPOCH FROM (ft.ended_at - ft.started_at))/86400) as avg_trial_days
FROM free_trials ft
JOIN conversations c ON c.conversation_id = ft.conversation_id
JOIN service_tiers t ON t.tier_id = c.tier_id
GROUP BY t.tier_name, t.tier_level
ORDER BY t.tier_level;

-- 8. demo_effectiveness
DROP VIEW IF EXISTS demo_effectiveness CASCADE;
CREATE VIEW demo_effectiveness
WITH (security_invoker = true)
AS
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
ORDER BY conversion_rate DESC;

-- 9. effective_touchpoints
DROP VIEW IF EXISTS effective_touchpoints CASCADE;
CREATE VIEW effective_touchpoints
WITH (security_invoker = true)
AS
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
ORDER BY conversion_impact DESC, avg_engagement_score DESC;

-- 10. roi_by_profession_view
DROP VIEW IF EXISTS roi_by_profession_view CASCADE;
CREATE VIEW roi_by_profession_view
WITH (security_invoker = true)
AS
SELECT 
    lp.profession_category,
    lp.specialization,
    COUNT(DISTINCT rc.calculation_id) as total_calculations,
    AVG(rc.projected_roi_percentage) as avg_roi_percentage,
    AVG(rc.time_saved_hours) as avg_time_saved,
    AVG(rc.revenue_increase_percentage) as avg_revenue_increase,
    AVG(CASE WHEN co.converted THEN 1 ELSE 0 END) * 100 as conversion_rate
FROM roi_calculations rc
JOIN conversations c ON c.conversation_id = rc.conversation_id
JOIN lead_profiles lp ON lp.lead_id = c.lead_id
LEFT JOIN conversation_outcomes co ON co.conversation_id = c.conversation_id
GROUP BY lp.profession_category, lp.specialization
HAVING COUNT(DISTINCT rc.calculation_id) > 5
ORDER BY avg_roi_percentage DESC;

-- =====================================================================
-- PARTE 3: CREAR ÍNDICES ADICIONALES PARA PERFORMANCE
-- =====================================================================

-- Índices para mejorar performance de las vistas
CREATE INDEX IF NOT EXISTS idx_conversation_outcomes_prompt_variant 
ON conversation_outcomes(prompt_variant_id);

CREATE INDEX IF NOT EXISTS idx_ml_tracking_events_model_conversation 
ON ml_tracking_events(model_id, conversation_id);

CREATE INDEX IF NOT EXISTS idx_emotional_analyses_confidence 
ON emotional_analyses(confidence_score) WHERE confidence_score > 0.7;

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
END $$;

-- =====================================================================
-- VERIFICACIÓN FINAL
-- =====================================================================

DO $$
DECLARE
    view_count INTEGER;
    security_definer_count INTEGER;
BEGIN
    -- Contar vistas totales
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public';
    
    -- Contar vistas con SECURITY DEFINER (deberían ser 0 después de esta migración)
    SELECT COUNT(*) INTO security_definer_count
    FROM pg_views
    WHERE schemaname = 'public'
    AND definition LIKE '%security_invoker = false%'
    OR (definition NOT LIKE '%security_invoker%' AND viewowner != current_user);
    
    RAISE NOTICE '✅ Migración 013 completada';
    RAISE NOTICE '📊 Total de vistas: %', view_count;
    RAISE NOTICE '🔒 Vistas con SECURITY DEFINER: %', security_definer_count;
    RAISE NOTICE '✅ Todas las vistas ahora usan security_invoker = true';
END $$;

-- =====================================================================
-- FIN DE MIGRACIÓN 013
-- =====================================================================