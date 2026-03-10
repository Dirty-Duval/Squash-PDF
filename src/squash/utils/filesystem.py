"""
Filesystem utilities for file operations.
"""

from pathlib import Path
from typing import Optional
import shutil
import logging

logger = logging.getLogger(__name__)


class FileSystemHelper:
    """Helper for filesystem operations."""

    @staticmethod
    def get_file_size_mb(path: Path) -> float:
        """
        Get file size in megabytes.

        Args:
            path: File path

        Returns:
            Size in MB
        """
        return path.stat().st_size / (1024 * 1024)

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """
        Ensure directory exists, create if not.

        Args:
            path: Directory path
        """
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_unique_filename(path: Path) -> Path:
        """
        Get unique filename if file already exists.

        Args:
            path: Desired file path

        Returns:
            Unique file path (adds _1, _2, etc if needed)
        """
        if not path.exists():
            return path

        counter = 1
        while True:
            new_path = path.parent / f"{path.stem}_{counter}{path.suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    @staticmethod
    def copy_file(src: Path, dst: Path, overwrite: bool = False) -> bool:
        """
        Copy file safely.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Allow overwriting existing file

        Returns:
            True if successful, False otherwise
        """
        try:
            if dst.exists() and not overwrite:
                logger.warning(f"File exists, not overwriting: {dst}")
                return False

            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.debug(f"Copied {src} -> {dst}")
            return True

        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False

    @staticmethod
    def delete_file(path: Path) -> bool:
        """
        Delete file safely.

        Args:
            path: File path to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if path.exists():
                path.unlink()
                logger.debug(f"Deleted {path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    @staticmethod
    def get_app_data_dir() -> Path:
        """
        Get application data directory.

        Returns:
            Path to AppData/Squash directory (Windows)
        """
        import os

        if os.name == "nt":  # Windows
            app_data = Path(os.environ.get("APPDATA", ""))
            return app_data / "Squash"
        else:
            # Fallback for development on other platforms
            return Path.home() / ".squash"
