-- Migration: Add PII encryption support
-- Description: Adds hash columns for searchable encrypted PII fields and encryption metadata

-- Add hash columns for searchable PII fields in customers table
ALTER TABLE customers 
ADD COLUMN IF NOT EXISTS email_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT FALSE;

-- Create index on email hash for fast lookups
CREATE INDEX IF NOT EXISTS idx_customers_email_hash ON customers(email_hash);

-- Add encryption tracking to conversations
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS pii_encrypted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS encryption_version INTEGER DEFAULT 1;

-- Add encryption audit table
CREATE TABLE IF NOT EXISTS encryption_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL, -- 'encrypt', 'decrypt', 'access'
    field_names TEXT[], -- Array of field names affected
    user_id UUID,
    ip_address INET,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Create index on encryption audit for monitoring
CREATE INDEX IF NOT EXISTS idx_encryption_audit_timestamp ON encryption_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_encryption_audit_table_record ON encryption_audit(table_name, record_id);

-- Add function to automatically set email hash on insert/update
CREATE OR REPLACE FUNCTION set_email_hash()
RETURNS TRIGGER AS $$
BEGIN
    -- Only set hash if email is provided and encrypted
    IF NEW.email IS NOT NULL AND NEW.is_encrypted = TRUE THEN
        -- This will be replaced by application-level hashing
        -- For now, just mark that hash should be set
        NEW.email_hash = 'pending_hash';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for email hash
DROP TRIGGER IF EXISTS tr_set_email_hash ON customers;
CREATE TRIGGER tr_set_email_hash
BEFORE INSERT OR UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION set_email_hash();

-- Add encryption support to trial_events
ALTER TABLE trial_events
ADD COLUMN IF NOT EXISTS ip_address_encrypted TEXT,
ADD COLUMN IF NOT EXISTS user_agent_encrypted TEXT,
ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT FALSE;

-- Create view for decrypted customer data (for backward compatibility)
-- Note: Actual decryption happens at application level
CREATE OR REPLACE VIEW customers_decrypted AS
SELECT 
    id,
    CASE 
        WHEN is_encrypted THEN 'encrypted'
        ELSE name
    END as name,
    CASE 
        WHEN is_encrypted THEN 'encrypted'
        ELSE email
    END as email,
    age,
    gender,
    occupation,
    created_at,
    updated_at,
    is_encrypted
FROM customers;

-- Add RLS policies for encryption audit
ALTER TABLE encryption_audit ENABLE ROW LEVEL SECURITY;

-- Policy: Only admins can view encryption audit
CREATE POLICY encryption_audit_admin_only ON encryption_audit
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM auth.users
        WHERE auth.users.id = auth.uid()
        AND auth.users.raw_user_meta_data->>'role' = 'admin'
    )
);

-- Add comment to document encryption
COMMENT ON TABLE encryption_audit IS 'Audit log for PII encryption/decryption operations';
COMMENT ON COLUMN customers.email_hash IS 'SHA-256 hash of email for searching encrypted data';
COMMENT ON COLUMN customers.is_encrypted IS 'Whether PII fields in this record are encrypted';
COMMENT ON COLUMN conversations.pii_encrypted IS 'Whether customer_data JSONB contains encrypted PII';

-- Migration rollback script
/*
-- To rollback this migration:
ALTER TABLE customers 
DROP COLUMN IF EXISTS email_hash,
DROP COLUMN IF EXISTS is_encrypted;

ALTER TABLE conversations
DROP COLUMN IF EXISTS pii_encrypted,
DROP COLUMN IF EXISTS encryption_version;

ALTER TABLE trial_events
DROP COLUMN IF EXISTS ip_address_encrypted,
DROP COLUMN IF EXISTS user_agent_encrypted,
DROP COLUMN IF EXISTS is_encrypted;

DROP TABLE IF EXISTS encryption_audit;
DROP VIEW IF EXISTS customers_decrypted;
DROP FUNCTION IF EXISTS set_email_hash();
*/