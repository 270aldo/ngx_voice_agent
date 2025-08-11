-- =====================================================================
-- QUERY PERFORMANCE MONITORING SCRIPT
-- =====================================================================
-- This script helps identify slow queries and performance bottlenecks

-- Enable pg_stat_statements extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- =====================================================================
-- 1. FIND SLOW QUERIES
-- =====================================================================
-- Top 20 slowest queries by total time
SELECT 
    round(total_exec_time::numeric, 2) AS total_time_ms,
    round(mean_exec_time::numeric, 2) AS mean_time_ms,
    round(stddev_exec_time::numeric, 2) AS stddev_time_ms,
    calls,
    round(100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0), 2) AS cache_hit_percent,
    regexp_replace(query, '\s+', ' ', 'g')::varchar(500) AS query_text
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;

-- =====================================================================
-- 2. QUERIES WITH POOR CACHE HIT RATIO
-- =====================================================================
SELECT 
    round(100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0), 2) AS cache_hit_percent,
    calls,
    round(mean_exec_time::numeric, 2) AS mean_time_ms,
    regexp_replace(query, '\s+', ' ', 'g')::varchar(500) AS query_text
FROM pg_stat_statements
WHERE 
    shared_blks_hit + shared_blks_read > 0
    AND calls > 100
    AND query NOT LIKE '%pg_stat_statements%'
ORDER BY cache_hit_percent ASC
LIMIT 20;

-- =====================================================================
-- 3. MOST FREQUENTLY CALLED QUERIES
-- =====================================================================
SELECT 
    calls,
    round(mean_exec_time::numeric, 2) AS mean_time_ms,
    round(total_exec_time::numeric, 2) AS total_time_ms,
    regexp_replace(query, '\s+', ' ', 'g')::varchar(500) AS query_text
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY calls DESC
LIMIT 20;

-- =====================================================================
-- 4. CHECK INDEX USAGE
-- =====================================================================
-- Find tables with missing indexes (high sequential scans)
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    CASE 
        WHEN seq_scan + idx_scan = 0 THEN 0
        ELSE round(100.0 * idx_scan / (seq_scan + idx_scan), 2)
    END AS index_usage_percent
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;

-- =====================================================================
-- 5. UNUSED INDEXES
-- =====================================================================
-- Find indexes that are rarely or never used
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan < 50
ORDER BY pg_relation_size(indexrelid) DESC;

-- =====================================================================
-- 6. TABLE BLOAT CHECK
-- =====================================================================
-- Identify tables that need VACUUM
SELECT 
    schemaname,
    tablename,
    n_dead_tup,
    n_live_tup,
    round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_tuple_percent,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY dead_tuple_percent DESC;

-- =====================================================================
-- 7. LOCK MONITORING
-- =====================================================================
-- Check for blocking locks
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_query,
    blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- =====================================================================
-- 8. CONNECTION MONITORING
-- =====================================================================
-- Check connection usage
SELECT 
    count(*) AS total_connections,
    count(*) FILTER (WHERE state = 'active') AS active_connections,
    count(*) FILTER (WHERE state = 'idle') AS idle_connections,
    count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction,
    max(EXTRACT(epoch FROM (now() - query_start))::int) AS longest_query_seconds
FROM pg_stat_activity
WHERE datname = current_database();

-- =====================================================================
-- 9. QUERY PLAN CACHE STATISTICS
-- =====================================================================
-- Reset statistics (run periodically)
-- SELECT pg_stat_statements_reset();

-- =====================================================================
-- 10. RECOMMENDATIONS QUERY
-- =====================================================================
-- Generate index recommendations based on query patterns
WITH index_recommendations AS (
    SELECT 
        'CREATE INDEX idx_' || tablename || '_' || attname || ' ON ' || 
        schemaname || '.' || tablename || '(' || attname || ');' AS index_sql,
        schemaname,
        tablename,
        attname
    FROM (
        SELECT 
            n.nspname AS schemaname,
            c.relname AS tablename,
            a.attname,
            s.seq_scan,
            s.seq_tup_read
        FROM pg_stat_user_tables s
        JOIN pg_class c ON c.oid = s.relid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE 
            s.seq_scan > 1000
            AND s.seq_tup_read > 100000
            AND a.attnum > 0
            AND NOT a.attisdropped
            AND a.attname IN (
                -- Common columns that often need indexes
                'conversation_id', 'customer_phone', 'created_at', 
                'status', 'event_type', 'phone', 'user_id'
            )
    ) t
    WHERE NOT EXISTS (
        SELECT 1 
        FROM pg_index i
        JOIN pg_attribute ia ON ia.attrelid = i.indrelid AND ia.attnum = ANY(i.indkey)
        WHERE i.indrelid = (schemaname || '.' || tablename)::regclass
        AND ia.attname = t.attname
    )
)
SELECT * FROM index_recommendations;