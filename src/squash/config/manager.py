"""
Configuration management for application settings.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from .. import __version__
from ..utils.filesystem import FileSystemHelper

logger = logging.getLogger(__name__)

VALID_THEMES = ("system", "light", "dark")
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
SAME_FOLDER = "same_folder"


@dataclass
class Settings:
    """Application settings persisted to ``settings.json``."""

    version: str = __version__

    # General
    default_preset: str = "medium"
    output_location: str = SAME_FOLDER  # SAME_FOLDER or an absolute folder path
    output_naming_pattern: str = "{filename}_compressed.pdf"
    theme: str = "system"  # light, dark, system

    # Advanced
    ghostscript_path: Optional[str] = None
    compression_timeout: int = 300  # seconds per file
    keep_larger_output: bool = False  # keep output even when larger than the original
    log_level: str = "INFO"

    # Privacy
    check_updates: bool = True
    store_history: bool = True
    skip_version: str = ""  # suppress update dialog for this specific version

    # Window state (GUI)
    window_width: int = 760
    window_height: int = 640
    window_maximized: bool = False

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create settings from a dictionary.

        Unknown keys are ignored and values of the wrong type fall back to the
        default, so a hand-edited or older settings file never crashes startup.
        """
        defaults = cls()
        known = {f.name for f in dataclasses.fields(cls)}
        filtered: dict = {}
        for key, value in data.items():
            if key not in known:
                continue
            default_value = getattr(defaults, key)
            if default_value is not None and value is not None:
                if isinstance(default_value, bool):
                    if not isinstance(value, bool):
                        continue
                elif isinstance(default_value, int) and not isinstance(value, int):
                    continue
                elif isinstance(default_value, str) and not isinstance(value, str):
                    continue
            filtered[key] = value
        settings = cls(**filtered)
        settings.version = __version__  # always stamp the running version
        return settings

    # Convenience accessors -------------------------------------------------

    @property
    def output_dir(self) -> Optional[Path]:
        """Return the custom output folder, or None for "same folder as source"."""
        value = (self.output_location or "").strip()
        if not value or value == SAME_FOLDER:
            return None
        return Path(value)

    @property
    def normalized_theme(self) -> str:
        return self.theme if self.theme in VALID_THEMES else "system"

    @property
    def normalized_log_level(self) -> str:
        level = (self.log_level or "").upper()
        return level if level in VALID_LOG_LEVELS else "INFO"


class ConfigManager:
    """Loads and saves :class:`Settings` as JSON in the app data folder."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: Custom config directory. If None, uses AppData/Squash.
        """
        if config_dir is None:
            config_dir = FileSystemHelper.get_app_data_dir()

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "settings.json"
        self.settings = Settings()

        FileSystemHelper.ensure_directory(self.config_dir)
        logger.info(f"ConfigManager initialized: {self.config_dir}")

    def load_settings(self) -> Settings:
        """Load settings from disk, falling back to defaults on any problem."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("settings.json does not contain an object")
                self.settings = Settings.from_dict(data)
                logger.info("Settings loaded successfully")
            else:
                logger.info("No settings file found, using defaults")
        except Exception as exc:
            logger.error(f"Error loading settings, using defaults: {exc}")
            self.settings = Settings()
        return self.settings

    def save_settings(self, settings: Optional[Settings] = None) -> bool:
        """Atomically write settings to disk.

        Args:
            settings: Settings to persist. If None, the current settings are used.

        Returns:
            True on success.
        """
        if settings is not None:
            self.settings = settings

        temp_file = self.config_file.with_suffix(".json.tmp")
        try:
            FileSystemHelper.ensure_directory(self.config_dir)
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.settings.to_dict(), f, indent=2, ensure_ascii=False)
            os.replace(temp_file, self.config_file)
            logger.info("Settings saved successfully")
            return True
        except Exception as exc:
            logger.error(f"Error saving settings: {exc}")
            try:
                temp_file.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        return getattr(self.settings, key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value (unknown keys are ignored with a warning)."""
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
        else:
            logger.warning(f"Unknown setting key: {key}")

    def reset_to_defaults(self) -> None:
        """Reset settings to defaults and persist them."""
        self.settings = Settings()
        self.save_settings()
        logger.info("Settings reset to defaults")
