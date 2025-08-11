-- =====================================================================
-- FIX PARA PROBLEMA DE variant_id
-- =====================================================================
-- Este script corrige el problema de la columna variant_id faltante

-- 1. Verificar si las tablas existen y qué columnas tienen
DO $$
BEGIN
    RAISE NOTICE '=== VERIFICANDO ESTADO DE TABLAS ===';
    
    -- Verificar ab_test_variants
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ab_test_variants') THEN
        RAISE NOTICE 'Tabla ab_test_variants existe';
        
        -- Verificar si tiene variant_id
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'ab_test_variants' 
                       AND column_name = 'variant_id') THEN
            RAISE NOTICE 'FALTA columna variant_id en ab_test_variants - agregando...';
            ALTER TABLE ab_test_variants ADD COLUMN variant_id VARCHAR(100);
            
            -- Si la tabla tiene datos, generar variant_ids únicos
            UPDATE ab_test_variants 
            SET variant_id = 'variant_' || id::text 
            WHERE variant_id IS NULL;
            
            -- Hacer la columna NOT NULL y UNIQUE
            ALTER TABLE ab_test_variants ALTER COLUMN variant_id SET NOT NULL;
            
            -- Agregar constraint único si no existe
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                          WHERE table_name = 'ab_test_variants' 
                          AND constraint_type = 'UNIQUE'
                          AND constraint_name = 'ab_test_variants_variant_id_key') THEN
                ALTER TABLE ab_test_variants ADD CONSTRAINT ab_test_variants_variant_id_key UNIQUE (variant_id);
            END IF;
        ELSE
            RAISE NOTICE 'Columna variant_id ya existe en ab_test_variants';
        END IF;
    ELSE
        RAISE NOTICE 'Tabla ab_test_variants NO existe - creándola...';
        
        -- Crear la tabla completa
        CREATE TABLE ab_test_variants (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            experiment_id UUID NOT NULL,
            variant_id VARCHAR(100) NOT NULL UNIQUE,
            variant_name VARCHAR(255) NOT NULL,
            description TEXT,
            variant_config JSONB NOT NULL DEFAULT '{}',
            content JSONB DEFAULT '{}',
            is_control BOOLEAN DEFAULT false,
            is_active BOOLEAN DEFAULT true,
            allocation_percentage FLOAT DEFAULT 0.0,
            impressions INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            conversion_rate FLOAT DEFAULT 0.0,
            arm_value FLOAT DEFAULT 1.0,
            arm_count INTEGER DEFAULT 0,
            ucb_score FLOAT DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT valid_allocation CHECK (allocation_percentage >= 0.0 AND allocation_percentage <= 1.0),
            CONSTRAINT valid_conversion_rate CHECK (conversion_rate >= 0.0 AND conversion_rate <= 1.0)
        );
    END IF;
    
    -- Verificar ab_test_results
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ab_test_results') THEN
        RAISE NOTICE 'Tabla ab_test_results existe';
        
        -- Verificar si tiene variant_id
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'ab_test_results' 
                       AND column_name = 'variant_id') THEN
            RAISE NOTICE 'FALTA columna variant_id en ab_test_results - agregando...';
            ALTER TABLE ab_test_results ADD COLUMN variant_id VARCHAR(100) NOT NULL DEFAULT 'unknown';
        ELSE
            RAISE NOTICE 'Columna variant_id ya existe en ab_test_results';
        END IF;
    ELSE
        RAISE NOTICE 'Tabla ab_test_results NO existe - creándola...';
        
        CREATE TABLE ab_test_results (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            experiment_id UUID NOT NULL,
            variant_id VARCHAR(100) NOT NULL,
            conversation_id UUID,
            metric_name VARCHAR(100) NOT NULL,
            metric_value FLOAT NOT NULL,
            success BOOLEAN DEFAULT false,
            user_context JSONB DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        );
    END IF;
    
    -- Verificar experiment_results
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'experiment_results') THEN
        RAISE NOTICE 'Tabla experiment_results existe';
        
        -- Verificar si tiene variant_id
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'experiment_results' 
                       AND column_name = 'variant_id') THEN
            RAISE NOTICE 'FALTA columna variant_id en experiment_results - agregando...';
            ALTER TABLE experiment_results ADD COLUMN variant_id VARCHAR(100) NOT NULL DEFAULT 'unknown';
        ELSE
            RAISE NOTICE 'Columna variant_id ya existe en experiment_results';
        END IF;
    ELSE
        RAISE NOTICE 'Tabla experiment_results NO existe - creándola...';
        
        CREATE TABLE experiment_results (
            id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
            experiment_id UUID NOT NULL,
            variant_id VARCHAR(100) NOT NULL,
            conversation_id UUID,
            user_id VARCHAR(255),
            metric_name VARCHAR(100) NOT NULL,
            metric_value FLOAT NOT NULL,
            success BOOLEAN DEFAULT false,
            context JSONB DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    END IF;
    
END $$;

-- 2. Recrear índices de forma segura
CREATE INDEX IF NOT EXISTS idx_ab_test_variants_variant_id 
ON ab_test_variants(variant_id);

CREATE INDEX IF NOT EXISTS idx_ab_test_results_variant_id 
ON ab_test_results(variant_id);

CREATE INDEX IF NOT EXISTS idx_experiment_results_variant_id 
ON experiment_results(variant_id);

-- 3. Recrear vistas que dependen de variant_id
-- Primero eliminar las vistas existentes
DROP VIEW IF EXISTS ab_variant_performance CASCADE;

-- Luego recrearlas
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

-- 4. Mensaje final
DO $$
BEGIN
    RAISE NOTICE '=== CORRECCIÓN COMPLETADA ===';
    RAISE NOTICE 'Por favor ejecuta el script de diagnóstico nuevamente para verificar';
END $$;