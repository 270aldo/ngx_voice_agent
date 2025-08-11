# Configuration System Migration Guide

## Overview

The NGX Voice Sales Agent configuration system has been successfully unified to eliminate duplication between `src/core/config.py` and `src/config/settings.py`. This migration improves maintainability, adds better validation, and provides a more modern configuration structure.

## What Changed

### 1. Unified Configuration
- **Primary Config**: `src/config/settings.py` is now the single source of truth
- **Deprecated Config**: `src/core/config.py` is deprecated and acts as a proxy

### 2. Backward Compatibility
- All existing code continues to work without changes
- Uppercase property names are maintained via compatibility properties
- Import paths remain functional during transition period

### 3. Enhanced Features
- Better type safety with Pydantic v2
- SecretStr for sensitive configuration values
- Computed fields for complex configurations
- Enhanced validation and environment support

## Migration Details

### Files Updated
1. `src/core/auth/deps.py` - Updated import to use unified settings
2. `src/api/v1/endpoints/auth.py` - Updated import to use unified settings  
3. `src/api/middleware/csrf_protection.py` - Updated import to use unified settings
4. `src/services/websocket/websocket_manager.py` - Updated import to use unified settings
5. `src/core/config.py` - Deprecated and converted to proxy

### Variable Name Mapping

| Old (core/config.py) | New (config/settings.py) | Compatibility Property |
|---------------------|-------------------------|----------------------|
| JWT_SECRET_KEY | jwt_secret | ✅ Available |
| JWT_ALGORITHM | jwt_algorithm | ✅ Available |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | jwt_access_token_expire_minutes | ✅ Available |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | jwt_refresh_token_expire_days | ✅ Available |
| SUPABASE_URL | supabase_url | ✅ Available |
| SUPABASE_ANON_KEY | supabase_anon_key | ✅ Available |
| SUPABASE_SERVICE_KEY | supabase_service_role_key | ✅ Available |
| OPENAI_API_KEY | openai_api_key | ✅ Available |
| OPENAI_MODEL | openai_model | ✅ Available |
| OPENAI_MAX_TOKENS | openai_max_tokens | ✅ Available |
| OPENAI_TEMPERATURE | openai_temperature | ✅ Available |
| ELEVENLABS_API_KEY | elevenlabs_api_key | ✅ Available |
| ELEVENLABS_VOICE_ID | elevenlabs_voice_id | ✅ Available |
| REDIS_URL | redis_url | ✅ Available |
| REDIS_PASSWORD | (computed from redis_url) | ✅ Available |
| ALLOWED_ORIGINS | allowed_origins_str | ✅ Available |

## Usage Examples

### Current Usage (Still Works)
```python
from src.core.config import settings

# These continue to work with deprecation warning
secret = settings.JWT_SECRET_KEY
algorithm = settings.JWT_ALGORITHM
```

### Recommended Usage (New)
```python
from src.config.settings import settings

# Modern approach with type safety
secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else None
algorithm = settings.jwt_algorithm

# Or use compatibility properties (no deprecation warning)
secret = settings.JWT_SECRET_KEY
algorithm = settings.JWT_ALGORITHM
```

## Enhanced Features

### 1. SecretStr for Sensitive Data
```python
# Automatically masks secrets in logs and serialization
settings.jwt_secret  # Returns SecretStr object
settings.jwt_secret.get_secret_value()  # Returns actual string
```

### 2. Better Validation
```python
# JWT secret required in production
# Database URL validation
# Port range validation (1-65535)
# Percentage validation (0-1) for ML settings
```

### 3. Environment-Specific Configurations
```python
# Production vs Development settings
if settings.is_production:
    # Production-specific logic
elif settings.is_development:
    # Development-specific logic
```

### 4. Computed Properties
```python
# Automatically parsed from comma-separated strings
settings.allowed_origins  # List[str] from CSV
settings.allow_methods    # List[str] from CSV
settings.allow_headers    # List[str] from CSV
```

## Migration Timeline

- **Current (v1.x)**: Both configurations work, deprecation warnings issued
- **Next Minor (v1.1)**: Deprecation warnings become more prominent
- **Major (v2.0)**: `src/core/config.py` will be completely removed

## Action Required

### For Immediate Use
✅ **No action required** - All existing code continues to work

### For Future-Proofing (Recommended)
1. Update imports to use `from src.config.settings import settings`
2. Use modern lowercase property names where possible
3. Handle SecretStr properly for sensitive values

### Example Migration
```python
# Before
from src.core.config import settings
token = settings.JWT_SECRET_KEY

# After (recommended)
from src.config.settings import settings  
token = settings.jwt_secret.get_secret_value() if settings.jwt_secret else None

# After (compatible)
from src.config.settings import settings
token = settings.JWT_SECRET_KEY  # Uses compatibility property
```

## Benefits

1. **Single Source of Truth**: No more configuration duplication
2. **Better Security**: SecretStr prevents accidental secret exposure
3. **Type Safety**: Full Pydantic v2 validation and type hints
4. **Future-Ready**: Modern configuration patterns
5. **Maintainability**: Centralized configuration management

## Support

For questions about this migration, please refer to:
- This migration guide
- `src/config/settings.py` documentation
- Project maintainers

The configuration system is now unified and ready for production use! 🚀