"""
Theme color management for chart components.

Provides centralized color scheme management that adapts to CustomTkinter's
appearance mode (dark/light).
"""

import customtkinter as ctk
from typing import Dict


class ChartTheme:
    """Centralized theme color management for charts.

    Provides consistent color schemes for all chart components based on
    CustomTkinter's current appearance mode.
    """

    @staticmethod
    def get_colors() -> Dict[str, str]:
        """Get colors based on current CustomTkinter appearance mode.

        Returns:
            Dictionary with color keys:
                - bg: Background color for canvas
                - text: Text/label color
                - primary: Primary bars/elements (original size, main data)
                - success: Success indicators (compressed size, positive results)
                - border: Border/outline color
                - grid: Grid line color
                - axis: Axis line color
                - warning: Warning/failure indicators

        Example:
            >>> colors = ChartTheme.get_colors()
            >>> canvas = tk.Canvas(parent, bg=colors["bg"])
        """
        mode = ctk.get_appearance_mode()  # Returns "Dark" or "Light"

        if mode == "Dark":
            return {
                "bg": "#2A231C",           # Dark warm brown background
                "text": "#F0E8DC",          # Warm white text
                "primary": "#E07B10",       # Brand orange (original/main data)
                "success": "#50C878",       # Green (compressed/success)
                "border": "#7A3800",        # Dark orange border
                "grid": "#3A2A1A",          # Dark warm grid lines
                "axis": "#C2B8AC",          # Warm gray axes
                "warning": "#E74C3C",       # Red (errors/warnings)
            }
        else:  # Light mode
            return {
                "bg": "#F5F0EB",           # Warm cream background
                "text": "#1A1208",          # Dark warm text
                "primary": "#C86B00",       # Brand orange (original/main data)
                "success": "#43A047",       # Darker green (compressed/success)
                "border": "#8B3A0F",        # Dark orange border
                "grid": "#DDD4C8",          # Warm light grid lines
                "axis": "#6A5A4A",          # Warm gray axes
                "warning": "#C62828",       # Darker red (errors/warnings)
            }

    @staticmethod
    def format_size(bytes_size: int) -> str:
        """Format byte size to human-readable string.

        Args:
            bytes_size: Size in bytes

        Returns:
            Formatted string with appropriate unit (bytes, KB, MB, GB)

        Example:
            >>> ChartTheme.format_size(1024)
            '1.0 KB'
            >>> ChartTheme.format_size(5242880)
            '5.0 MB'
        """
        if bytes_size < 1024:
            return f"{bytes_size} bytes"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"
