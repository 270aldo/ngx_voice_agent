"""
Cache Migration Tests - Validate the cache service consolidation.

These tests ensure that the migration from legacy cache services to the
consolidated CacheService works correctly with backward compatibility.
"""

import pytest
import asyncio
import warnings
from unittest.mock import patch, MagicMock
import sys
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, '.')

from src.config import settings
from src.services.cache_service import CacheService, get_cache_instance
from src.services.cache_compatibility import (
    RedisCacheServiceCompat,
    NGXCacheManagerCompat,
    HTTPCacheServiceCompat,
    ResponsePrecomputationServiceCompat,
    log_cache_migration_progress
)
from src.core.dependencies_migrated import (
    get_redis_cache,
    get_ngx_cache_manager,
    initialize_dependencies
)


class TestCacheCompatibilityLayer:
    """Test the cache compatibility layer."""
    
    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock consolidated cache service."""
        cache = MagicMock(spec=CacheService)
        cache.get.return_value = None
        cache.set.return_value = True
        cache.delete.return_value = True
        cache.health_check.return_value = True
        cache.get_service_stats.return_value = {
            "total_entries": 100,
            "hit_rate": 0.85,
            "total_size_bytes": 1024000
        }
        return cache
    
    @pytest.mark.asyncio
    async def test_redis_cache_service_compat_initialization(self, mock_cache_service):
        """Test RedisCacheServiceCompat initialization."""
        with patch('src.services.cache_compatibility.get_cache_instance', return_value=mock_cache_service):
            compat_service = RedisCacheServiceCompat()
            
            # Capture deprecation warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                await compat_service.initialize()
                
                # Check that deprecation warning was issued
                assert len(w) > 0
                assert issubclass(w[0].category, DeprecationWarning)
                assert "RedisCacheService is deprecated" in str(w[0].message)
            
            assert compat_service._connected
            assert compat_service._cache is not None
    
    @pytest.mark.asyncio
    async def test_redis_cache_service_compat_operations(self, mock_cache_service):
        """Test RedisCacheServiceCompat basic operations."""
        with patch('src.services.cache_compatibility.get_cache_instance', return_value=mock_cache_service):
            compat_service = RedisCacheServiceCompat()
            await compat_service.initialize()
            
            # Test set operation
            result = await compat_service.set("test_key", "test_value", ttl=300)
            assert result is True
            mock_cache_service.set.assert_called_once()
            
            # Test get operation
            mock_cache_service.get.return_value = "test_value"
            value = await compat_service.get("test_key")
            assert value == "test_value"
            
            # Test delete operation
            result = await compat_service.delete("test_key")
            assert result is True
            mock_cache_service.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ngx_cache_manager_compat(self, mock_cache_service):
        """Test NGXCacheManagerCompat functionality."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            compat_manager = NGXCacheManagerCompat(mock_cache_service)
            
            # Check deprecation warning
            assert len(w) > 0
            assert issubclass(w[0].category, DeprecationWarning)
            assert "NGXCacheManager is deprecated" in str(w[0].message)
        
        # Test that it has the expected key mappings
        assert "conversation" in compat_manager.keys
        assert "customer" in compat_manager.keys
        assert "prediction" in compat_manager.keys
        
        # Test TTL constants
        assert compat_manager.TTL_CONVERSATION == 7200
        assert compat_manager.TTL_CUSTOMER == 10800
    
    @pytest.mark.asyncio
    async def test_http_cache_service_compat(self):
        """Test HTTPCacheServiceCompat initialization."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            compat_service = HTTPCacheServiceCompat()
            
            # Check deprecation warning
            assert len(w) > 0
            assert issubclass(w[0].category, DeprecationWarning)
            assert "HTTPCacheService is deprecated" in str(w[0].message)
        
        # Test configuration
        assert compat_service.config["enable_compression"]
        assert compat_service.config["default_ttl_seconds"] == 300
    
    @pytest.mark.asyncio
    async def test_response_precomputation_service_compat(self, mock_cache_service):
        """Test ResponsePrecomputationServiceCompat functionality."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            compat_service = ResponsePrecomputationServiceCompat(mock_cache_service)
            
            # Check deprecation warning
            assert len(w) > 0
            assert issubclass(w[0].category, DeprecationWarning)
            assert "ResponsePrecomputationService is deprecated" in str(w[0].message)
        
        # Test that patterns are compiled
        assert len(compat_service.pattern_cache) > 0
        assert any("pricing" in str(pattern.pattern) for pattern in compat_service.pattern_cache.keys())


class TestConsolidatedCacheIntegration:
    """Test consolidated cache integration."""
    
    @pytest.mark.asyncio
    async def test_consolidated_cache_basic_operations(self):
        """Test basic operations on consolidated cache."""
        # Mock Redis for testing
        with patch.dict('os.environ', {'REDIS_MOCK_ENABLED': 'true'}):
            cache = await get_cache_instance()
            assert cache is not None
            
            # Test set/get
            test_key = "integration_test_key"
            test_value = {"data": "test", "number": 123}
            
            success = await cache.set(test_key, test_value, ttl=60)
            assert success
            
            retrieved = await cache.get(test_key)
            assert retrieved == test_value
            
            # Test delete
            deleted = await cache.delete(test_key)
            assert deleted
            
            # Verify deletion
            retrieved_after_delete = await cache.get(test_key)
            assert retrieved_after_delete is None
    
    @pytest.mark.asyncio
    async def test_ngx_specific_operations(self):
        """Test NGX-specific cache operations."""
        with patch.dict('os.environ', {'REDIS_MOCK_ENABLED': 'true'}):
            cache = await get_cache_instance()
            assert cache is not None
            
            # Test conversation caching (would need proper ConversationState model)
            conv_id = "test_conversation_123"
            conv_data = {
                "id": conv_id,
                "customer_id": "cust_123",
                "messages": ["Hello", "Hi there!"],
                "status": "active"
            }
            
            # For now, test with basic data structure
            success = await cache.set(f"conv:{conv_id}", conv_data, ttl=7200)
            assert success
            
            retrieved_conv = await cache.get(f"conv:{conv_id}")
            assert retrieved_conv == conv_data
            
            # Test precomputed responses
            response_key = "pricing_response_hash"
            response_text = "Our programs start at $79/month"
            
            success = await cache.set_precomputed_response(
                response_key, response_text, confidence=0.95
            )
            assert success
            
            retrieved_response = await cache.get_precomputed_response(response_key)
            assert retrieved_response == response_text
    
    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """Test cache statistics functionality."""
        with patch.dict('os.environ', {'REDIS_MOCK_ENABLED': 'true'}):
            cache = await get_cache_instance()
            assert cache is not None
            
            # Get initial stats
            stats = await cache.get_service_stats()
            assert isinstance(stats, dict)
            assert "hit_rate" in stats
            assert "total_entries" in stats
            
            # Add some data and check stats update
            await cache.set("stats_test_1", "value1")
            await cache.set("stats_test_2", "value2")
            
            # Get updated stats
            updated_stats = await cache.get_service_stats()
            assert isinstance(updated_stats, dict)


class TestFeatureFlagMigration:
    """Test feature flag controlled migration."""
    
    @pytest.mark.asyncio
    async def test_consolidated_cache_enabled(self):
        """Test behavior when consolidated cache is enabled."""
        with patch.dict('os.environ', {
            'USE_CONSOLIDATED_CACHE': 'true',
            'REDIS_MOCK_ENABLED': 'true'
        }):
            # Re-import settings to pick up environment changes
            import importlib
            from src import config
            importlib.reload(config)
            
            cache = await get_redis_cache()
            assert cache is not None
            
            # Should be using consolidated cache
            assert hasattr(cache, 'get_service_stats')
    
    @pytest.mark.asyncio
    async def test_consolidated_cache_disabled(self):
        """Test behavior when consolidated cache is disabled."""
        with patch.dict('os.environ', {
            'USE_CONSOLIDATED_CACHE': 'false',
            'REDIS_MOCK_ENABLED': 'true'
        }):
            # This would test fallback to compatibility layer
            # In a real scenario, this would use the legacy services
            pass
    
    def test_migration_progress_logging(self, capsys):
        """Test migration progress logging."""
        with patch.dict('os.environ', {'USE_CONSOLIDATED_CACHE': 'true'}):
            log_cache_migration_progress()
            captured = capsys.readouterr()
            # The actual logging might go to logger, not stdout
            # This is a placeholder test


class TestBackwardCompatibility:
    """Test backward compatibility during migration."""
    
    @pytest.mark.asyncio
    async def test_legacy_interface_compatibility(self):
        """Test that legacy interfaces still work during migration."""
        with patch.dict('os.environ', {'REDIS_MOCK_ENABLED': 'true'}):
            # Test that we can still import and use legacy interfaces
            # through the compatibility layer
            
            # This simulates existing code that uses legacy interfaces
            cache_manager = await get_ngx_cache_manager()
            assert cache_manager is not None
            
            # Test that legacy-style operations work
            if hasattr(cache_manager, 'set'):
                success = await cache_manager.set("legacy_test", {"data": "test"}, ttl=60)
                # Depending on implementation, this might work or need adaptation
    
    @pytest.mark.asyncio 
    async def test_dependency_injection_compatibility(self):
        """Test that dependency injection still works after migration."""
        with patch.dict('os.environ', {'REDIS_MOCK_ENABLED': 'true'}):
            # Test dependencies initialization
            await initialize_dependencies()
            
            # Get cache through dependency system
            cache = await get_redis_cache()
            assert cache is not None
            
            cache_manager = await get_ngx_cache_manager()
            assert cache_manager is not None


class TestMigrationRollback:
    """Test migration rollback scenarios."""
    
    @pytest.mark.asyncio
    async def test_rollback_capability(self):
        """Test that migration can be rolled back."""
        # Test switching from consolidated back to legacy
        original_setting = settings.use_consolidated_cache
        
        try:
            # Simulate rollback by changing setting
            with patch.object(settings, 'use_consolidated_cache', False):
                # This would test fallback behavior
                # In practice, this requires restart to take effect
                pass
        finally:
            # Restore original setting
            pass
    
    @pytest.mark.asyncio
    async def test_data_preservation_during_rollback(self):
        """Test that cache data is preserved during rollback."""
        # This would test that switching between cache implementations
        # doesn't lose data (assuming same Redis backend)
        pass


class TestErrorHandling:
    """Test error handling during migration."""
    
    @pytest.mark.asyncio
    async def test_consolidated_cache_failure_fallback(self):
        """Test fallback behavior when consolidated cache fails."""
        # Simulate consolidated cache failure
        with patch('src.services.cache_service.get_cache_instance', side_effect=Exception("Cache init failed")):
            # Should gracefully fall back or handle error
            cache = await get_redis_cache()
            # Depending on implementation, might return None or fallback cache
    
    @pytest.mark.asyncio
    async def test_compatibility_layer_error_handling(self):
        """Test error handling in compatibility layer."""
        with patch('src.services.cache_compatibility.get_cache_instance', return_value=None):
            compat_service = RedisCacheServiceCompat()
            
            # Should handle initialization failure gracefully
            await compat_service.initialize()
            assert not compat_service._connected
            
            # Operations should return appropriate defaults
            value = await compat_service.get("test_key", "default")
            assert value == "default"


@pytest.mark.asyncio
async def test_performance_comparison():
    """Test performance comparison between legacy and consolidated cache."""
    import time
    
    with patch.dict('os.environ', {'REDIS_MOCK_ENABLED': 'true'}):
        cache = await get_cache_instance()
        
        # Simple performance test
        start_time = time.time()
        
        for i in range(100):
            await cache.set(f"perf_test_{i}", {"data": i}, ttl=60)
            await cache.get(f"perf_test_{i}")
        
        elapsed = time.time() - start_time
        
        # Should complete reasonably quickly (less than 1 second for mock)
        assert elapsed < 1.0
        
        # Cleanup
        for i in range(100):
            await cache.delete(f"perf_test_{i}")


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])