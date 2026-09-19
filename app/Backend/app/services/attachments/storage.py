from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    """Abstract base class for attachment file storage."""

    @abstractmethod
    async def save(self, storage_key: str, data: bytes | BinaryIO) -> int:
        """Save file data to the given storage_key. Returns bytes written."""
        pass

    @abstractmethod
    async def get(self, storage_key: str) -> bytes:
        """Retrieve file bytes by storage_key."""
        pass

    @abstractmethod
    async def delete(self, storage_key: str) -> bool:
        """Delete file at storage_key. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def exists(self, storage_key: str) -> bool:
        """Check if file at storage_key exists."""
        pass
