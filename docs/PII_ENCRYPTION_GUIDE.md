# PII Encryption Guide

## Overview

The NGX Voice Sales Agent implements AES-256-GCM encryption for all Personal Identifiable Information (PII) stored in the database. This ensures GDPR compliance and protects sensitive customer data.

## Encrypted Fields

### Customer Table
- `name` - Full name
- `email` - Email address  
- `phone` - Phone number
- `age` - Age
- `gender` - Gender
- `occupation` - Occupation/profession

### Conversations Table
- `customer_data` (JSONB) - Contains encrypted customer information

### Trial Events Table
- `ip_address` - User IP address
- `user_agent` - Browser/device information

## Implementation Details

### Encryption Algorithm
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations
- **Nonce**: 12-byte random nonce per encryption
- **Authentication**: GCM provides built-in authentication

### Environment Variables

Required in production:
```bash
ENCRYPTION_MASTER_KEY=<base64-encoded-32-byte-key>
ENCRYPTION_SALT=<base64-encoded-16-byte-salt>
```

Generate keys:
```bash
# Generate master key
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Generate salt  
python -c "import os, base64; print(base64.b64encode(os.urandom(16)).decode())"
```

## Usage

### Using Encrypted Supabase Client

```python
from src.integrations.supabase.resilient_client import ResilientSupabaseClient

# Client automatically handles encryption/decryption
client = ResilientSupabaseClient(enable_encryption=True)

# Insert encrypted data
customer_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "555-1234"
}

# Data is automatically encrypted before insert
result = await client.table("customers").insert(customer_data).execute()

# Data is automatically decrypted on select
result = await client.table("customers").select("*").eq("id", customer_id).execute()
customer = result.data[0]  # PII fields are decrypted
```

### Manual Encryption/Decryption

```python
from src.services.encryption_service import get_encryption_service

service = get_encryption_service()

# Encrypt single value
encrypted_email = service.encrypt("john@example.com")

# Decrypt single value  
email = service.decrypt(encrypted_email)

# Encrypt multiple PII fields
data = {"name": "John", "email": "john@example.com", "public_field": "data"}
encrypted = service.encrypt_pii_fields(data, ["name", "email"])
```

### Searching Encrypted Data

For exact match searches on encrypted fields:

```python
# Create search hash for indexed lookups
email_hash = service.hash_identifier("john@example.com")
result = await client.table("customers").select("*").eq("email_hash", email_hash).execute()

# Or use encrypted search token
search_token = service.create_search_token("email", "john@example.com")
result = await client.table("customers").select("*").eq("email", search_token).execute()
```

## Database Migration

1. Run the PII encryption migration:
```bash
psql $DATABASE_URL -f scripts/migrations/008_pii_encryption.sql
```

2. Encrypt existing data:
```bash
# Dry run first
python scripts/encrypt_existing_data.py --dry-run

# Encrypt all tables
python scripts/encrypt_existing_data.py

# Encrypt specific tables
python scripts/encrypt_existing_data.py --tables customers conversations
```

## Security Best Practices

1. **Key Management**
   - Store encryption keys in secure environment variables
   - Never commit keys to version control
   - Use different keys for each environment
   - Rotate keys periodically

2. **Access Control**
   - Limit access to decryption capabilities
   - Log all encryption/decryption operations
   - Use RLS policies to restrict data access

3. **Monitoring**
   - Monitor encryption_audit table for anomalies
   - Set up alerts for decryption failures
   - Track performance impact

4. **Compliance**
   - Document all PII fields
   - Implement data retention policies
   - Support right to erasure (GDPR)
   - Regular security audits

## Testing

Run encryption tests:
```bash
pytest tests/unit/services/test_encryption_service.py -v
```

## Troubleshooting

### Common Issues

1. **"ENCRYPTION_MASTER_KEY must be set in production"**
   - Ensure environment variables are properly set
   - Check that values are base64 encoded

2. **Decryption failures**
   - Verify the correct key is being used
   - Check if data was encrypted with a different key
   - Look for corruption in stored ciphertext

3. **Performance issues**
   - Consider caching decrypted data in memory
   - Use batch operations for bulk encryption
   - Monitor encryption_audit for bottlenecks

### Rollback

To disable encryption temporarily:
```python
client = ResilientSupabaseClient(enable_encryption=False)
```

To decrypt all data permanently:
```python
# Use decrypt_existing_data.py script (create if needed)
```

## Future Enhancements

1. **Field-level encryption keys** - Different keys for different sensitivity levels
2. **Hardware Security Module (HSM)** integration
3. **Transparent Data Encryption (TDE)** at database level
4. **Homomorphic encryption** for analytics on encrypted data
5. **Key rotation automation**