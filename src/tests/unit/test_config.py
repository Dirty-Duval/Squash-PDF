"""
Unit tests for configuration management.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from squash import __version__
from squash.config.manager import ConfigManager, Settings


class TestSettings:
    """Test Settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.version == __version__
        assert settings.default_preset == "medium"
        assert settings.theme == "system"
        assert settings.output_dir is None
        assert settings.window_width > 0
        assert settings.window_height > 0

    def test_settings_to_dict(self):
        """Test converting settings to dictionary."""
        settings = Settings()
        data = settings.to_dict()

        assert isinstance(data, dict)
        assert data["version"] == __version__
        assert data["default_preset"] == "medium"

    def test_from_dict_stamps_running_version_and_ignores_bad_types(self):
        data = {
            "version": "1.0.0",
            "theme": "dark",
            "compression_timeout": "not-a-number",
            "check_updates": "yes",
            "unknown_key": 123,
        }
        settings = Settings.from_dict(data)
        assert settings.version == __version__
        assert settings.theme == "dark"
        assert settings.compression_timeout == Settings().compression_timeout
        assert settings.check_updates is True

    def test_output_dir_property(self):
        assert Settings(output_location="same_folder").output_dir is None
        assert Settings(output_location="").output_dir is None
        assert Settings(output_location="C:/out").output_dir == Path("C:/out")

    def test_normalizers(self):
        assert Settings(theme="purple").normalized_theme == "system"
        assert Settings(log_level="verbose").normalized_log_level == "INFO"
        assert Settings(log_level="debug").normalized_log_level == "DEBUG"

    def test_settings_from_dict(self):
        """Test creating settings from dictionary."""
        data = {
            "version": "2.0.0",
            "default_preset": "high",
            "theme": "dark",
        }

        settings = Settings.from_dict(data)
        assert settings.default_preset == "high"
        assert settings.theme == "dark"


class TestConfigManager:
    """Test ConfigManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_initialization(self, temp_config_dir):
        """Test config manager initialization."""
        manager = ConfigManager(config_dir=temp_config_dir)

        assert manager.config_dir == temp_config_dir
        assert manager.config_file == temp_config_dir / "settings.json"
        assert temp_config_dir.exists()

    def test_save_and_load_settings(self, temp_config_dir):
        """Test saving and loading settings."""
        manager = ConfigManager(config_dir=temp_config_dir)

        # Modify settings
        manager.settings.default_preset = "high"
        manager.settings.theme = "dark"

        # Save
        success = manager.save_settings()
        assert success is True
        assert manager.config_file.exists()

        # Create new manager and load
        new_manager = ConfigManager(config_dir=temp_config_dir)
        new_manager.load_settings()

        assert new_manager.settings.default_preset == "high"
        assert new_manager.settings.theme == "dark"

    def test_get_setting(self, temp_config_dir):
        """Test getting setting value."""
        manager = ConfigManager(config_dir=temp_config_dir)

        value = manager.get("default_preset")
        assert value == "medium"

        # Test default value
        value = manager.get("nonexistent", "default_value")
        assert value == "default_value"

    def test_set_setting(self, temp_config_dir):
        """Test setting value."""
        manager = ConfigManager(config_dir=temp_config_dir)

        manager.set("default_preset", "small")
        assert manager.settings.default_preset == "small"

    def test_reset_to_defaults(self, temp_config_dir):
        """Test resetting to default settings."""
        manager = ConfigManager(config_dir=temp_config_dir)

        # Modify settings
        manager.settings.default_preset = "high"
        manager.save_settings()

        # Reset
        manager.reset_to_defaults()

        assert manager.settings.default_preset == "medium"
