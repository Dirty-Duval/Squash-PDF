"""
Appearance helpers shared by the entry point and the GUI.
"""

import customtkinter as ctk

_THEME_TO_CTK = {"system": "System", "light": "Light", "dark": "Dark"}


def apply_appearance(theme: str) -> None:
    """Apply a Squash theme name (``system`` / ``light`` / ``dark``) to CustomTkinter."""
    ctk.set_appearance_mode(_THEME_TO_CTK.get(theme, "System"))
