from functools import wraps
import time
from typing import Callable, TypeVar, Any
import logging
from fastapi import HTTPException
import validators
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T')

class RetryableError(Exception):
    """Base class for errors that can be retried"""
    pass

class RateLimitError(RetryableError):
    """Raised when rate limit is hit"""
    pass

class NetworkError(RetryableError):
    """Raised when network issues occur"""
    pass

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1,
    max_delay: float = 10,
    backoff_factor: float = 2,
    retryable_exceptions: tuple = (RetryableError,)
) -> Callable:
    """
    Decorator that implements retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        retryable_exceptions: Tuple of exceptions that should trigger a retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None
            
            for retry in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if retry == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded: {str(e)}")
                        raise
                    
                    logger.warning(
                        f"Retry {retry + 1}/{max_retries} after error: {str(e)}. "
                        f"Waiting {delay} seconds..."
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            raise last_exception  # This line should never be reached
            
        return wrapper
    return decorator

def validate_url(url: str) -> bool:
    """
    Validates a URL for safety and format.
    
    Args:
        url: URL string to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
        
    Raises:
        ValueError: If URL is invalid with specific reason
    """
    # Basic URL format validation
    if not validators.url(url):
        raise ValueError("Invalid URL format")
    
    # Parse URL for additional checks
    parsed = urlparse(url)
    
    # Check scheme
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("URL must use HTTP or HTTPS protocol")
    
    # Check for suspicious or malicious patterns
    suspicious_patterns = [
        'javascript:', 'data:', 'vbscript:',  # Potential XSS vectors
        '.exe', '.dll', '.bat', '.cmd',       # Executable files
        'file://', 'ftp://'                   # Unwanted protocols
    ]
    
    if any(pattern in url.lower() for pattern in suspicious_patterns):
        raise ValueError("URL contains suspicious patterns")
    
    # Whitelist of allowed medical/academic domains
    allowed_domains = [
        'nejm.org', 'pubmed.ncbi.nlm.nih.gov', 'mayoclinic.org',
        'health.harvard.edu', 'cdc.gov', 'who.int', 'nih.gov',
        'medlineplus.gov', 'clinicaltrials.gov', 'jamanetwork.com',
        'thelancet.com', 'bmj.com', 'sciencedirect.com'
    ]
    
    # Check if domain is in whitelist
    if not any(domain in parsed.netloc.lower() for domain in allowed_domains):
        raise ValueError(
            f"Domain not in whitelist. Allowed domains: {', '.join(allowed_domains)}"
        )
    
    return True

def handle_api_error(error: Exception) -> HTTPException:
    """
    Converts various exceptions to appropriate HTTPException responses.
    
    Args:
        error: The exception to handle
        
    Returns:
        HTTPException: Appropriate HTTP error response
    """
    if isinstance(error, ValueError):
        return HTTPException(status_code=400, detail=str(error))
    elif isinstance(error, RateLimitError):
        return HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    elif isinstance(error, NetworkError):
        return HTTPException(
            status_code=503,
            detail="Service temporarily unavailable due to network issues."
        )
    elif isinstance(error, RetryableError):
        return HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again."
        )
    else:
        logger.error(f"Unexpected error: {str(error)}")
        return HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        ) 