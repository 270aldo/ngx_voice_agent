-- =====================================================================
-- MIGRATION 014: PERFORMANCE INDEXES
-- =====================================================================
-- This migration adds comprehensive indexes to improve query performance
-- Based on common query patterns in the NGX Voice Sales Agent

-- Drop existing indexes if they exist to recreate with better configuration
DROP INDEX IF EXISTS idx_conversations_status;
DROP INDEX IF EXISTS idx_conversations_created_at;
DROP INDEX IF EXISTS idx_conversations_customer_phone;
DROP INDEX IF EXISTS idx_conversations_tier_detected;
DROP INDEX IF EXISTS idx_conversations_last_message_at;
DROP INDEX IF EXISTS idx_messages_conversation_id;
DROP INDEX IF EXISTS idx_messages_created_at;
DROP INDEX IF EXISTS idx_messages_role;
DROP INDEX IF EXISTS idx_conversation_outcomes_conversation_id;
DROP INDEX IF EXISTS idx_ml_tracking_events_conversation_id;
DROP INDEX IF EXISTS idx_ml_tracking_events_event_type;
DROP INDEX IF EXISTS idx_ml_training_data_feature_type;
DROP INDEX IF EXISTS idx_lead_scores_phone;
DROP INDEX IF EXISTS idx_objection_handling_conversation_id;
DROP INDEX IF EXISTS idx_ab_experiments_status;
DROP INDEX IF EXISTS idx_prompt_versions_is_active;

-- =====================================================================
-- CONVERSATIONS TABLE INDEXES
-- =====================================================================

-- Composite index for status queries with time filtering
CREATE INDEX idx_conversations_status_created 
ON conversations(status, created_at DESC) 
WHERE status IN ('active', 'in_progress', 'completed');

-- Index for customer lookup (phone is most common search)
CREATE INDEX idx_conversations_customer_phone 
ON conversations(customer_phone) 
WHERE customer_phone IS NOT NULL;

-- Index for tier-based queries
CREATE INDEX idx_conversations_tier_confidence 
ON conversations(tier_detected, tier_confidence DESC) 
WHERE tier_detected IS NOT NULL;

-- Index for recent activity queries
CREATE INDEX idx_conversations_last_message 
ON conversations(last_message_at DESC NULLS LAST, conversation_id);

-- Index for ML tracking enabled conversations
CREATE INDEX idx_conversations_ml_enabled 
ON conversations(conversation_id) 
WHERE ml_tracking_enabled = true;

-- Composite index for analytics queries
CREATE INDEX idx_conversations_analytics 
ON conversations(created_at DESC, status, outcome) 
INCLUDE (customer_name, tier_detected, lead_score);

-- =====================================================================
-- MESSAGES TABLE INDEXES
-- =====================================================================

-- Primary lookup index with created_at for ordering
CREATE INDEX idx_messages_conversation_lookup 
ON messages(conversation_id, created_at DESC);

-- Index for role-based queries (finding all user or assistant messages)
CREATE INDEX idx_messages_role_filter 
ON messages(role, created_at DESC) 
WHERE role IN ('user', 'assistant');

-- Full text search index on message content (if needed)
-- CREATE INDEX idx_messages_content_search ON messages USING gin(to_tsvector('english', content));

-- =====================================================================
-- CONVERSATION_OUTCOMES TABLE INDEXES
-- =====================================================================

-- Primary lookup and analytics
CREATE INDEX idx_outcomes_conversation_date 
ON conversation_outcomes(conversation_id, created_at DESC);

-- Index for outcome analytics
CREATE INDEX idx_outcomes_analytics 
ON conversation_outcomes(outcome_type, created_at DESC) 
INCLUDE (outcome_details);

-- =====================================================================
-- ML_TRACKING_EVENTS TABLE INDEXES
-- =====================================================================

-- Composite index for ML event queries
CREATE INDEX idx_ml_events_lookup 
ON ml_tracking_events(conversation_id, event_type, timestamp DESC);

-- Index for event type analytics
CREATE INDEX idx_ml_events_type_time 
ON ml_tracking_events(event_type, timestamp DESC) 
WHERE event_type IN ('message_exchange', 'pattern_detected', 'decision_made', 'outcome_recorded');

-- Index for pattern detection queries
CREATE INDEX idx_ml_events_patterns 
ON ml_tracking_events((event_data->>'pattern_type'), timestamp DESC) 
WHERE event_type = 'pattern_detected';

-- =====================================================================
-- ML_TRAINING_DATA TABLE INDEXES
-- =====================================================================

-- Index for feature type queries
CREATE INDEX idx_ml_training_feature_lookup 
ON ml_training_data(feature_type, created_at DESC);

-- Index for conversation-based training data
CREATE INDEX idx_ml_training_conversation 
ON ml_training_data(conversation_id, feature_type) 
WHERE conversation_id IS NOT NULL;

-- =====================================================================
-- LEAD_SCORES TABLE INDEXES
-- =====================================================================

-- Primary lookup by phone
CREATE INDEX idx_lead_scores_phone_lookup 
ON lead_scores(phone, score DESC);

-- Index for high-value leads
CREATE INDEX idx_lead_scores_high_value 
ON lead_scores(score DESC, last_updated DESC) 
WHERE score >= 70;

-- =====================================================================
-- OBJECTION_HANDLING TABLE INDEXES
-- =====================================================================

-- Lookup by conversation
CREATE INDEX idx_objections_conversation 
ON objection_handling(conversation_id, created_at DESC);

-- Analytics by objection type
CREATE INDEX idx_objections_type_success 
ON objection_handling(objection_type, handled_successfully, created_at DESC);

-- =====================================================================
-- AB_EXPERIMENTS TABLE INDEXES
-- =====================================================================

-- Active experiments lookup
CREATE INDEX idx_experiments_active 
ON ab_experiments(status, created_at DESC) 
WHERE status = 'active';

-- Experiment results analysis
CREATE INDEX idx_experiments_completion 
ON ab_experiments(experiment_type, ended_at DESC) 
WHERE status = 'completed' AND ended_at IS NOT NULL;

-- =====================================================================
-- PROMPT_VERSIONS TABLE INDEXES
-- =====================================================================

-- Active prompts lookup
CREATE INDEX idx_prompts_active 
ON prompt_versions(prompt_key, version DESC) 
WHERE is_active = true;

-- Performance tracking
CREATE INDEX idx_prompts_performance 
ON prompt_versions(prompt_key, performance_score DESC) 
WHERE performance_score IS NOT NULL;

-- =====================================================================
-- CONVERSATION_TRANSCRIPTS TABLE INDEXES
-- =====================================================================

-- If transcripts table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_transcripts') THEN
        -- Primary lookup
        CREATE INDEX IF NOT EXISTS idx_transcripts_conversation 
        ON conversation_transcripts(conversation_id, created_at DESC);
        
        -- Status-based queries
        CREATE INDEX IF NOT EXISTS idx_transcripts_status 
        ON conversation_transcripts(status, created_at DESC) 
        WHERE status IN ('pending', 'processing', 'completed');
    END IF;
END $$;

-- =====================================================================
-- SECURITY_AUDIT_LOGS TABLE INDEXES (if exists)
-- =====================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'security_audit_logs') THEN
        -- Time-based security queries
        CREATE INDEX IF NOT EXISTS idx_security_logs_time 
        ON security_audit_logs(created_at DESC, event_type);
        
        -- User activity tracking
        CREATE INDEX IF NOT EXISTS idx_security_logs_user 
        ON security_audit_logs(user_id, created_at DESC) 
        WHERE user_id IS NOT NULL;
        
        -- Security event analysis
        CREATE INDEX IF NOT EXISTS idx_security_logs_severity 
        ON security_audit_logs(severity, created_at DESC) 
        WHERE severity IN ('high', 'critical');
    END IF;
END $$;

-- =====================================================================
-- PARTIAL INDEXES FOR COMMON QUERIES
-- =====================================================================

-- Index for active conversations needing attention
CREATE INDEX idx_conversations_needs_attention 
ON conversations(last_message_at DESC) 
WHERE status = 'active' 
  AND last_message_at < NOW() - INTERVAL '5 minutes';

-- Index for conversations ready for follow-up
CREATE INDEX idx_conversations_follow_up 
ON conversations(created_at DESC) 
WHERE status = 'completed' 
  AND outcome IN ('follow_up_scheduled', 'callback_requested');

-- =====================================================================
-- JSONB INDEXES FOR FASTER QUERIES
-- =====================================================================

-- Index for customer metadata queries
CREATE INDEX idx_conversations_metadata_gin 
ON conversations USING gin(metadata);

-- Index for platform context queries
CREATE INDEX idx_conversations_platform_gin 
ON conversations USING gin(platform_context);

-- Index for ML event data queries
CREATE INDEX idx_ml_events_data_gin 
ON ml_tracking_events USING gin(event_data);

-- =====================================================================
-- ANALYZE TABLES TO UPDATE STATISTICS
-- =====================================================================

-- Update table statistics for query planner
ANALYZE conversations;
ANALYZE messages;
ANALYZE conversation_outcomes;
ANALYZE ml_tracking_events;
ANALYZE ml_training_data;
ANALYZE lead_scores;
ANALYZE objection_handling;
ANALYZE ab_experiments;
ANALYZE prompt_versions;

-- =====================================================================
-- PERFORMANCE NOTES
-- =====================================================================
-- 1. These indexes are designed based on common query patterns
-- 2. Monitor pg_stat_user_indexes to track index usage
-- 3. Consider partitioning messages table by created_at if it grows large
-- 4. Use EXPLAIN ANALYZE to verify query plans are using indexes
-- 5. Regularly run VACUUM ANALYZE to maintain performance

-- Query to check index usage:
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- ORDER BY idx_scan DESC;