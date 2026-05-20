"""
Retry utility - Exponential backoff retry decorator for API calls
"""

import time
import functools
from typing import Tuple, Type

from .logger import get_logger

logger = get_logger('memecoin.utils.retry')


def retry(max_attempts: int = 3, delay: float = 1.0,
          backoff_factor: float = 2.0,
          exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch
        
    Example:
        @retry(max_attempts=3, delay=1.0)
        def fetch_data():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"[{func.__name__}] Failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_async(max_attempts: int = 3, delay: float = 1.0,
                backoff_factor: float = 2.0,
                exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    Async retry decorator with exponential backoff
    
    Example:
        @retry_async(max_attempts=3)
        async def fetch_data():
            ...
    """
    import asyncio
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"[{func.__name__}] Failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
            
            raise last_exception
        
        return wrapper
    return decorator
