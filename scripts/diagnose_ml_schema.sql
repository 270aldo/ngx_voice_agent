-- =====================================================================
-- SCRIPT DE DIAGNÓSTICO PARA ESQUEMA ML
-- =====================================================================
-- Este script ayuda a identificar problemas con las tablas ML

-- 1. Verificar qué tablas existen
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'ml_experiments',
    'experiment_results',
    'ab_test_variants',
    'ab_test_results',
    'pattern_recognitions',
    'ml_tracking_events',
    'conversation_outcomes',
    'predictive_models'
)
ORDER BY table_name;

-- 2. Verificar columnas de ab_test_variants
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'ab_test_variants'
ORDER BY ordinal_position;

-- 3. Verificar columnas de ab_test_results
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'ab_test_results'
ORDER BY ordinal_position;

-- 4. Verificar columnas de experiment_results
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'experiment_results'
ORDER BY ordinal_position;

-- 5. Buscar constraints con variant_id
SELECT 
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public'
AND kcu.column_name = 'variant_id';

-- 6. Buscar índices con variant_id
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND indexdef LIKE '%variant_id%';

-- 7. Buscar triggers problemáticos
SELECT 
    trigger_name,
    event_object_table,
    action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
AND trigger_name LIKE '%updated_at%';

-- 8. Verificar vistas que usan variant_id
SELECT 
    table_name as view_name,
    view_definition
FROM information_schema.views
WHERE table_schema = 'public'
AND view_definition LIKE '%variant_id%';