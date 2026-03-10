"""
Unit tests for custom preset management functionality.

Tests CRUD operations, validation, import/export, and persistence
for custom compression presets.
"""

import pytest
from pathlib import Path
import json
import tempfile
from src.squash.core.presets import PresetManager, Preset


class TestCustomPresetCRUD:
    """Test Create, Read, Update, Delete operations for custom presets."""

    def test_add_custom_preset_success(self, tmp_path):
        """Test successfully adding a custom preset."""
        # Setup
        manager = PresetManager()
        custom_preset = Preset(
            name="test_preset",
            display_name="Test Preset",
            description="Test custom preset",
            dpi=200,
            color_image_resolution=200,
            gray_image_resolution=200,
            mono_image_resolution=600,
            pdf_settings="/ebook",
            target_reduction="40-60%",
            is_custom=True
        )

        # Execute
        result = manager.add_custom_preset(custom_preset)

        # Assert
        assert result is True
        assert "test_preset" in manager.get_preset_names()
        assert manager.get_preset("test_preset").is_custom is True

        # Cleanup
        manager.delete_preset("test_preset")

    def test_add_duplicate_preset_fails(self, tmp_path):
        """Test that adding a duplicate preset raises ValueError."""
        # Setup
        manager = PresetManager()
        custom_preset = Preset(
            name="duplicate_test",
            display_name="Duplicate Test",
            description="Test duplicate",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )
        manager.add_custom_preset(custom_preset)

        # Execute & Assert
        with pytest.raises(ValueError, match="already exists"):
            manager.add_custom_preset(custom_preset)

        # Cleanup
        manager.delete_preset("duplicate_test")

    def test_update_custom_preset_success(self, tmp_path):
        """Test successfully updating a custom preset."""
        # Setup
        manager = PresetManager()
        original = Preset(
            name="update_test",
            display_name="Original",
            description="Original preset",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )
        manager.add_custom_preset(original)

        # Execute - update with new data
        updated = Preset(
            name="update_test",
            display_name="Updated",
            description="Updated preset",
            dpi=200,
            color_image_resolution=200,
            gray_image_resolution=200,
            mono_image_resolution=600,
            pdf_settings="/printer",
            target_reduction="40-60%",
            is_custom=True
        )
        result = manager.update_preset("update_test", updated)

        # Assert
        assert result is True
        preset = manager.get_preset("update_test")
        assert preset.display_name == "Updated"
        assert preset.dpi == 200

        # Cleanup
        manager.delete_preset("update_test")

    def test_update_builtin_preset_fails(self):
        """Test that updating a built-in preset raises ValueError."""
        # Setup
        manager = PresetManager()
        modified = Preset(
            name="small",
            display_name="Modified Small",
            description="Should not work",
            dpi=100,
            color_image_resolution=100,
            gray_image_resolution=100,
            mono_image_resolution=300,
            pdf_settings="/screen",
            target_reduction="70-90%",
            is_custom=False
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Cannot modify built-in preset"):
            manager.update_preset("small", modified)

    def test_delete_custom_preset_success(self, tmp_path):
        """Test successfully deleting a custom preset."""
        # Setup
        manager = PresetManager()
        custom = Preset(
            name="delete_test",
            display_name="Delete Test",
            description="Will be deleted",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )
        manager.add_custom_preset(custom)
        assert "delete_test" in manager.get_preset_names()

        # Execute
        result = manager.delete_preset("delete_test")

        # Assert
        assert result is True
        assert "delete_test" not in manager.get_preset_names()

    def test_delete_builtin_preset_fails(self):
        """Test that deleting a built-in preset raises ValueError."""
        # Setup
        manager = PresetManager()

        # Execute & Assert
        with pytest.raises(ValueError, match="Cannot delete built-in preset"):
            manager.delete_preset("small")

        # Verify built-in still exists
        assert "small" in manager.get_preset_names()

    def test_delete_nonexistent_preset_fails(self):
        """Test that deleting a non-existent preset raises KeyError."""
        # Setup
        manager = PresetManager()

        # Execute & Assert
        with pytest.raises(KeyError, match="not found"):
            manager.delete_preset("nonexistent")


class TestPresetValidation:
    """Test preset validation rules."""

    def test_validate_name_too_long(self):
        """Test that names longer than 50 characters are rejected."""
        # Setup
        manager = PresetManager()
        invalid_preset = Preset(
            name="a" * 51,  # 51 characters
            display_name="Valid Display",
            description="Valid description",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Name must be 1-50 characters"):
            manager.add_custom_preset(invalid_preset)

    def test_validate_name_invalid_characters(self):
        """Test that names with invalid characters are rejected."""
        # Setup
        manager = PresetManager()
        invalid_preset = Preset(
            name="invalid@name!",  # Contains @ and !
            display_name="Valid Display",
            description="Valid description",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="can only contain letters, numbers"):
            manager.add_custom_preset(invalid_preset)

    def test_validate_display_name_too_long(self):
        """Test that display names longer than 100 characters are rejected."""
        # Setup
        manager = PresetManager()
        invalid_preset = Preset(
            name="valid_name",
            display_name="a" * 101,  # 101 characters
            description="Valid description",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Display name must be 1-100 characters"):
            manager.add_custom_preset(invalid_preset)

    def test_validate_dpi_below_minimum(self):
        """Test that DPI values below 50 are rejected."""
        # Setup
        manager = PresetManager()
        invalid_preset = Preset(
            name="low_dpi",
            display_name="Low DPI Test",
            description="Test low DPI",
            dpi=49,
            color_image_resolution=49,  # Below minimum
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Color image resolution must be 50-2400 DPI"):
            manager.add_custom_preset(invalid_preset)

    def test_validate_dpi_above_maximum(self):
        """Test that DPI values above 2400 are rejected."""
        # Setup
        manager = PresetManager()
        invalid_preset = Preset(
            name="high_dpi",
            display_name="High DPI Test",
            description="Test high DPI",
            dpi=2401,
            color_image_resolution=150,
            gray_image_resolution=2401,  # Above maximum
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Gray image resolution must be 50-2400 DPI"):
            manager.add_custom_preset(invalid_preset)

    def test_validate_invalid_pdf_settings(self):
        """Test that invalid PDF settings are rejected."""
        # Setup
        manager = PresetManager()
        invalid_preset = Preset(
            name="invalid_pdf",
            display_name="Invalid PDF",
            description="Test invalid PDF settings",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/invalid",  # Not a valid setting
            target_reduction="50-70%",
            is_custom=True
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="PDF settings must be one of"):
            manager.add_custom_preset(invalid_preset)


class TestPresetPersistence:
    """Test preset save/load functionality."""

    def test_preset_save_load_cycle(self, tmp_path, monkeypatch):
        """Test that presets persist across manager instances."""
        # Setup - create custom preset
        manager1 = PresetManager()
        custom = Preset(
            name="persist_test",
            display_name="Persistence Test",
            description="Test persistence",
            dpi=200,
            color_image_resolution=200,
            gray_image_resolution=200,
            mono_image_resolution=600,
            pdf_settings="/printer",
            target_reduction="40-60%",
            is_custom=True
        )
        manager1.add_custom_preset(custom)

        # Execute - create new manager instance
        manager2 = PresetManager()

        # Assert - preset should exist in new instance
        assert "persist_test" in manager2.get_preset_names()
        loaded_preset = manager2.get_preset("persist_test")
        assert loaded_preset.display_name == "Persistence Test"
        assert loaded_preset.dpi == 200
        assert loaded_preset.is_custom is True

        # Cleanup
        manager2.delete_preset("persist_test")

    def test_json_corruption_handling(self, tmp_path, monkeypatch):
        """Test that corrupted JSON doesn't crash the manager."""
        # Setup - manually create corrupted JSON file
        from src.squash.utils.filesystem import FileSystemHelper
        presets_dir = FileSystemHelper.get_app_data_dir() / "presets"
        FileSystemHelper.ensure_directory(presets_dir)
        corrupt_file = presets_dir / "custom_presets.json"

        # Write invalid JSON
        with open(corrupt_file, "w") as f:
            f.write("{invalid json content")

        # Execute - should not crash, just log error
        manager = PresetManager()

        # Assert - should have default presets only
        assert len(manager.get_preset_names()) == 3
        assert "small" in manager.get_preset_names()
        assert "medium" in manager.get_preset_names()
        assert "high" in manager.get_preset_names()

        # Cleanup
        if corrupt_file.exists():
            corrupt_file.unlink()


class TestPresetImportExport:
    """Test preset import/export functionality."""

    def test_export_preset_to_json(self, tmp_path):
        """Test exporting a preset to JSON file."""
        # Setup
        manager = PresetManager()
        export_path = tmp_path / "exported_preset.json"

        # Execute
        result = manager.export_preset("medium", export_path)

        # Assert
        assert result is True
        assert export_path.exists()

        # Verify JSON content
        with open(export_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["version"] == "2.0.0"
        assert data["preset"]["name"] == "medium"
        assert data["preset"]["display_name"] == "Medium"
        assert data["preset"]["dpi"] == 150

    def test_import_preset_from_json(self, tmp_path):
        """Test importing a preset from JSON file."""
        # Setup - create a JSON file
        import_path = tmp_path / "import_test.json"
        preset_data = {
            "version": "2.0.0",
            "preset": {
                "name": "imported_test",
                "display_name": "Imported Test",
                "description": "Test import",
                "dpi": 180,
                "color_image_resolution": 180,
                "gray_image_resolution": 180,
                "mono_image_resolution": 400,
                "pdf_settings": "/ebook",
                "target_reduction": "45-65%",
                "is_custom": True
            }
        }

        with open(import_path, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, indent=2)

        # Execute
        manager = PresetManager()
        imported_preset = manager.import_preset(import_path)

        # Assert
        assert imported_preset.name == "imported_test"
        assert imported_preset.display_name == "Imported Test"
        assert imported_preset.dpi == 180
        assert imported_preset.is_custom is True

    def test_import_with_name_conflict(self, tmp_path):
        """Test importing a preset with conflicting name."""
        # Setup - create custom preset
        manager = PresetManager()
        custom = Preset(
            name="conflict_test",
            display_name="Existing",
            description="Existing preset",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )
        manager.add_custom_preset(custom)

        # Create import file with same name
        import_path = tmp_path / "conflict.json"
        preset_data = {
            "version": "2.0.0",
            "preset": {
                "name": "conflict_test",
                "display_name": "Imported",
                "description": "Should conflict",
                "dpi": 200,
                "color_image_resolution": 200,
                "gray_image_resolution": 200,
                "mono_image_resolution": 600,
                "pdf_settings": "/printer",
                "target_reduction": "40-60%",
                "is_custom": True
            }
        }

        with open(import_path, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, indent=2)

        # Execute - import returns preset, doesn't auto-add
        imported = manager.import_preset(import_path)

        # Assert - preset returned but not auto-added
        assert imported.name == "conflict_test"

        # Cleanup
        manager.delete_preset("conflict_test")

    def test_import_invalid_json(self, tmp_path):
        """Test importing from invalid JSON file."""
        # Setup
        invalid_path = tmp_path / "invalid.json"
        with open(invalid_path, "w") as f:
            f.write("{invalid json")

        # Execute & Assert
        manager = PresetManager()
        with pytest.raises(ValueError, match="Invalid JSON"):
            manager.import_preset(invalid_path)

    def test_import_nonexistent_file(self, tmp_path):
        """Test importing from non-existent file."""
        # Setup
        nonexistent = tmp_path / "does_not_exist.json"

        # Execute & Assert
        manager = PresetManager()
        with pytest.raises(FileNotFoundError):
            manager.import_preset(nonexistent)


class TestBuiltinProtection:
    """Test that built-in presets are properly protected."""

    def test_builtin_presets_have_correct_flag(self):
        """Test that built-in presets have is_custom=False."""
        # Setup
        manager = PresetManager()

        # Assert
        assert manager.get_preset("small").is_custom is False
        assert manager.get_preset("medium").is_custom is False
        assert manager.get_preset("high").is_custom is False

    def test_cannot_modify_builtin_via_update(self):
        """Test built-in presets cannot be modified via update."""
        # Setup
        manager = PresetManager()
        modified = Preset(
            name="medium",
            display_name="Modified Medium",
            description="Should fail",
            dpi=999,
            color_image_resolution=999,
            gray_image_resolution=999,
            mono_image_resolution=999,
            pdf_settings="/screen",
            target_reduction="99%",
            is_custom=True  # Try to force it
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Cannot modify built-in preset"):
            manager.update_preset("medium", modified)

    def test_cannot_delete_builtin(self):
        """Test built-in presets cannot be deleted."""
        # Setup
        manager = PresetManager()

        # Execute & Assert
        for builtin_name in ["small", "medium", "high"]:
            with pytest.raises(ValueError, match="Cannot delete built-in preset"):
                manager.delete_preset(builtin_name)

    def test_builtin_count_remains_constant(self):
        """Test that there are always 3 built-in presets."""
        # Setup
        manager = PresetManager()
        builtin_count = sum(1 for p in manager.list_presets() if not p.is_custom)

        # Assert
        assert builtin_count == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_valid_name_with_allowed_characters(self):
        """Test that names with spaces, hyphens, underscores are valid."""
        # Setup
        manager = PresetManager()
        valid_preset = Preset(
            name="test_preset-name 123",
            display_name="Valid Name Test",
            description="Test valid characters",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True
        )

        # Execute
        result = manager.add_custom_preset(valid_preset)

        # Assert
        assert result is True
        assert "test_preset-name 123" in manager.get_preset_names()

        # Cleanup
        manager.delete_preset("test_preset-name 123")

    def test_boundary_dpi_values(self):
        """Test DPI values at exact boundaries (50 and 2400)."""
        # Setup
        manager = PresetManager()
        min_dpi = Preset(
            name="min_dpi",
            display_name="Min DPI",
            description="Minimum DPI test",
            dpi=50,
            color_image_resolution=50,
            gray_image_resolution=50,
            mono_image_resolution=50,
            pdf_settings="/screen",
            target_reduction="90%",
            is_custom=True
        )
        max_dpi = Preset(
            name="max_dpi",
            display_name="Max DPI",
            description="Maximum DPI test",
            dpi=2400,
            color_image_resolution=2400,
            gray_image_resolution=2400,
            mono_image_resolution=2400,
            pdf_settings="/prepress",
            target_reduction="10%",
            is_custom=True
        )

        # Execute
        result_min = manager.add_custom_preset(min_dpi)
        result_max = manager.add_custom_preset(max_dpi)

        # Assert
        assert result_min is True
        assert result_max is True

        # Cleanup
        manager.delete_preset("min_dpi")
        manager.delete_preset("max_dpi")

    def test_all_valid_pdf_settings(self):
        """Test all valid PDF settings values."""
        # Setup
        manager = PresetManager()
        valid_settings = ["/screen", "/ebook", "/printer", "/prepress", "/default"]

        # Execute & Assert
        for i, setting in enumerate(valid_settings):
            preset = Preset(
                name=f"pdf_setting_{i}",
                display_name=f"PDF Setting {setting}",
                description=f"Test {setting}",
                dpi=150,
                color_image_resolution=150,
                gray_image_resolution=150,
                mono_image_resolution=300,
                pdf_settings=setting,
                target_reduction="50%",
                is_custom=True
            )
            result = manager.add_custom_preset(preset)
            assert result is True

            # Cleanup
            manager.delete_preset(f"pdf_setting_{i}")
