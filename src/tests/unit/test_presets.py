"""
Unit tests for preset management.
"""

import pytest
from squash.core.presets import Preset, PresetManager


class TestPreset:
    """Test Preset class."""

    def test_preset_creation(self):
        """Test creating a preset."""
        preset = Preset(
            name="test",
            display_name="Test Preset",
            description="Test description",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
        )

        assert preset.name == "test"
        assert preset.dpi == 150

    def test_to_ghostscript_params(self):
        """Test converting preset to Ghostscript parameters."""
        preset = Preset(
            name="test",
            display_name="Test",
            description="Test",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50%",
        )

        params = preset.to_ghostscript_params()

        assert params["PDFSETTINGS"] == "/ebook"
        assert params["ColorImageResolution"] == 150
        assert params["DownsampleColorImages"] is True


class TestPresetManager:
    """Test PresetManager class."""

    def test_initialization(self):
        """Test preset manager initialization."""
        manager = PresetManager()

        assert len(manager.presets) == 3  # small, medium, high
        assert "small" in manager.presets
        assert "medium" in manager.presets
        assert "high" in manager.presets

    def test_get_preset(self):
        """Test getting a preset."""
        manager = PresetManager()

        preset = manager.get_preset("medium")
        assert preset.name == "medium"
        assert preset.dpi == 150

    def test_get_invalid_preset(self):
        """Test getting invalid preset raises error."""
        manager = PresetManager()

        with pytest.raises(KeyError):
            manager.get_preset("invalid")

    def test_list_presets(self):
        """Test listing all presets."""
        manager = PresetManager()

        presets = manager.list_presets()
        assert len(presets) == 3
        assert all(isinstance(p, Preset) for p in presets)

    def test_get_preset_names(self):
        """Test getting preset names."""
        manager = PresetManager()

        names = manager.get_preset_names()
        assert "small" in names
        assert "medium" in names
        assert "high" in names

    def test_default_preset(self):
        """Test getting default preset."""
        manager = PresetManager()

        default = manager.get_default_preset()
        assert default.name == "medium"
