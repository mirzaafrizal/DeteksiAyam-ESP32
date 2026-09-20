from typing import Any, Optional


class InMemoryCache:
    """
    Simple in-memory cache used as a fallback when MongoDB is unavailable.
    Thread-safe enough for async FastAPI use since Python's GIL protects
    dict operations, and async code runs on a single thread by default.
    """

    def __init__(self) -> None:
        self._store: dict = {}

    def set(self, key: str, value: Any) -> None:
        """Store a value under the given key."""
        self._store[key] = value

    def get(self, key: str) -> Optional[Any]:
        """Return the value for key, or None if the key does not exist."""
        return self._store.get(key, None)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._store.clear()


# Singleton instance shared across the application
cache = InMemoryCache()
