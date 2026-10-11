"""
Filesystem utilities for file operations.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class FileSystemHelper:
    """Helper for filesystem operations."""

    @staticmethod
    def format_size(num_bytes: int, precision: int = 1) -> str:
        """Format a byte count for display (B, KB, MB, GB).

        Args:
            num_bytes: Size in bytes (negative values are formatted with a sign).
            precision: Decimal places for KB and above.

        Returns:
            Human-readable size such as ``"2.4 MB"``.
        """
        sign = "-" if num_bytes < 0 else ""
        value = float(abs(num_bytes))
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{sign}{int(value)} B"
                return f"{sign}{value:.{precision}f} {unit}"
            value /= 1024
        return f"{sign}{value:.{precision}f} TB"

    @staticmethod
    def get_file_size_mb(path: Path) -> float:
        """Get file size in megabytes."""
        return path.stat().st_size / (1024 * 1024)

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists, create if not."""
        Path(path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_unique_filename(path: Path) -> Path:
        """Return ``path`` if free, else ``stem_1``, ``stem_2``, ... in the same folder."""
        path = Path(path)
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
        """Copy a file, optionally refusing to overwrite."""
        try:
            if dst.exists() and not overwrite:
                logger.warning(f"File exists, not overwriting: {dst}")
                return False
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.debug(f"Copied {src} -> {dst}")
            return True
        except Exception as exc:
            logger.error(f"Error copying file: {exc}")
            return False

    @staticmethod
    def delete_file(path: Path) -> bool:
        """Delete a file if it exists."""
        try:
            if path.exists():
                path.unlink()
                logger.debug(f"Deleted {path}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Error deleting file: {exc}")
            return False

    @staticmethod
    def is_writable_directory(path: Path) -> bool:
        """Check that ``path`` is a directory we can create a file in."""
        path = Path(path)
        if not path.is_dir():
            return False
        probe = path / ".squash_write_test"
        try:
            probe.touch()
            probe.unlink()
            return True
        except OSError:
            return False

    @staticmethod
    def open_in_file_manager(path: Path) -> bool:
        """Reveal ``path`` in the OS file manager (Explorer on Windows).

        For a file, the containing folder is opened with the file selected.

        Returns:
            True if a file manager was launched.
        """
        path = Path(path)
        try:
            if sys.platform == "win32":
                if path.is_file():
                    subprocess.Popen(["explorer", "/select,", str(path)])
                else:
                    os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                args = ["open", "-R", str(path)] if path.is_file() else ["open", str(path)]
                subprocess.Popen(args)
            else:
                target = path if path.is_dir() else path.parent
                subprocess.Popen(["xdg-open", str(target)])
            return True
        except Exception as exc:
            logger.error(f"Could not open file manager for {path}: {exc}")
            return False

    @staticmethod
    def get_app_data_dir() -> Path:
        """Return the per-user application data directory (``%APPDATA%\\Squash``)."""
        if os.name == "nt":
            app_data = os.environ.get("APPDATA")
            base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
            return base / "Squash"
        return Path.home() / ".squash"
