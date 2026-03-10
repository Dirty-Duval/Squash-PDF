"""
Main entry point for Squash PDF Compressor.
"""

import sys
from pathlib import Path

from .utils.logger import setup_logger
from .utils.filesystem import FileSystemHelper

# Resolve assets directory — handles both dev tree and PyInstaller frozen builds.
# In frozen mode (COLLECT), assets land in <app>/_internal/assets/ next to the exe.
if getattr(sys, "frozen", False):
    _ASSETS_DIR = Path(sys.executable).parent / "_internal" / "assets"
else:
    _ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
_THEME_FILE = _ASSETS_DIR / "squash_theme.json"


def main():
    """Main application entry point."""
    # Set up logging
    log_dir = FileSystemHelper.get_app_data_dir() / "logs"
    log_file = log_dir / "squash.log"
    logger = setup_logger(log_file=log_file)

    logger.info("=" * 60)
    logger.info("Squash PDF Compressor v2.1.0 starting...")
    logger.info("=" * 60)

    try:
        # Import GUI after logging is set up
        import customtkinter as ctk
        from .gui.main_window import MainWindow

        # Configure appearance before creating any window
        ctk.set_appearance_mode("System")
        if _THEME_FILE.exists():
            ctk.set_default_color_theme(str(_THEME_FILE))
        else:
            ctk.set_default_color_theme("blue")

        # Create and run application
        app = MainWindow()
        app.mainloop()

        logger.info("Application closed normally")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
