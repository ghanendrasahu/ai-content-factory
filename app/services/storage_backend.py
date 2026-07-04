from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings
from app.core.paths import BASE_DIR, ensure_inside_directory


class StorageBackend(ABC):
    @abstractmethod
    def exists(self, path: str | Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def url_for(self, path: str | Path) -> str:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    def exists(self, path: str | Path) -> bool:
        return Path(path).is_file()

    def url_for(self, path: str | Path) -> str:
        resolved = ensure_inside_directory(Path(path), BASE_DIR)
        return "/" + resolved.relative_to(BASE_DIR).as_posix()


def get_storage_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND != "local":
        raise ValueError(f"Unsupported storage backend: {settings.STORAGE_BACKEND}")
    return LocalStorage()
