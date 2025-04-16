from typing import Any, Dict, Optional, Callable
import time
from datetime import datetime, timedelta
import logging
from functools import wraps
from error_handlers import RateLimitError
import json
from fastapi import Request
import aioredis
import hashlib
import redis.asyncio as redis

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter using a token bucket algorithm"""
    
    def __init__(self, redis_url: str, max_requests: int = 60, time_window: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            redis_url: Redis connection URL
            max_requests: Maximum number of requests allowed in the time window
            time_window: Time window in seconds
        """
        self.redis_client = redis.from_url(redis_url)
        self.max_requests = max_requests
        self.time_window = time_window

    async def _cleanup_old_requests(self, key: str) -> None:
        """Remove requests older than the time window."""
        current_time = time.time()
        min_time = current_time - self.time_window
        await self.redis_client.zremrangebyscore(key, 0, min_time)

    async def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if the client has exceeded their rate limit.
        
        Args:
            client_id: Unique identifier for the client (e.g., IP address)
            
        Returns:
            bool: True if the request is allowed, False otherwise
            
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        key = f"rate_limit:{client_id}"
        current_time = time.time()
        
        # Use Redis pipeline for atomic operations
        async with self.redis_client.pipeline() as pipe:
            # Remove old requests
            await self._cleanup_old_requests(key)
            
            # Add current request timestamp
            await pipe.zadd(key, {str(current_time): current_time})
            
            # Get count of recent requests
            request_count = await pipe.zcard(key)
            
            # Set expiry on the key
            await pipe.expire(key, self.time_window)
            
            # Execute pipeline
            await pipe.execute()

        if request_count > self.max_requests:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            raise RateLimitError(
                f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.time_window} seconds."
            )
        
        return True

class Cache:
    """Caching implementation using Redis"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost",
        default_ttl: int = 3600,  # 1 hour
        redis_prefix: str = "cache:"
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_prefix = redis_prefix
        self._redis: Optional[aioredis.Redis] = None
    
    async def init_redis(self):
        """Initialize Redis connection"""
        if self._redis is None:
            self._redis = await aioredis.from_url(self.redis_url)
    
    async def close(self):
        """Close Redis connection"""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
    
    def get_cache_key(self, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{self.redis_prefix}{key}"
    
    def generate_key(self, func_name: str, args: tuple, kwargs: Dict) -> str:
        """Generate a unique cache key based on function name and arguments"""
        key_parts = [func_name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        await self.init_redis()
        return await self._redis.get(self.get_cache_key(key))
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache"""
        await self.init_redis()
        await self._redis.set(
            self.get_cache_key(key),
            json.dumps(value),
            ex=ttl or self.default_ttl
        )
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        await self.init_redis()
        await self._redis.delete(self.get_cache_key(key))

def cached(ttl: int = 3600):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time to live in seconds for cached results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = None
            for arg in args:
                if hasattr(arg, 'client'):
                    request = arg
                    break
            
            if not request:
                return await func(*args, **kwargs)
            
            # Get Redis client from app state
            redis_client = getattr(request.app.state, 'redis_client', None)
            if not redis_client:
                return await func(*args, **kwargs)
            
            # Create cache key from function name and arguments
            cache_key = f"cache:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get cached result
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return cached_result
            
            # Get fresh result
            result = await func(*args, **kwargs)
            
            # Cache the result
            await redis_client.setex(cache_key, ttl, str(result))
            
            return result
        
        return wrapper
    
    return decorator

def rate_limit(func: Callable) -> Callable:
    """
    Decorator to apply rate limiting to a function.
    Must be used with FastAPI dependency injection to get the request object.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request object from kwargs
        request = kwargs.get('request')
        if not request:
            for arg in args:
                if hasattr(arg, 'client'):
                    request = arg
                    break
        
        if not request:
            raise ValueError("Could not find request object")
        
        # Get rate limiter from app state
        rate_limiter = getattr(request.app.state, 'rate_limiter', None)
        if not rate_limiter:
            logger.warning("Rate limiter not initialized in app state")
            return await func(*args, **kwargs)
        
        # Check rate limit
        client_id = request.client.host
        await rate_limiter.check_rate_limit(client_id)
        
        return await func(*args, **kwargs)
    
    return wrapper 