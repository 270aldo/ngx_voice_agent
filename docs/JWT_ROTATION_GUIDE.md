# JWT Secret Rotation Guide

## Overview

The NGX Voice Sales Agent implements automatic JWT secret rotation to enhance security. The system uses a dual-key approach allowing graceful rotation without immediately invalidating existing tokens.

## Key Features

- **Automatic Rotation**: Secrets rotate every 30 days by default
- **Grace Period**: Previous secret remains valid for 7 days after rotation
- **Zero Downtime**: Tokens remain valid during rotation
- **Audit Trail**: All rotation events are logged
- **Manual Override**: Admins can force rotation when needed

## Architecture

### Rotation Service Components

1. **JWTRotationService**: Core rotation logic
   - Manages current and previous secrets
   - Handles secret generation and storage
   - Tracks rotation schedule

2. **JWTRotationScheduler**: Automated scheduling
   - Runs background checks hourly
   - Triggers rotation when due
   - Cleans up expired secrets

3. **Secrets Storage**: Secure key management
   - Uses secrets manager in production
   - Falls back to environment variables
   - Encrypts secrets at rest

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET=<initial-secret>              # Initial secret (required)
JWT_ALGORITHM=HS256                      # Algorithm (default: HS256)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30       # Access token lifetime
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7         # Refresh token lifetime

# Rotation Configuration (optional)
JWT_ROTATION_INTERVAL_DAYS=30            # Days between rotations
JWT_GRACE_PERIOD_DAYS=7                  # Days to keep old secret valid
```

### Database Tables

The following tables track rotation:

- `security_events`: General security event log
- `jwt_rotation_history`: Detailed rotation history

## API Endpoints

### Check Rotation Status
```bash
GET /security/jwt/status
Authorization: Bearer <admin-token>

Response:
{
  "success": true,
  "data": {
    "current_secret_active": true,
    "previous_secret_active": true,
    "last_rotation": "2024-01-15T10:00:00Z",
    "next_rotation": "2024-02-14T10:00:00Z",
    "rotation_due": false,
    "rotation_interval_days": 30,
    "grace_period_days": 7
  }
}
```

### Force Rotation
```bash
POST /security/jwt/rotate?force=true
Authorization: Bearer <admin-token>

Response:
{
  "success": true,
  "data": {
    "rotated": true,
    "message": "JWT secret rotated successfully",
    "next_rotation": "2024-02-14T10:00:00Z"
  }
}
```

### View Rotation History
```bash
GET /security/jwt/history?limit=10
Authorization: Bearer <admin-token>

Response:
{
  "success": true,
  "data": {
    "history": [
      {
        "id": "uuid",
        "rotation_timestamp": "2024-01-15T10:00:00Z",
        "rotation_reason": "scheduled",
        "success": true,
        "rotation_count": 5
      }
    ],
    "count": 1
  }
}
```

## Rotation Process

### Automatic Rotation Flow

1. **Scheduler Check** (Hourly)
   - Checks if rotation is due
   - Verifies system health

2. **Rotation Execution**
   - Generate new cryptographically secure secret
   - Move current secret to previous
   - Store new secret as current
   - Update rotation schedule

3. **Grace Period**
   - Both secrets remain valid
   - New tokens use new secret
   - Old tokens still validate

4. **Cleanup**
   - After grace period expires
   - Previous secret is deleted
   - Only current secret remains

### Manual Rotation

Admins can force rotation in case of:
- Security breach
- Suspected key compromise
- Compliance requirements

```python
# Via API
POST /security/jwt/rotate?force=true

# Via CLI (if implemented)
python manage.py rotate-jwt-secret --force
```

## Token Validation

The system validates tokens using multiple secrets:

```python
# Pseudocode for validation logic
def validate_token(token):
    # Try current secret first
    try:
        return decode_with_secret(token, current_secret)
    except InvalidToken:
        # Try previous secret during grace period
        if previous_secret_exists:
            try:
                return decode_with_secret(token, previous_secret)
            except InvalidToken:
                pass
    
    raise InvalidToken("Token validation failed")
```

## Security Best Practices

1. **Production Requirements**
   - Always use secrets manager
   - Enable audit logging
   - Monitor rotation events
   - Set up alerts for failures

2. **Secret Generation**
   - 512-bit (64 bytes) random secrets
   - Cryptographically secure random generator
   - Base64 encoded for storage

3. **Access Control**
   - Only admins can view rotation status
   - Only admins can force rotation
   - Rotation history requires admin role

4. **Monitoring**
   - Track rotation success rate
   - Alert on rotation failures
   - Monitor token validation errors
   - Review security events regularly

## Troubleshooting

### Common Issues

1. **"Rotation failed"**
   - Check secrets manager connectivity
   - Verify database permissions
   - Review error logs

2. **"Token validation failed after rotation"**
   - Ensure grace period is active
   - Check if token was issued before rotation
   - Verify both secrets are loaded

3. **"Scheduler not running"**
   - Only runs in production mode
   - Check application startup logs
   - Verify asyncio event loop

### Emergency Procedures

1. **Rollback Rotation**
   ```sql
   -- Restore previous secret as current
   UPDATE secrets SET 
     key = 'jwt_current_secret',
     value = (SELECT value FROM secrets WHERE key = 'jwt_previous_secret')
   WHERE key = 'jwt_current_secret';
   ```

2. **Disable Rotation**
   - Set environment variable: `JWT_ROTATION_ENABLED=false`
   - Restart application

3. **Extended Grace Period**
   - Update `JWT_GRACE_PERIOD_DAYS` to larger value
   - Allows more time for token migration

## Integration with CI/CD

### Deployment Considerations

1. **Rolling Updates**
   - New instances get latest secrets
   - Old instances use cached secrets
   - Grace period handles transition

2. **Secret Propagation**
   - Use centralized secrets manager
   - Avoid hardcoded secrets
   - Automate secret distribution

3. **Testing**
   ```bash
   # Run rotation tests
   pytest tests/unit/services/test_jwt_rotation_service.py
   
   # Test token validation with multiple secrets
   pytest tests/integration/test_jwt_rotation_integration.py
   ```

## Compliance

The JWT rotation system helps meet various compliance requirements:

- **PCI DSS**: Regular key rotation
- **SOC 2**: Cryptographic key management
- **ISO 27001**: Access control and key lifecycle
- **GDPR**: Security of processing

## Future Enhancements

1. **Asymmetric Keys**: Support for RS256/ES256
2. **HSM Integration**: Hardware security module support
3. **Key Versioning**: Multiple active keys with versions
4. **Automated Alerts**: Slack/email notifications
5. **Metrics Dashboard**: Grafana dashboard for rotation metrics