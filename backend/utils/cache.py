import time
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

class SimpleCache:
    """
    A simple in-memory TTL cache to improve analytical report performance.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            item = self._cache[key]
            if time.time() < item['expires']:
                logger.info(f"Cache HIT for key: {key}")
                return item['data']
            else:
                logger.info(f"Cache EXPIRED for key: {key}")
                del self._cache[key]
        else:
            logger.info(f"Cache MISS for key: {key}")
        return None

    def set(self, key: str, data: Any, ttl: int = 300):
        """
        Set data in cache with a default TTL of 5 minutes (300 seconds).
        """
        self._cache[key] = {
            'data': data,
            'expires': time.time() + ttl
        }
        logger.info(f"Cache SET for key: {key} (TTL: {ttl}s)")

    def clear(self, pattern: Optional[str] = None):
        """
        Clear the cache. If pattern is provided, clears keys starting with it.
        """
        if pattern:
            keys_to_del = [k for k in self._cache.keys() if k.startswith(pattern)]
            for k in keys_to_del:
                del self._cache[k]
            logger.info(f"Cache CLEARED for pattern: {pattern}")
        else:
            self._cache.clear()
            logger.info("Cache CLEARED completely")

# Global singleton for analytical data
analytics_cache = SimpleCache()
