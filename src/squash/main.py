"""
Main entry point for Squash PDF Compressor.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from . import APP_NAME, __version__
from .config.manager import ConfigManager
from .utils.filesystem import FileSystemHelper
from .utils.logger import setup_logger

# Resolve assets directory — handles both dev tree and PyInstaller frozen builds.
# In frozen mode (COLLECT), assets land in <app>/_internal/assets/ next to the exe.
if getattr(sys, "frozen", False):
    ASSETS_DIR = Path(sys.executable).parent / "_internal" / "assets"
else:
    ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
THEME_FILE = ASSETS_DIR / "squash_theme.json"
ICON_FILE = ASSETS_DIR / "squash.ico"


def _install_excepthook(logger: logging.Logger) -> None:
    """Make sure uncaught exceptions (including in Tk callbacks) reach the log."""

    def _hook(exc_type, exc, tb):
        logger.critical("Uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook


def main() -> None:
    """Application entry point."""
    config_manager = ConfigManager()
    settings = config_manager.load_settings()

    log_file = FileSystemHelper.get_app_data_dir() / "logs" / "squash.log"
    logger = setup_logger(level=settings.normalized_log_level, log_file=log_file)
    _install_excepthook(logger)

    logger.info("=" * 60)
    logger.info(f"{APP_NAME} v{__version__} starting...")
    logger.info("=" * 60)

    try:
        import customtkinter as ctk

        from .gui.appearance import apply_appearance
        from .gui.main_window import MainWindow, StartupError

        # Configure appearance before creating any window
        apply_appearance(settings.normalized_theme)
        if THEME_FILE.exists():
            ctk.set_default_color_theme(str(THEME_FILE))
        else:
            logger.warning(f"Theme file not found, using built-in theme: {THEME_FILE}")
            ctk.set_default_color_theme("blue")

        try:
            app = MainWindow(config_manager=config_manager)
        except StartupError as exc:
            # The window has already shown the user a dialog explaining the problem.
            logger.critical(f"Startup aborted: {exc}")
            sys.exit(1)

        app.mainloop()
        logger.info("Application closed normally")

    except Exception as exc:
        logger.error(f"Fatal error: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
