"""
Configuration management for application settings.
"""

import dataclasses
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Any
import json
import logging

from ..utils.filesystem import FileSystemHelper

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Application settings."""

    version: str = "2.1.0"

    # General
    default_preset: str = "medium"
    output_location: str = "same_folder"  # or custom path
    output_naming_pattern: str = "{filename}_compressed.pdf"
    theme: str = "system"  # light, dark, system

    # Advanced
    ghostscript_path: Optional[str] = None
    compression_timeout: int = 300  # seconds
    log_level: str = "WARNING"

    # Privacy
    check_updates: bool = True
    store_history: bool = True
    skip_version: str = ""  # suppress update dialog for this specific version

    # Window state (GUI)
    window_width: int = 700
    window_height: int = 600
    window_maximized: bool = False

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create settings from dictionary, ignoring unknown keys."""
        known_keys = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known_keys}
        return cls(**filtered)


class ConfigManager:
    """Manages application configuration and settings."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Custom config directory. If None, uses AppData.
        """
        if config_dir is None:
            config_dir = FileSystemHelper.get_app_data_dir()

        self.config_dir = config_dir
        self.config_file = self.config_dir / "settings.json"
        self.settings = Settings()

        # Ensure config directory exists
        FileSystemHelper.ensure_directory(self.config_dir)

        logger.info(f"ConfigManager initialized: {self.config_dir}")

    def load_settings(self) -> Settings:
        """
        Load settings from file.

        Returns:
            Settings object
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.settings = Settings.from_dict(data)
                    logger.info("Settings loaded successfully")
            else:
                logger.info("No settings file found, using defaults")

        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self.settings = Settings()  # Use defaults

        return self.settings

    def save_settings(self, settings: Optional[Settings] = None) -> bool:
        """
        Save settings to file.

        Args:
            settings: Settings object. If None, uses current settings.

        Returns:
            True if successful, False otherwise
        """
        if settings:
            self.settings = settings

        try:
            with open(self.config_file, "w") as f:
                json.dump(self.settings.to_dict(), f, indent=2)
            logger.info("Settings saved successfully")
            return True

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by key.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        return getattr(self.settings, key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set setting value.

        Args:
            key: Setting key
            value: Setting value
        """
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
        else:
            logger.warning(f"Unknown setting key: {key}")

    def reset_to_defaults(self) -> None:
        """Reset settings to defaults."""
        self.settings = Settings()
        self.save_settings()
        logger.info("Settings reset to defaults")
