import asyncio
from functools import wraps
import logging
from typing import Type, Tuple, Callable, Any
import validators
from fastapi import HTTPException

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleFetchError(Exception):
    """Raised when article fetching fails.
    
    This exception is raised when there are issues fetching an article,
    such as network errors, 404 errors, or invalid content.
    """
    pass

class RetryableError(Exception):
    """Base class for errors that can be retried."""
    pass

class NetworkError(RetryableError):
    """Raised when network operations fail"""
    pass

class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    pass

def validate_url(url: str) -> bool:
    """
    Validate URL format and domain.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if URL is valid
        
    Raises:
        ValueError: If URL is invalid
    """
    # Check URL format
    if not validators.url(url):
        raise ValueError("Invalid URL format")
    
    # Check protocol
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must use HTTP/HTTPS protocol")
    
    # Check for suspicious patterns
    suspicious_patterns = ['.exe', '.dll', '.bat', '.sh', 'javascript:', 'file:']
    if any(pattern in url.lower() for pattern in suspicious_patterns):
        raise ValueError("URL contains suspicious patterns")
    
    # Whitelist of medical/academic domains
    allowed_domains = [
        'nejm.org', 'mayoclinic.org', 'health.harvard.edu',
        'nih.gov', 'who.int', 'cdc.gov', 'clinicaltrials.gov',
        'pubmed.ncbi.nlm.nih.gov', 'medlineplus.gov'
    ]
    
    if not any(domain in url.lower() for domain in allowed_domains):
        raise ValueError("Domain not in whitelist of medical/academic sources")
    
    return True

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (RetryableError,)
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        retryable_exceptions: Tuple of exception types to retry on
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            raise last_exception
        
        return wrapper
    
    return decorator

def handle_api_error(error: Exception) -> HTTPException:
    """
    Convert exceptions to appropriate HTTP responses.
    
    Args:
        error: The exception to handle
        
    Returns:
        HTTPException: Appropriate HTTP exception
    """
    if isinstance(error, ValueError):
        return HTTPException(status_code=400, detail=str(error))
    elif isinstance(error, ArticleFetchError):
        return HTTPException(status_code=404, detail=str(error))
    elif isinstance(error, RateLimitError):
        return HTTPException(status_code=429, detail=str(error))
    elif isinstance(error, NetworkError):
        return HTTPException(status_code=503, detail=str(error))
    else:
        logger.error(f"Unhandled error: {str(error)}")
        return HTTPException(status_code=500, detail="Internal server error") 