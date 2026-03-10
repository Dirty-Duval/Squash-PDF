"""
Shared window-icon helper for Squash dialogs.

Call apply_icon(window) in any CTkToplevel __init__ to set the Squash logo.
The 200 ms delay is required on Windows — CustomTkinter resets the icon
after window creation, so we must set it after the event loop runs once.
"""

import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolved once at import time so every dialog shares the same Path object.
if getattr(sys, "frozen", False):
    _ICON_PATH = Path(sys.executable).parent / "_internal" / "assets" / "squash.ico"
else:
    # src/squash/gui/_icon.py  →  ../../.. = project root
    _ICON_PATH = Path(__file__).parent.parent.parent.parent / "assets" / "squash.ico"


def apply_icon(window) -> None:
    """Set the Squash .ico on *window* after a short delay.

    Safe to call from any CTkToplevel subclass or inline dialog.
    Does nothing if the icon file is not found (dev environments without assets).
    """
    if not _ICON_PATH.exists():
        logger.debug(f"Window icon not found: {_ICON_PATH}")
        return

    icon_str = str(_ICON_PATH)

    def _set():
        try:
            if window.winfo_exists():
                window.iconbitmap(icon_str)
        except Exception as exc:
            logger.debug(f"iconbitmap failed: {exc}")

    window.after(200, _set)
