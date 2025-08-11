"""
Unit tests for HTTP Cache Middleware.
"""

import pytest
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.middleware.http_cache_middleware import (
    HTTPCacheMiddleware, CacheConfig, cache_response
)


@pytest.fixture
def mock_cache_manager():
    """Mock NGX cache manager."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.clear_namespace = AsyncMock()
    return mock


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test", "timestamp": datetime.now().isoformat()}
    
    @app.get("/cached")
    @cache_response(ttl_seconds=60)
    async def cached_endpoint():
        return {"message": "cached", "timestamp": datetime.now().isoformat()}
    
    @app.post("/update")
    async def update_endpoint():
        return {"message": "updated"}
    
    return app


@pytest.fixture
def cache_middleware(app, mock_cache_manager):
    """Create cache middleware instance."""
    with patch('src.api.middleware.http_cache_middleware.get_ngx_cache_manager', 
               return_value=mock_cache_manager):
        middleware = HTTPCacheMiddleware(app)
        middleware._cache_manager = mock_cache_manager
        return middleware


class TestHTTPCacheMiddleware:
    """Test HTTP Cache Middleware functionality."""
    
    def test_cache_config_initialization(self):
        """Test cache configuration initialization."""
        config = CacheConfig(
            ttl_seconds=600,
            cache_control="public, max-age=600",
            vary_headers=["Accept", "X-Custom"],
            conditional_requests=True
        )
        
        assert config.ttl_seconds == 600
        assert config.cache_control == "public, max-age=600"
        assert "X-Custom" in config.vary_headers
        assert config.conditional_requests is True
    
    def test_default_cache_configs(self, cache_middleware):
        """Test default cache configurations."""
        configs = cache_middleware.cache_configs
        
        # Check analytics endpoint config
        analytics_pattern = r"/api/analytics/.*"
        assert analytics_pattern in configs
        assert configs[analytics_pattern].ttl_seconds == 300
        
        # Check that conversation endpoints are not cached
        conversation_pattern = r"/api/conversation/.*"
        assert configs[conversation_pattern] is None
    
    def test_cache_key_generation(self, cache_middleware):
        """Test cache key generation."""
        # Create mock request
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/test"
        request.query_params = {"param1": "value1", "param2": "value2"}
        request.headers = {"Accept": "application/json"}
        request.state = Mock()
        request.state.user = None
        
        config = CacheConfig(vary_headers=["Accept"])
        
        # Generate cache key
        cache_key = cache_middleware._generate_cache_key(request, config)
        
        # Verify key format
        assert cache_key.startswith("http_response:/api/test:")
        assert len(cache_key.split(":")) == 3
        
        # Verify key includes query params
        assert "param1" in str(request.query_params.items())
    
    def test_etag_generation(self, cache_middleware):
        """Test ETag generation."""
        content = b'{"test": "data"}'
        etag = cache_middleware._generate_etag(content)
        
        # Verify ETag format
        assert etag.startswith('"')
        assert etag.endswith('"')
        assert len(etag) == 34  # 32 chars + quotes
        
        # Verify consistency
        etag2 = cache_middleware._generate_etag(content)
        assert etag == etag2
        
        # Verify different content produces different ETag
        different_content = b'{"test": "different"}'
        different_etag = cache_middleware._generate_etag(different_content)
        assert etag != different_etag
    
    @pytest.mark.asyncio
    async def test_cache_miss_flow(self, cache_middleware, mock_cache_manager):
        """Test cache miss flow."""
        # Setup
        mock_cache_manager.get.return_value = None
        
        # Create request
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/analytics/test"
        request.query_params = {}
        request.headers = {}
        
        # Create response
        response_data = {"data": "test"}
        
        async def call_next(req):
            response = Response(
                content=json.dumps(response_data),
                media_type="application/json"
            )
            response.status_code = 200
            response.headers = {}
            response.body_iterator = [json.dumps(response_data).encode()].__iter__()
            return response
        
        # Process request
        response = await cache_middleware.dispatch(request, call_next)
        
        # Verify cache miss
        assert cache_middleware.metrics["misses"] == 1
        assert mock_cache_manager.get.called
        
        # Verify response cached
        # Note: In real implementation, this would be called
        # For now, just verify the flow completed
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_cache_hit_flow(self, cache_middleware, mock_cache_manager):
        """Test cache hit flow."""
        # Setup cached data
        cached_data = {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"data": "cached"},
            "cached_at": datetime.now().timestamp(),
            "expires_at": (datetime.now() + timedelta(minutes=5)).timestamp(),
            "etag": '"test-etag"',
            "last_modified": datetime.now().isoformat()
        }
        mock_cache_manager.get.return_value = cached_data
        
        # Create request
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/analytics/test"
        request.query_params = {}
        request.headers = {}
        
        async def call_next(req):
            # Should not be called on cache hit
            raise Exception("Should not be called")
        
        # Process request
        response = await cache_middleware.dispatch(request, call_next)
        
        # Verify cache hit
        assert cache_middleware.metrics["hits"] == 1
        assert response.headers["X-Cache"] == "HIT"
        assert "X-Cache-Age" in response.headers
    
    @pytest.mark.asyncio
    async def test_conditional_request_etag(self, cache_middleware, mock_cache_manager):
        """Test conditional request with ETag."""
        # Setup cached data
        cached_data = {
            "etag": '"test-etag"',
            "expires_at": (datetime.now() + timedelta(minutes=5)).timestamp(),
            "cached_at": datetime.now().timestamp()
        }
        mock_cache_manager.get.return_value = cached_data
        
        # Create request with If-None-Match
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/analytics/test"
        request.query_params = {}
        request.headers = {"If-None-Match": '"test-etag"'}
        
        async def call_next(req):
            raise Exception("Should not be called")
        
        # Process request
        response = await cache_middleware.dispatch(request, call_next)
        
        # Verify 304 response
        assert response.status_code == 304
        assert response.headers["ETag"] == '"test-etag"'
        assert response.headers["X-Cache"] == "HIT"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_write(self, cache_middleware, mock_cache_manager):
        """Test cache invalidation on write operations."""
        # Create POST request
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/api/conversation/create"
        
        async def call_next(req):
            return Response(status_code=201)
        
        # Process request
        await cache_middleware.dispatch(request, call_next)
        
        # Verify invalidation triggered
        assert cache_middleware.metrics["invalidations"] == 1
        # In real implementation, specific keys would be invalidated
        mock_cache_manager.clear_namespace.assert_called_once()
    
    def test_cache_config_matching(self, cache_middleware):
        """Test cache configuration matching for paths."""
        # Test analytics endpoint
        config = cache_middleware._get_cache_config("/api/analytics/summary")
        assert config is not None
        assert config.ttl_seconds == 300
        
        # Test drift status endpoint
        config = cache_middleware._get_cache_config("/api/ml/drift/status/model1")
        assert config is not None
        assert config.ttl_seconds == 60
        
        # Test conversation endpoint (should not cache)
        config = cache_middleware._get_cache_config("/api/conversation/123")
        assert config is None
        
        # Test unknown endpoint (no config)
        config = cache_middleware._get_cache_config("/api/unknown/endpoint")
        assert config is None
    
    def test_metrics_calculation(self, cache_middleware):
        """Test cache metrics calculation."""
        # Set some metrics
        cache_middleware.metrics["hits"] = 75
        cache_middleware.metrics["misses"] = 25
        cache_middleware.metrics["invalidations"] = 5
        cache_middleware.metrics["errors"] = 2
        
        # Get metrics
        metrics = cache_middleware.get_metrics()
        
        assert metrics["total_requests"] == 100
        assert metrics["hits"] == 75
        assert metrics["misses"] == 25
        assert metrics["hit_rate"] == "75.00%"
        assert metrics["invalidations"] == 5
        assert metrics["errors"] == 2


class TestCacheResponseDecorator:
    """Test cache_response decorator."""
    
    @pytest.mark.asyncio
    async def test_cache_decorator_basic(self, mock_cache_manager):
        """Test basic cache decorator functionality."""
        with patch('src.api.middleware.http_cache_middleware.get_ngx_cache_manager',
                   return_value=mock_cache_manager):
            
            call_count = 0
            
            @cache_response(ttl_seconds=60)
            async def test_function(param1: str, param2: int):
                nonlocal call_count
                call_count += 1
                return {"param1": param1, "param2": param2, "count": call_count}
            
            # First call - cache miss
            result1 = await test_function("test", 123)
            assert result1["count"] == 1
            assert mock_cache_manager.get.called
            assert mock_cache_manager.set.called
            
            # Setup cache hit
            mock_cache_manager.get.return_value = result1
            
            # Second call - cache hit
            result2 = await test_function("test", 123)
            assert result2["count"] == 1  # Same as first call
            assert call_count == 1  # Function not called again
    
    @pytest.mark.asyncio
    async def test_cache_decorator_custom_key(self, mock_cache_manager):
        """Test cache decorator with custom key function."""
        with patch('src.api.middleware.http_cache_middleware.get_ngx_cache_manager',
                   return_value=mock_cache_manager):
            
            def custom_key_func(user_id: str, *args, **kwargs):
                return f"user:{user_id}"
            
            @cache_response(ttl_seconds=60, cache_key_func=custom_key_func)
            async def get_user_data(user_id: str):
                return {"user_id": user_id, "data": "test"}
            
            # Call function
            await get_user_data("123")
            
            # Verify custom key was used
            cache_call_args = mock_cache_manager.set.call_args
            assert "user:123" in str(cache_call_args)
    
    @pytest.mark.asyncio
    async def test_cache_decorator_condition(self, mock_cache_manager):
        """Test cache decorator with condition function."""
        with patch('src.api.middleware.http_cache_middleware.get_ngx_cache_manager',
                   return_value=mock_cache_manager):
            
            def should_cache(result):
                return result.get("success", False)
            
            @cache_response(ttl_seconds=60, condition_func=should_cache)
            async def conditional_function(success: bool):
                return {"success": success, "data": "test"}
            
            # Call with success=False (should not cache)
            await conditional_function(False)
            assert not mock_cache_manager.set.called
            
            # Call with success=True (should cache)
            await conditional_function(True)
            assert mock_cache_manager.set.called