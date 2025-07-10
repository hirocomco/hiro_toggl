"""
Simple in-memory caching utility for report data.
"""

import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
import hashlib
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        return time.time() > cache_entry['expires_at']
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if self._is_expired(entry):
            del self.cache[key]
            return None
        
        entry['last_accessed'] = time.time()
        entry['access_count'] += 1
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        self.cache[key] = {
            'value': value,
            'created_at': time.time(),
            'expires_at': time.time() + ttl,
            'last_accessed': time.time(),
            'access_count': 1,
            'ttl': ttl
        }
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if self._is_expired(entry)
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        expired_count = self.cleanup_expired()
        
        total_access_count = sum(entry['access_count'] for entry in self.cache.values())
        
        return {
            'total_entries': total_entries,
            'expired_cleaned': expired_count,
            'total_accesses': total_access_count,
            'memory_usage_kb': self._estimate_memory_usage(),
            'oldest_entry': min(
                (entry['created_at'] for entry in self.cache.values()),
                default=None
            ),
            'newest_entry': max(
                (entry['created_at'] for entry in self.cache.values()),
                default=None
            )
        }
    
    def _estimate_memory_usage(self) -> float:
        """Rough estimate of memory usage in KB."""
        try:
            import sys
            total_size = sys.getsizeof(self.cache)
            for key, entry in self.cache.items():
                total_size += sys.getsizeof(key)
                total_size += sys.getsizeof(entry)
                total_size += sys.getsizeof(entry['value'])
            return total_size / 1024
        except Exception:
            return 0.0


# Global cache instance
_report_cache = SimpleCache(default_ttl=300)  # 5 minutes default


def make_cache_key(*args, **kwargs) -> str:
    """
    Create a cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        MD5 hash of serialized arguments
    """
    # Convert arguments to a serializable format
    cache_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())  # Sort for consistent keys
    }
    
    # Serialize and hash
    cache_string = json.dumps(cache_data, sort_keys=True, default=str)
    return hashlib.md5(cache_string.encode()).hexdigest()


def cached_report(ttl: int = 300, key_prefix: str = "report"):
    """
    Decorator for caching report function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            func_key = f"{key_prefix}:{func.__name__}"
            args_key = make_cache_key(*args, **kwargs)
            cache_key = f"{func_key}:{args_key}"
            
            # Try to get from cache
            cached_result = _report_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}, executing function")
            result = func(*args, **kwargs)
            _report_cache.set(cache_key, result, ttl)
            
            return result
        
        # Add cache management methods to the wrapped function
        wrapper.cache_clear = lambda: _report_cache.clear()
        wrapper.cache_delete = lambda *args, **kwargs: _report_cache.delete(
            f"{key_prefix}:{func.__name__}:{make_cache_key(*args, **kwargs)}"
        )
        wrapper.cache_stats = lambda: _report_cache.get_stats()
        
        return wrapper
    return decorator


def invalidate_report_cache(pattern: Optional[str] = None) -> int:
    """
    Invalidate cached reports.
    
    Args:
        pattern: Optional pattern to match cache keys (simple string contains)
        
    Returns:
        Number of cache entries removed
    """
    if pattern is None:
        # Clear all cache
        count = len(_report_cache.cache)
        _report_cache.clear()
        logger.info(f"Cleared all cache entries: {count}")
        return count
    
    # Remove entries matching pattern
    keys_to_remove = [
        key for key in _report_cache.cache.keys()
        if pattern in key
    ]
    
    for key in keys_to_remove:
        _report_cache.delete(key)
    
    logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}")
    return len(keys_to_remove)


def get_cache_info() -> Dict[str, Any]:
    """Get information about the report cache."""
    return _report_cache.get_stats()


class ReportCacheManager:
    """Manager for report-specific cache operations."""
    
    @staticmethod
    def invalidate_workspace_reports(workspace_id: int) -> int:
        """Invalidate all reports for a specific workspace."""
        return invalidate_report_cache(f"workspace_id:{workspace_id}")
    
    @staticmethod
    def invalidate_client_reports(client_id: int) -> int:
        """Invalidate all reports for a specific client."""
        return invalidate_report_cache(f"client_id:{client_id}")
    
    @staticmethod
    def invalidate_member_reports(member_id: int) -> int:
        """Invalidate all reports for a specific member."""
        return invalidate_report_cache(f"member_id:{member_id}")
    
    @staticmethod
    def invalidate_date_range_reports(start_date: str, end_date: str) -> int:
        """Invalidate reports for a specific date range."""
        count = 0
        count += invalidate_report_cache(f"start_date:{start_date}")
        count += invalidate_report_cache(f"end_date:{end_date}")
        return count
    
    @staticmethod
    def cleanup_expired() -> int:
        """Clean up expired cache entries."""
        return _report_cache.cleanup_expired()
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache statistics."""
        return _report_cache.get_stats()


# Cache warming functions
def warm_common_reports(workspace_id: int) -> None:
    """
    Pre-warm cache with common report queries.
    
    Args:
        workspace_id: Workspace ID to warm reports for
    """
    from datetime import date, timedelta
    
    logger.info(f"Warming cache for workspace {workspace_id}")
    
    # Common date ranges to pre-load
    today = date.today()
    date_ranges = [
        (today - timedelta(days=7), today),    # Last 7 days
        (today - timedelta(days=30), today),   # Last 30 days
        (today.replace(day=1), today),         # This month
    ]
    
    # This would typically call your report functions
    # For now, just log the intent
    for start_date, end_date in date_ranges:
        logger.debug(f"Would warm cache for {workspace_id} from {start_date} to {end_date}")


def schedule_cache_cleanup():
    """Schedule periodic cache cleanup (would be called by a background task)."""
    logger.info("Running scheduled cache cleanup")
    expired_count = _report_cache.cleanup_expired()
    
    # Log cache statistics
    stats = _report_cache.get_stats()
    logger.info(f"Cache cleanup complete. Removed {expired_count} expired entries. "
               f"Current stats: {stats['total_entries']} entries, "
               f"{stats['memory_usage_kb']:.1f}KB")
    
    return expired_count