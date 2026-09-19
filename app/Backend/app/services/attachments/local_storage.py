from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.services.attachments.storage import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for attachments.

    Uses ATTACHMENTS_STORAGE_DIR from environment/settings.
    Prevents path traversal outside root storage directory.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            base_dir = settings.ATTACHMENTS_STORAGE_DIR
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        """Resolve storage_key safely within base_dir, preventing path traversal."""
        # Normalize separators
        clean_key = storage_key.strip("/\\")
        target_path = (self.base_dir / clean_key).resolve()
        if not target_path.is_relative_to(self.base_dir):
            raise ValueError(f"Invalid storage key path traversal: {storage_key}")
        return target_path

    async def save(self, storage_key: str, data: bytes | BinaryIO) -> int:
        target_path = self._resolve_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, (bytes, bytearray)):
            target_path.write_bytes(data)
            return len(data)
        else:
            content = data.read()
            target_path.write_bytes(content)
            return len(content)

    async def get(self, storage_key: str) -> bytes:
        target_path = self._resolve_path(storage_key)
        if not target_path.is_file():
            raise FileNotFoundError(
                f"Attachment not found at storage key: {storage_key}"
            )
        return target_path.read_bytes()

    async def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        if target_path.is_file():
            target_path.unlink()
            return True
        return False

    async def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        return target_path.is_file()


_default_storage_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    """Dependency / getter for storage backend."""
    global _default_storage_backend
    if _default_storage_backend is None:
        _default_storage_backend = LocalStorageBackend()
    return _default_storage_backend
