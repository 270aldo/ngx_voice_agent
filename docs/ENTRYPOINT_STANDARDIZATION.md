# NGX Voice Sales Agent - Entry Point Standardization

## Overview

This document explains the standardization of entry points for the NGX Voice Sales Agent project, implemented on **August 10, 2025**.

## Problem Solved

**Before standardization:**
- Multiple confusing entry points: `run.py`, `start_api.py`, `src/api/main.py`, `src/api/main_simple.py`
- No clear indication of which file to use in different environments
- Duplication of initialization logic
- Confusion for new developers

**After standardization:**
- Single, clear entry point: `src/api/main.py`
- Unified startup script: `bin/start.sh`
- Clear documentation and examples
- Organized project structure

## Standard Entry Point

### Primary Method
```bash
uvicorn src.api.main:app
```

This is the **canonical way** to start the NGX Voice Sales Agent API.

### Convenience Script
```bash
./bin/start.sh [options]
```

The unified startup script supports different environments and configurations.

## File Organization

### ✅ Active Files
- **`src/api/main.py`** - Main FastAPI application (production-ready)
- **`bin/start.sh`** - Unified startup script for all environments

### 📁 Moved Files
- **`scripts/dev/run_dev.py`** - Development utility (moved from `run.py`)
- **`examples/simple_api_example.py`** - Basic API example (moved from `start_api.py`)

### 🗑️ Removed Files
- **`src/api/main_simple.py`** - Redundant file (deleted)

## Usage Examples

### Development
```bash
# With auto-reload
./bin/start.sh --env development

# Direct uvicorn
uvicorn src.api.main:app --reload
```

### Staging
```bash
./bin/start.sh --env staging --host 0.0.0.0
```

### Production
```bash
./bin/start.sh --env production --host 0.0.0.0 --workers 16
```

### Docker
```bash
./bin/start.sh --docker
```

## Benefits

1. **Clarity** - Single, obvious entry point
2. **Consistency** - Standard across all environments
3. **Flexibility** - Script supports multiple configurations
4. **Organization** - Files in appropriate directories
5. **Documentation** - Clear instructions in README

## Migration Notes

Existing deployments or scripts that use:
- `python run.py` → Use `./bin/start.sh` or `uvicorn src.api.main:app`
- `python start_api.py` → Use example for reference only
- `python src/api/main_simple.py` → Use `uvicorn src.api.main:app`

## Future Maintenance

- Keep `src/api/main.py` as the single source of truth
- Update `bin/start.sh` for new environment requirements
- Document any changes in this file
- Maintain backward compatibility when possible

---
**Last Updated:** August 10, 2025  
**Status:** ✅ Complete