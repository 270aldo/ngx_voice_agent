-- Migration: Security Events Table
-- Description: Create table for tracking security events including JWT rotations

-- Create security events table
CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    next_rotation TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_user ON security_events(user_id);

-- Create table for JWT rotation history
CREATE TABLE IF NOT EXISTS jwt_rotation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rotation_timestamp TIMESTAMPTZ DEFAULT NOW(),
    previous_secret_hash VARCHAR(64),  -- SHA-256 hash of previous secret
    new_secret_hash VARCHAR(64),       -- SHA-256 hash of new secret
    rotation_reason VARCHAR(100),       -- 'scheduled', 'manual', 'security_incident'
    rotation_count INTEGER DEFAULT 0,
    grace_period_end TIMESTAMPTZ,
    initiated_by VARCHAR(100),          -- 'system', 'admin', etc.
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    metadata JSONB
);

-- Create index on rotation history
CREATE INDEX IF NOT EXISTS idx_jwt_rotation_timestamp ON jwt_rotation_history(rotation_timestamp DESC);

-- Add RLS policies
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE jwt_rotation_history ENABLE ROW LEVEL SECURITY;

-- Policy: Only admins can view security events
CREATE POLICY security_events_admin_only ON security_events
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.users.id = auth.uid()
        AND auth.users.raw_user_meta_data->>'role' = 'admin'
    )
);

-- Policy: Only admins can view JWT rotation history
CREATE POLICY jwt_rotation_admin_only ON jwt_rotation_history
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.users.id = auth.uid()
        AND auth.users.raw_user_meta_data->>'role' = 'admin'
    )
);

-- Create function to log security events
CREATE OR REPLACE FUNCTION log_security_event(
    p_event_type VARCHAR,
    p_success BOOLEAN DEFAULT TRUE,
    p_error_message TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL,
    p_user_id UUID DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
BEGIN
    INSERT INTO security_events (
        event_type,
        success,
        error_message,
        metadata,
        user_id
    ) VALUES (
        p_event_type,
        p_success,
        p_error_message,
        p_metadata,
        p_user_id
    ) RETURNING id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Create view for recent security events
CREATE OR REPLACE VIEW recent_security_events AS
SELECT 
    id,
    event_type,
    success,
    timestamp,
    error_message,
    user_id,
    CASE 
        WHEN metadata->>'ip_address' IS NOT NULL THEN 
            substring(metadata->>'ip_address' from 1 for position('.' in metadata->>'ip_address' || '.') + 3) || 'xxx'
        ELSE NULL
    END as masked_ip
FROM security_events
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- Add comments
COMMENT ON TABLE security_events IS 'Audit log for security-related events';
COMMENT ON TABLE jwt_rotation_history IS 'History of JWT secret rotations';
COMMENT ON FUNCTION log_security_event IS 'Helper function to log security events';
COMMENT ON VIEW recent_security_events IS 'Recent security events with masked IP addresses';

-- Migration rollback script
/*
-- To rollback this migration:
DROP VIEW IF EXISTS recent_security_events;
DROP FUNCTION IF EXISTS log_security_event;
DROP TABLE IF EXISTS jwt_rotation_history;
DROP TABLE IF EXISTS security_events;
*/