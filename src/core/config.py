"""
DEPRECATED: Application configuration settings for NGX Voice Agent

⚠️  DEPRECATION WARNING: This module is deprecated and will be removed in v2.0.0.
    Please migrate to `src.config.settings` for unified configuration management.

This module now acts as a proxy to the unified settings system to maintain
backward compatibility during the migration period.
"""

import warnings
from src.config.settings import settings as unified_settings

# Issue deprecation warning when this module is imported
warnings.warn(
    "src.core.config is deprecated and will be removed in v2.0.0. "
    "Please use src.config.settings instead.",
    DeprecationWarning,
    stacklevel=2
)

# Proxy to unified settings for backward compatibility
settings = unified_settings