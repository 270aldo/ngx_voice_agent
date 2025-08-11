-- =====================================================================
-- DIAGNÓSTICO: ESTADO DE TABLA conversation_outcomes
-- =====================================================================
-- Este script verifica el estado actual de la tabla conversation_outcomes
-- y sus columnas para determinar la mejor estrategia de migración

-- 1. Verificar si la tabla existe
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_outcomes')
        THEN '✅ La tabla conversation_outcomes EXISTE'
        ELSE '❌ La tabla conversation_outcomes NO EXISTE'
    END as tabla_status;

-- 2. Si existe, mostrar todas sus columnas
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'conversation_outcomes'
ORDER BY ordinal_position;

-- 3. Buscar columnas relacionadas con prompts
SELECT 
    column_name,
    data_type,
    '✅ ENCONTRADA' as status
FROM information_schema.columns
WHERE table_name = 'conversation_outcomes'
AND (
    column_name LIKE '%prompt%' 
    OR column_name LIKE '%variant%'
    OR data_type = 'jsonb'
);

-- 4. Verificar si prompt_variants existe y su estructura
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'prompt_variants')
        THEN '✅ La tabla prompt_variants EXISTE'
        ELSE '❌ La tabla prompt_variants NO EXISTE'
    END as prompt_variants_status;

-- 5. Si prompt_variants existe, mostrar estructura de variant_id
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prompt_variants'
AND column_name = 'variant_id';

-- 6. Verificar vistas que dependen de conversation_outcomes
SELECT 
    viewname,
    CASE 
        WHEN definition LIKE '%conversation_outcomes%' 
        THEN '⚠️ USA conversation_outcomes'
        ELSE '✅ NO usa conversation_outcomes'
    END as dependency_status
FROM pg_views
WHERE schemaname = 'public'
AND definition LIKE '%conversation_outcomes%';

-- 7. Contar registros en conversation_outcomes (si existe)
DO $$
DECLARE
    row_count BIGINT;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_outcomes') THEN
        EXECUTE 'SELECT COUNT(*) FROM conversation_outcomes' INTO row_count;
        RAISE NOTICE '📊 Registros en conversation_outcomes: %', row_count;
    ELSE
        RAISE NOTICE '❌ No se puede contar registros - tabla no existe';
    END IF;
END $$;

-- 8. Verificar contenido de columna prompts_used (si existe)
DO $$
DECLARE
    sample_data JSONB;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_outcomes' 
        AND column_name = 'prompts_used'
    ) THEN
        EXECUTE 'SELECT prompts_used FROM conversation_outcomes LIMIT 1' INTO sample_data;
        RAISE NOTICE '📋 Ejemplo de prompts_used: %', sample_data;
    END IF;
END $$;

-- 9. Resumen de hallazgos
SELECT 
    'RESUMEN DE DIAGNÓSTICO' as titulo,
    NOW() as fecha_diagnostico;

-- 10. Recomendaciones
SELECT 
    'RECOMENDACIONES' as titulo,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_outcomes')
        THEN 'La tabla existe. Verificar si necesita columna prompt_variant_id o usar prompts_used JSONB'
        ELSE 'Ejecutar script create_ml_learning_tables.sql primero'
    END as recomendacion;