import os
import aiofiles
from pathlib import Path
from app.core.config import settings


class StorageService:
    """
    Abstraction layer for file storage.
    Currently implements local filesystem storage.
    Can be extended for S3, GCS, Azure Blob, etc.
    """

    def __init__(self):
        self.base_path = Path(settings.UPLOAD_DIR)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save_file(
        self,
        content: bytes,
        filename: str,
        subdirectory: str = ""
    ) -> str:
        """Save file and return the full path."""
        if subdirectory:
            dir_path = self.base_path / subdirectory
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            dir_path = self.base_path

        file_path = dir_path / filename

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        return str(file_path)

    async def read_file(self, file_path: str) -> bytes:
        """Read and return file contents."""
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        try:
            os.remove(file_path)
            return True
        except OSError:
            return False

    def get_file_path(self, filename: str, subdirectory: str = "") -> str:
        """Get the full path for a file."""
        if subdirectory:
            return str(self.base_path / subdirectory / filename)
        return str(self.base_path / filename)

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        return os.path.exists(file_path)
