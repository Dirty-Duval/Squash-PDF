"""
Preset management for compression quality settings.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class Preset:
    """Compression quality preset."""

    name: str
    display_name: str
    description: str
    dpi: int
    color_image_resolution: int
    gray_image_resolution: int
    mono_image_resolution: int
    pdf_settings: str
    target_reduction: str
    is_custom: bool = False  # Flag to distinguish custom from built-in presets

    def to_ghostscript_params(self) -> Dict[str, Any]:
        """
        Convert preset to Ghostscript parameters.

        Returns:
            Dictionary of Ghostscript parameters
        """
        return {
            "PDFSETTINGS": self.pdf_settings,
            "ColorImageResolution": self.color_image_resolution,
            "GrayImageResolution": self.gray_image_resolution,
            "MonoImageResolution": self.mono_image_resolution,
            "ColorImageDownsampleType": "/Bicubic",
            "GrayImageDownsampleType": "/Bicubic",
            "MonoImageDownsampleType": "/Subsample",
            "ColorConversionStrategy": "/RGB",
            "DownsampleColorImages": True,
            "DownsampleGrayImages": True,
            "DownsampleMonoImages": True,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary."""
        return asdict(self)


class PresetManager:
    """Manages compression quality presets."""

    # Default presets based on PRD requirements
    DEFAULT_PRESETS = {
        "small": Preset(
            name="small",
            display_name="Small",
            description="Smallest file size for web viewing (72 DPI)",
            dpi=72,
            color_image_resolution=72,
            gray_image_resolution=72,
            mono_image_resolution=300,
            pdf_settings="/screen",
            target_reduction="70-90%",
        ),
        "medium": Preset(
            name="medium",
            display_name="Medium",
            description="Balanced quality for general documents (150 DPI)",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
        ),
        "high": Preset(
            name="high",
            display_name="High Quality",
            description="High quality for printing (300 DPI)",
            dpi=300,
            color_image_resolution=300,
            gray_image_resolution=300,
            mono_image_resolution=600,
            pdf_settings="/printer",
            target_reduction="30-50%",
        ),
    }

    def __init__(self):
        """Initialize preset manager with default and custom presets."""
        self.presets: Dict[str, Preset] = self.DEFAULT_PRESETS.copy()
        self._load_custom_presets()
        logger.info(f"Initialized PresetManager with {len(self.presets)} presets")

    def get_preset(self, name: str) -> Preset:
        """
        Get preset by name.

        Args:
            name: Preset name (small, medium, high)

        Returns:
            Preset object

        Raises:
            KeyError: If preset not found
        """
        if name not in self.presets:
            raise KeyError(f"Preset '{name}' not found. Available: {list(self.presets.keys())}")

        return self.presets[name]

    def list_presets(self) -> List[Preset]:
        """
        Get list of all available presets.

        Returns:
            List of Preset objects
        """
        return list(self.presets.values())

    def get_preset_names(self) -> List[str]:
        """
        Get list of preset names.

        Returns:
            List of preset names
        """
        return list(self.presets.keys())

    def get_default_preset(self) -> Preset:
        """
        Get default preset (medium quality).

        Returns:
            Default Preset object
        """
        return self.presets["medium"]

    @property
    def custom_presets_file(self) -> Path:
        """
        Get path to custom presets JSON file.

        Returns:
            Path to custom_presets.json in AppData
        """
        from ..utils.filesystem import FileSystemHelper

        presets_dir = FileSystemHelper.get_app_data_dir() / "presets"
        FileSystemHelper.ensure_directory(presets_dir)
        return presets_dir / "custom_presets.json"

    def _load_custom_presets(self) -> None:
        """Load custom presets from JSON file."""
        if not self.custom_presets_file.exists():
            logger.debug("No custom presets file found")
            return

        try:
            with open(self.custom_presets_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            presets_data = data.get("presets", [])
            loaded_count = 0

            for preset_dict in presets_data:
                try:
                    # Ensure is_custom flag is set
                    preset_dict["is_custom"] = True
                    preset = Preset(**preset_dict)

                    # Validate before adding
                    is_valid, error = self._validate_preset(preset)
                    if is_valid:
                        self.presets[preset.name] = preset
                        loaded_count += 1
                    else:
                        logger.warning(f"Skipping invalid preset '{preset.name}': {error}")

                except Exception as e:
                    logger.error(f"Error loading preset: {e}")
                    continue

            logger.info(f"Loaded {loaded_count} custom presets from {self.custom_presets_file}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse custom presets JSON: {e}")
        except Exception as e:
            logger.error(f"Error loading custom presets: {e}")

    def _save_custom_presets(self) -> bool:
        """
        Save all custom presets to JSON file.

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Collect only custom presets
            custom_presets = [
                preset.to_dict()
                for preset in self.presets.values()
                if preset.is_custom
            ]

            data = {"version": "2.0.0", "presets": custom_presets}

            # Atomic write: write to temp file first, then rename
            temp_file = self.custom_presets_file.with_suffix(".tmp")

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Rename temp to actual file (atomic on Windows)
            temp_file.replace(self.custom_presets_file)

            logger.info(f"Saved {len(custom_presets)} custom presets to {self.custom_presets_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save custom presets: {e}")
            return False

    def _validate_preset(self, preset: Preset) -> tuple[bool, Optional[str]]:
        """
        Validate preset data.

        Args:
            preset: Preset object to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate name
        if not preset.name or len(preset.name) > 50:
            return False, "Name must be 1-50 characters"

        if not re.match(r"^[a-zA-Z0-9_\-\s]+$", preset.name):
            return False, "Name can only contain letters, numbers, spaces, hyphens, and underscores"

        # Validate display name
        if not preset.display_name or len(preset.display_name) > 100:
            return False, "Display name must be 1-100 characters"

        # Validate DPI values
        if not (50 <= preset.color_image_resolution <= 2400):
            return False, "Color image resolution must be 50-2400 DPI"

        if not (50 <= preset.gray_image_resolution <= 2400):
            return False, "Gray image resolution must be 50-2400 DPI"

        if not (50 <= preset.mono_image_resolution <= 2400):
            return False, "Mono image resolution must be 50-2400 DPI"

        # Validate PDF settings
        valid_pdf_settings = ["/screen", "/ebook", "/printer", "/prepress", "/default"]
        if preset.pdf_settings not in valid_pdf_settings:
            return False, f"PDF settings must be one of: {', '.join(valid_pdf_settings)}"

        return True, None

    def add_custom_preset(self, preset: Preset) -> bool:
        """
        Add a new custom preset.

        Args:
            preset: Preset object to add

        Returns:
            True if added successfully, False otherwise

        Raises:
            ValueError: If preset name already exists or validation fails
        """
        # Ensure is_custom flag is set
        preset.is_custom = True

        # Validate preset
        is_valid, error = self._validate_preset(preset)
        if not is_valid:
            raise ValueError(f"Invalid preset: {error}")

        # Check if name already exists
        if preset.name in self.presets:
            raise ValueError(f"Preset '{preset.name}' already exists")

        # Add to presets dict
        self.presets[preset.name] = preset

        # Save to file
        success = self._save_custom_presets()
        if success:
            logger.info(f"Added custom preset: {preset.name}")
        else:
            # Rollback if save failed
            del self.presets[preset.name]
            raise IOError("Failed to save custom preset to file")

        return success

    def update_preset(self, name: str, preset: Preset) -> bool:
        """
        Update existing custom preset.

        Args:
            name: Name of preset to update
            preset: New preset data

        Returns:
            True if updated successfully, False otherwise

        Raises:
            ValueError: If preset is not custom or validation fails
            KeyError: If preset not found
        """
        # Check if preset exists
        if name not in self.presets:
            raise KeyError(f"Preset '{name}' not found")

        # Check if it's a custom preset (can't modify built-ins)
        if not self.presets[name].is_custom:
            raise ValueError(f"Cannot modify built-in preset '{name}'")

        # Ensure is_custom flag is set
        preset.is_custom = True

        # Validate new preset data
        is_valid, error = self._validate_preset(preset)
        if not is_valid:
            raise ValueError(f"Invalid preset: {error}")

        # If name changed, check for conflicts
        if preset.name != name and preset.name in self.presets:
            raise ValueError(f"Preset '{preset.name}' already exists")

        # Store old preset for rollback
        old_preset = self.presets[name]

        # Update preset
        del self.presets[name]
        self.presets[preset.name] = preset

        # Save to file
        success = self._save_custom_presets()
        if not success:
            # Rollback on failure
            del self.presets[preset.name]
            self.presets[name] = old_preset
            raise IOError("Failed to save updated preset to file")

        logger.info(f"Updated custom preset: {name} -> {preset.name}")
        return success

    def delete_preset(self, name: str) -> bool:
        """
        Delete custom preset (protects built-in presets).

        Args:
            name: Name of preset to delete

        Returns:
            True if deleted successfully, False otherwise

        Raises:
            ValueError: If preset is built-in
            KeyError: If preset not found
        """
        # Check if preset exists
        if name not in self.presets:
            raise KeyError(f"Preset '{name}' not found")

        # Check if it's a custom preset (can't delete built-ins)
        if not self.presets[name].is_custom:
            raise ValueError(f"Cannot delete built-in preset '{name}'")

        # Store for rollback
        deleted_preset = self.presets[name]

        # Delete from dict
        del self.presets[name]

        # Save to file
        success = self._save_custom_presets()
        if not success:
            # Rollback on failure
            self.presets[name] = deleted_preset
            raise IOError("Failed to save changes to file")

        logger.info(f"Deleted custom preset: {name}")
        return success

    def export_preset(self, name: str, file_path: Path) -> bool:
        """
        Export preset to JSON file.

        Args:
            name: Name of preset to export
            file_path: Path where preset will be saved

        Returns:
            True if exported successfully, False otherwise

        Raises:
            KeyError: If preset not found
        """
        # Check if preset exists
        if name not in self.presets:
            raise KeyError(f"Preset '{name}' not found")

        try:
            preset = self.presets[name]
            data = {
                "version": "2.0.0",
                "preset": preset.to_dict(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported preset '{name}' to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export preset: {e}")
            return False

    def import_preset(self, file_path: Path) -> Preset:
        """
        Import preset from JSON file (does not add to manager yet).

        Args:
            file_path: Path to preset JSON file

        Returns:
            Preset object loaded from file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or preset data is malformed
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Support both single preset and preset array formats
            if "preset" in data:
                preset_dict = data["preset"]
            elif "presets" in data and len(data["presets"]) > 0:
                preset_dict = data["presets"][0]
            else:
                raise ValueError("Invalid preset file format")

            # Create preset object (will be custom)
            preset_dict["is_custom"] = True
            preset = Preset(**preset_dict)

            # Validate
            is_valid, error = self._validate_preset(preset)
            if not is_valid:
                raise ValueError(f"Invalid preset: {error}")

            logger.info(f"Imported preset '{preset.name}' from {file_path}")
            return preset

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except TypeError as e:
            raise ValueError(f"Malformed preset data: {e}")
        except Exception as e:
            raise ValueError(f"Failed to import preset: {e}")
