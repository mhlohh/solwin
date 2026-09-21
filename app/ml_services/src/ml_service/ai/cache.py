"""Disk-backed embedding cache for the AI provider layer.

Cache keys are SHA-256 hashes of (model_name + normalized_text).
No raw API credentials are stored in cache metadata.

Thread safety: a single ``threading.Lock`` guards reads and writes.
"""

import hashlib
import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_PATH = Path("models/embedding_cache.json")


class EmbeddingCache:
    """A simple, persistent embedding cache backed by a JSON file.

    Embeddings are stored as ``{cache_key: [float, ...]}``.  The cache is
    loaded once on construction and flushed to disk after every write.
    """

    def __init__(self, cache_path: Path | None = None) -> None:
        self._path = cache_path or _DEFAULT_CACHE_PATH
        self._lock = threading.Lock()
        self._store: dict[str, list[float]] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, model_name: str, text: str) -> list[float] | None:
        """Return a cached embedding or ``None`` on a cache miss."""
        key = self._make_key(model_name, text)
        with self._lock:
            return self._store.get(key)

    def set(self, model_name: str, text: str, embedding: list[float]) -> None:
        """Store an embedding and persist the cache to disk."""
        key = self._make_key(model_name, text)
        with self._lock:
            self._store[key] = embedding
            self._flush()

    def size(self) -> int:
        """Return the number of cached embeddings."""
        with self._lock:
            return len(self._store)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(model_name: str, text: str) -> str:
        """Deterministic cache key — never contains API credentials."""
        payload = f"{model_name}::{text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load(self) -> dict[str, list[float]]:
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data  # type: ignore[return-value]
        except Exception as exc:
            logger.warning("EmbeddingCache: failed to load cache from %s: %s", self._path, exc)
        return {}

    def _flush(self) -> None:
        """Write cache to disk; called while holding ``self._lock``."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._store, separators=(",", ":")),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("EmbeddingCache: failed to flush cache to %s: %s", self._path, exc)
