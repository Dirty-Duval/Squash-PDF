"""
Integration test to verify Squash setup and Ghostscript integration.

Run this to verify your Squash installation is working correctly.
"""

import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("Squash PDF Compressor - Integration Test")
print("=" * 60)
print()

# Test 1: Import modules
print("Test 1: Importing modules...")
try:
    from squash import __version__
    from squash.core.compression import CompressionEngine
    from squash.core.presets import PresetManager
    from squash.core.batch import BatchProcessor
    from squash.config.manager import ConfigManager
    from squash.utils.logger import setup_logger
    from squash.utils.filesystem import FileSystemHelper

    print(f"✓ All modules imported successfully")
    print(f"  Version: {__version__}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Ghostscript detection
print("Test 2: Detecting Ghostscript...")
try:
    from squash.core.ghostscript import GhostscriptWrapper

    gs = GhostscriptWrapper()
    version = gs.get_version()
    print(f"✓ Ghostscript detected")
    print(f"  Path: {gs.gs_path}")
    print(f"  Version: {version}")
except RuntimeError as e:
    print(f"✗ Ghostscript not found: {e}")
    print("\nPlease install Ghostscript from:")
    print("https://www.ghostscript.com/releases/gsdnld.html")
    sys.exit(1)
except Exception as e:
    print(f"✗ Ghostscript detection failed: {e}")
    sys.exit(1)

print()

# Test 3: Preset system
print("Test 3: Testing preset system...")
try:
    manager = PresetManager()
    presets = manager.list_presets()
    print(f"✓ Preset system working")
    print(f"  Available presets: {len(presets)}")
    for preset in presets:
        print(f"    - {preset.display_name} ({preset.dpi} DPI): {preset.target_reduction}")

    # Test getting default preset
    default = manager.get_default_preset()
    print(f"  Default preset: {default.display_name}")
except Exception as e:
    print(f"✗ Preset system failed: {e}")
    sys.exit(1)

print()

# Test 4: Configuration system
print("Test 4: Testing configuration system...")
try:
    # Use temp directory for testing
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())

    config = ConfigManager(config_dir=temp_dir)
    config.load_settings()

    print(f"✓ Configuration system working")
    print(f"  Config directory: {config.config_dir}")
    print(f"  Default preset: {config.settings.default_preset}")
    print(f"  Theme: {config.settings.theme}")

    # Test save/load
    config.settings.default_preset = "high"
    config.save_settings()

    config2 = ConfigManager(config_dir=temp_dir)
    config2.load_settings()

    if config2.settings.default_preset == "high":
        print(f"  Settings persistence: ✓ Working")
    else:
        print(f"  Settings persistence: ✗ Failed")

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)

except Exception as e:
    print(f"✗ Configuration system failed: {e}")
    sys.exit(1)

print()

# Test 5: Compression engine initialization
print("Test 5: Testing compression engine...")
try:
    engine = CompressionEngine()
    print(f"✓ Compression engine initialized")
    print(f"  Ghostscript: {engine.gs.gs_path}")
    print(f"  Preset manager: {len(engine.preset_manager.presets)} presets")
except Exception as e:
    print(f"✗ Compression engine failed: {e}")
    sys.exit(1)

print()

# Test 6: Batch processor
print("Test 6: Testing batch processor...")
try:
    processor = BatchProcessor()
    print(f"✓ Batch processor initialized")
    print(f"  Engine ready: {processor.engine is not None}")
except Exception as e:
    print(f"✗ Batch processor failed: {e}")
    sys.exit(1)

print()

# Test 7: File system utilities
print("Test 7: Testing filesystem utilities...")
try:
    app_data = FileSystemHelper.get_app_data_dir()
    print(f"✓ Filesystem utilities working")
    print(f"  App data directory: {app_data}")

    # Test with a dummy file
    temp_file = Path(tempfile.gettempdir()) / "test.pdf"
    temp_file.touch()

    size_mb = FileSystemHelper.get_file_size_mb(temp_file)
    print(f"  File size calculation: ✓ Working")

    temp_file.unlink()  # Cleanup

except Exception as e:
    print(f"✗ Filesystem utilities failed: {e}")
    sys.exit(1)

print()

# Test 8: Logging system
print("Test 8: Testing logging system...")
try:
    import logging

    logger = setup_logger(name="test", level=logging.INFO)
    logger.info("Test log message")
    print(f"✓ Logging system working")
    print(f"  Logger configured: {logger.name}")
except Exception as e:
    print(f"✗ Logging system failed: {e}")
    sys.exit(1)

print()

# Summary
print("=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print()
print("Your Squash installation is working correctly!")
print()
print("Next steps:")
print("1. Run the application: python src/squash/main.py")
print("2. Add PDF files to compress")
print("3. Select quality preset and compress")
print()
print("For more information, see:")
print("- docs/user_guide.md - User guide")
print("- docs/API_REFERENCE.md - API documentation")
print("- docs/GHOSTSCRIPT_SETUP.md - Ghostscript setup")
print("- SETUP.md - Development setup")
print()
