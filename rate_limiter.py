from typing import Any, Dict, Optional
import time
from datetime import datetime, timedelta
import logging
from functools import wraps
from error_handlers import RateLimitError
import json
from fastapi import Request
import aioredis
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter using a token bucket algorithm"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost",
        max_requests: int = 60,
        time_window: int = 60,  # in seconds
        redis_prefix: str = "rate_limit:"
    ):
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.time_window = time_window
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
    
    def get_key(self, identifier: str) -> str:
        """Get Redis key for rate limiting"""
        return f"{self.redis_prefix}{identifier}"
    
    async def is_rate_limited(self, identifier: str) -> bool:
        """
        Check if the request should be rate limited.
        
        Args:
            identifier: Unique identifier for the client (e.g., IP address)
            
        Returns:
            bool: True if rate limited, False otherwise
            
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        await self.init_redis()
        key = self.get_key(identifier)
        
        async with self._redis.pipeline() as pipe:
            now = int(time.time())
            window_start = now - self.time_window
            
            # Remove old requests
            await pipe.zremrangebyscore(key, 0, window_start)
            # Count recent requests
            recent_requests = await pipe.zcount(key, window_start, now)
            
            if recent_requests >= self.max_requests:
                ttl = await self._redis.ttl(key)
                raise RateLimitError(
                    f"Rate limit exceeded. Try again in {ttl} seconds."
                )
            
            # Add new request
            await pipe.zadd(key, {str(now): now})
            # Set expiry
            await pipe.expire(key, self.time_window)
            
            await pipe.execute()
        
        return False

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

def cached(ttl: Optional[int] = None):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds for cached results
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = Cache()
            key = cache.generate_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_value = await cache.get(key)
            if cached_value is not None:
                logger.info(f"Cache hit for key: {key}")
                return json.loads(cached_value)
            
            # If not in cache, execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(key, result, ttl)
            logger.info(f"Cached result for key: {key}")
            
            return result
        return wrapper
    return decorator

def rate_limit(
    max_requests: int = 60,
    time_window: int = 60
):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        time_window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            limiter = RateLimiter(
                max_requests=max_requests,
                time_window=time_window
            )
            
            # Use client IP as identifier
            client_ip = request.client.host
            await limiter.is_rate_limited(client_ip)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator 