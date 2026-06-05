"""
Async Utilities - Bridge sync to async operations

Provides utilities for running blocking IO operations in async contexts,
and adding async versions of common functions.
"""

import asyncio
from typing import Callable, Any, Optional, TypeVar, Coroutine
from functools import wraps
import threading

T = TypeVar('T')


def run_in_thread(executor: Optional[threading.ThreadPoolExecutor] = None):
    """
    Decorator to run blocking sync functions in a thread pool.
    
    Usage:
        @run_in_thread()
        def blocking_io_operation():
            # sync code here
            pass
        
        # In async context:
        result = await blocking_io_operation()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
        return wrapper
    return decorator


async def run_sync_async(sync_func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in a thread pool.
    
    Usage:
        result = await run_sync_async(blocking_http_call, url)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: sync_func(*args, **kwargs))


class AsyncIOMixin:
    """
    Mixin to add async versions of common IO operations.
    
    Usage:
        class MyClient(AsyncIOMixin):
            def fetch_sync(self, url):
                # sync HTTP call
                pass
            
            async_fetch = asyncify(fetch_sync)
    """
    @staticmethod
    def asyncify(sync_method: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
        """Convert a sync method to async using run_in_executor"""
        @wraps(sync_method)
        async def wrapper(self, *args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: sync_method(self, *args, **kwargs))
        return wrapper


# Common async HTTP client using aiohttp (if available)
# Falls back to threaded urllib if aiohttp not installed

_aiohttp_available = False
try:
    import aiohttp
    _aiohttp_available = True
except ImportError:
    pass


async def async_http_get(url: str, headers: Optional[dict] = None, 
                          timeout: int = 30) -> dict:
    """
    Async HTTP GET request.
    
    Requires aiohttp to be installed: pip install aiohttp
    
    Returns:
        JSON response as dict
    """
    if not _aiohttp_available:
        raise ImportError(
            "aiohttp not installed. Install with: pip install aiohttp "
            "or use run_sync_async(urllib_request, ...)"
        )
    
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.get(url, headers=headers or {}) as response:
            return await response.json()


async def async_http_post(url: str, data: Optional[dict] = None, 
                          json: Optional[dict] = None,
                          headers: Optional[dict] = None,
                          timeout: int = 30) -> dict:
    """
    Async HTTP POST request.
    
    Requires aiohttp to be installed: pip install aiohttp
    
    Returns:
        JSON response as dict
    """
    if not _aiohttp_available:
        raise ImportError(
            "aiohttp not installed. Install with: pip install aiohttp "
            "or use run_sync_async(urllib_request, ...)"
        )
    
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.post(url, data=data, json=json, headers=headers or {}) as response:
            return await response.json()
