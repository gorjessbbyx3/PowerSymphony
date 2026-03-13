"""
LLM Response Cache — thread-safe, hash-based cache for deterministic model calls.

Saves re-invoking the LLM when the exact same conversation + params are repeated.
Useful for workflow retries, debugging, and repeated sub-workflows.

Usage:
    from utils.llm_cache import llm_cache

    cached = llm_cache.get(key)
    if cached is None:
        response = call_model(...)
        llm_cache.set(key, response)
"""

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("WareHouse/.llm_cache")
_DEFAULT_MAX_MEMORY_ENTRIES = 512
_DEFAULT_MAX_AGE_SECONDS = 3600 * 24  # 24 hours


def _stable_hash(data: Any) -> str:
    """Return a stable SHA-256 hex digest of arbitrary data."""
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class LLMCache:
    """Thread-safe in-memory LRU cache with optional disk backing."""

    def __init__(
        self,
        max_entries: int = _DEFAULT_MAX_MEMORY_ENTRIES,
        max_age: float = _DEFAULT_MAX_AGE_SECONDS,
        persist: bool = True,
    ) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._access: Dict[str, float] = {}             # key -> last_access
        self._max_entries = max_entries
        self._max_age = max_age
        self._persist = persist
        self._hits = 0
        self._misses = 0
        if persist:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def make_key(
        self,
        model_name: str,
        provider: str,
        messages: list,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        extra: Optional[Dict] = None,
    ) -> str:
        """Build a deterministic cache key from call parameters."""
        payload = {
            "model": model_name,
            "provider": provider,
            "messages": self._serialize_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            **(extra or {}),
        }
        return _stable_hash(payload)

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or None if not found / expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                # Try disk
                if self._persist:
                    entry = self._load_from_disk(key)
                    if entry:
                        self._store[key] = entry
                if entry is None:
                    self._misses += 1
                    return None

            value, ts = entry
            if time.time() - ts > self._max_age:
                self._evict(key)
                self._misses += 1
                return None

            self._access[key] = time.time()
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache."""
        with self._lock:
            self._evict_lru_if_needed()
            ts = time.time()
            self._store[key] = (value, ts)
            self._access[key] = ts
            if self._persist:
                self._save_to_disk(key, value, ts)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._evict(key)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._access.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total else 0.0,
                "entries": len(self._store),
            }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _serialize_messages(self, messages: list) -> list:
        """Convert messages to a stable serializable form."""
        result = []
        for msg in messages:
            if hasattr(msg, "role") and hasattr(msg, "blocks"):
                text_parts = []
                for block in (msg.blocks or []):
                    if hasattr(block, "text") and block.text:
                        text_parts.append(block.text)
                result.append({"role": str(msg.role), "text": "\n".join(text_parts)})
            elif isinstance(msg, dict):
                result.append(msg)
            else:
                result.append(str(msg))
        return result

    def _evict(self, key: str) -> None:
        self._store.pop(key, None)
        self._access.pop(key, None)
        if self._persist:
            cache_file = _CACHE_DIR / f"{key}.json"
            cache_file.unlink(missing_ok=True)

    def _evict_lru_if_needed(self) -> None:
        if len(self._store) < self._max_entries:
            return
        # Evict the least-recently-used entry
        lru_key = min(self._access, key=lambda k: self._access[k])
        self._evict(lru_key)

    def _save_to_disk(self, key: str, value: Any, ts: float) -> None:
        try:
            cache_file = _CACHE_DIR / f"{key}.json"
            payload = {"ts": ts, "value": value}
            cache_file.write_text(json.dumps(payload, default=str))
        except Exception as exc:
            logger.debug("LLM cache disk write failed: %s", exc)

    def _load_from_disk(self, key: str) -> Optional[Tuple[Any, float]]:
        try:
            cache_file = _CACHE_DIR / f"{key}.json"
            if not cache_file.exists():
                return None
            payload = json.loads(cache_file.read_text())
            return payload["value"], payload["ts"]
        except Exception:
            return None


# Global singleton
llm_cache = LLMCache(
    max_entries=int(os.getenv("LLM_CACHE_MAX_ENTRIES", "512")),
    max_age=float(os.getenv("LLM_CACHE_MAX_AGE_SECONDS", str(3600 * 24))),
    persist=os.getenv("LLM_CACHE_PERSIST", "true").lower() == "true",
)
