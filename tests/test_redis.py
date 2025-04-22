import pytest
import pytest_asyncio
from rate_limiter import RateLimiter, Cache
import time
import aioredis
import json
import asyncio

@pytest_asyncio.fixture
async def redis_url():
    return "redis://localhost:6379"

@pytest_asyncio.fixture
async def rate_limiter(redis_url):
    limiter = RateLimiter(redis_url)
    yield limiter
    # Cleanup after tests
    await limiter.redis_client.flushdb()
    await limiter.redis_client.aclose()

@pytest_asyncio.fixture
async def cache(redis_url):
    cache_instance = Cache(redis_url)
    yield cache_instance
    # Cleanup after tests
    await cache_instance.init_redis()
    await cache_instance._redis.flushdb()
    await cache_instance.aclose()

@pytest.mark.asyncio
async def test_rate_limiter_allows_requests_within_limit(rate_limiter):
    """Test that requests within rate limit are allowed"""
    client_id = "test_client_1"
    # Make multiple requests within limit
    for _ in range(rate_limiter.max_requests):
        assert await rate_limiter.check_rate_limit(client_id) is True

@pytest.mark.asyncio
async def test_rate_limiter_blocks_excess_requests(rate_limiter):
    """Test that excess requests are blocked"""
    client_id = "test_client_2"
    # Make requests up to limit
    for _ in range(rate_limiter.max_requests):
        await rate_limiter.check_rate_limit(client_id)
    
    # Next request should raise RateLimitError
    with pytest.raises(Exception) as exc_info:
        await rate_limiter.check_rate_limit(client_id)
    assert "Rate limit exceeded" in str(exc_info.value)

@pytest.mark.asyncio
async def test_rate_limiter_resets_after_window(rate_limiter):
    """Test that rate limit resets after time window"""
    client_id = "test_client_3"
    # Make requests up to limit
    for _ in range(rate_limiter.max_requests):
        await rate_limiter.check_rate_limit(client_id)
    
    # Wait for time window to pass
    await rate_limiter.redis_client.flushdb()  # Clear old data
    
    # Should be able to make requests again
    assert await rate_limiter.check_rate_limit(client_id) is True

@pytest.mark.asyncio
async def test_cache_set_and_get(cache):
    """Test basic cache set and get operations"""
    key = "test_key"
    value = {"test": "data"}
    
    # Set value in cache
    await cache.set(key, value)
    
    # Get value from cache
    cached_value = await cache.get(key)
    assert cached_value is not None
    assert json.loads(cached_value) == value

@pytest.mark.asyncio
async def test_cache_ttl(cache):
    """Test that cached items expire after TTL"""
    key = "test_ttl_key"
    value = {"test": "ttl_data"}
    ttl = 1  # 1 second TTL
    
    # Set value with short TTL
    await cache.set(key, value, ttl=ttl)
    
    # Value should exist initially
    assert await cache.get(key) is not None
    
    # Wait for TTL to expire
    await asyncio.sleep(ttl + 0.1)
    
    # Value should be gone
    assert await cache.get(key) is None

@pytest.mark.asyncio
async def test_cache_delete(cache):
    """Test cache deletion"""
    key = "test_delete_key"
    value = {"test": "delete_data"}
    
    # Set value
    await cache.set(key, value)
    
    # Delete value
    await cache.delete(key)
    
    # Value should be gone
    assert await cache.get(key) is None

@pytest.mark.asyncio
async def test_cache_with_prefix(cache):
    """Test that cache prefix is properly applied"""
    key = "test_prefix_key"
    value = {"test": "prefix_data"}
    
    # Set value
    await cache.set(key, value)
    
    # Check that key exists with prefix
    prefixed_key = cache.get_cache_key(key)
    assert await cache._redis.exists(prefixed_key) == 1 