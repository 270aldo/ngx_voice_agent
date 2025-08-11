"""
API Dependencies for FastAPI dependency injection.

This module provides dependency functions for API endpoints.
"""

from typing import Optional
from fastapi import Depends

from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
from src.integrations.supabase.client import supabase_client
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)

# Global instances
_ml_pipeline_service: Optional[MLPipelineService] = None


async def get_ml_pipeline_service() -> MLPipelineService:
    """
    Get ML Pipeline Service instance.
    
    Returns:
        MLPipelineService instance
    """
    global _ml_pipeline_service
    
    if _ml_pipeline_service is None:
        try:
            _ml_pipeline_service = MLPipelineService()
            logger.info("ML Pipeline Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ML Pipeline Service: {e}")
            # Return a mock instance to prevent crashes
            _ml_pipeline_service = MLPipelineService()
    
    return _ml_pipeline_service


async def get_database():
    """
    Get database connection.
    
    Yields:
        Database client
    """
    yield supabase_client