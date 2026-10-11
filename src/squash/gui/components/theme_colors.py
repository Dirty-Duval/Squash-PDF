"""
Theme color management for chart components.

Provides centralized color scheme management that adapts to CustomTkinter's
appearance mode (dark/light).
"""

from typing import Dict

import customtkinter as ctk

from ...utils.filesystem import FileSystemHelper


class ChartTheme:
    """Centralized theme color management for charts."""

    @staticmethod
    def get_colors() -> Dict[str, str]:
        """Get colors based on current CustomTkinter appearance mode.

        Returns:
            Dictionary with keys ``bg``, ``text``, ``primary``, ``success``,
            ``border``, ``grid``, ``axis`` and ``warning``.
        """
        if ctk.get_appearance_mode() == "Dark":
            return {
                "bg": "#2A231C",  # Dark warm brown background
                "text": "#F0E8DC",  # Warm white text
                "primary": "#E07B10",  # Brand orange (original/main data)
                "success": "#50C878",  # Green (compressed/success)
                "border": "#7A3800",  # Dark orange border
                "grid": "#3A2A1A",  # Dark warm grid lines
                "axis": "#C2B8AC",  # Warm gray axes
                "warning": "#E74C3C",  # Red (errors/warnings)
            }
        return {
            "bg": "#F5F0EB",  # Warm cream background
            "text": "#1A1208",  # Dark warm text
            "primary": "#C86B00",  # Brand orange (original/main data)
            "success": "#43A047",  # Darker green (compressed/success)
            "border": "#8B3A0F",  # Dark orange border
            "grid": "#DDD4C8",  # Warm light grid lines
            "axis": "#6A5A4A",  # Warm gray axes
            "warning": "#C62828",  # Darker red (errors/warnings)
        }

    @staticmethod
    def format_size(bytes_size: int) -> str:
        """Format a byte count for chart labels (delegates to FileSystemHelper)."""
        return FileSystemHelper.format_size(bytes_size)
