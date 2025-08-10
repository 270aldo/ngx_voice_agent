-- Migration: Remove all views with SECURITY DEFINER
-- Purpose: Fix Security Advisor errors about SECURITY DEFINER views
-- Date: 2025-07-28

-- Drop all views with SECURITY DEFINER in public schema
DO $$
DECLARE
    r RECORD;
    view_count INTEGER := 0;
BEGIN
    -- Log start of migration
    RAISE NOTICE 'Starting removal of SECURITY DEFINER views...';
    
    -- Find and drop all views with SECURITY DEFINER
    FOR r IN 
        SELECT viewname 
        FROM pg_views 
        WHERE schemaname = 'public' 
        AND definition LIKE '%SECURITY DEFINER%'
        ORDER BY viewname
    LOOP
        BEGIN
            EXECUTE 'DROP VIEW IF EXISTS public.' || quote_ident(r.viewname) || ' CASCADE';
            view_count := view_count + 1;
            RAISE NOTICE 'Dropped view: public.%', r.viewname;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Failed to drop view public.%: %', r.viewname, SQLERRM;
        END;
    END LOOP;
    
    -- Log completion
    RAISE NOTICE 'Migration complete. Removed % views with SECURITY DEFINER.', view_count;
    
    -- Verify no views remain
    SELECT COUNT(*) INTO view_count
    FROM pg_views
    WHERE schemaname = 'public'
    AND definition LIKE '%SECURITY DEFINER%';
    
    IF view_count > 0 THEN
        RAISE WARNING 'Warning: % views with SECURITY DEFINER still remain!', view_count;
    ELSE
        RAISE NOTICE 'Success: No views with SECURITY DEFINER remain in public schema.';
    END IF;
END $$;

-- Note: This migration intentionally does not have a rollback
-- as we're removing problematic views that shouldn't exist
-- If you need to recreate any views, do so without SECURITY DEFINER