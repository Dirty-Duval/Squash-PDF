"""
Chart components for Squash PDF Compressor.

Canvas-based chart widgets for visualizing compression data:
- ComparisonBarChart: Before/after size comparison with horizontal bars
- TrendLineChart: Line chart showing compression ratios over time
- PresetComparisonBar: Grouped bar chart comparing preset effectiveness
"""

import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging

import customtkinter as ctk

from .theme_colors import ChartTheme

logger = logging.getLogger(__name__)


class ComparisonBarChart(tk.Canvas):
    """Horizontal bar chart for before/after file size comparison.

    Displays two horizontal bars representing original and compressed file sizes
    with automatic scaling and theme-aware colors.

    Example:
        >>> chart = ComparisonBarChart(parent, width=400, height=80)
        >>> chart.set_data(5242880, 2097152, "report.pdf")
        >>> chart.pack(padx=10, pady=10)
    """

    def __init__(self, parent, width: int = 400, height: int = 80, **kwargs):
        """Initialize comparison chart canvas.

        Args:
            parent: Parent widget
            width: Canvas width in pixels (default 400)
            height: Canvas height in pixels (default 80 - enough for 2 bars + labels)
            **kwargs: Additional canvas options
        """
        colors = ChartTheme.get_colors()
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=colors["bg"],
            highlightthickness=0,
            **kwargs,
        )
        self._colors = colors
        self._original_size: Optional[int] = None
        self._compressed_size: Optional[int] = None
        self._filename: str = ""

    def set_data(
        self, original_size: int, compressed_size: int, filename: str = ""
    ) -> None:
        """Update chart with size comparison data.

        Args:
            original_size: Original file size in bytes
            compressed_size: Compressed file size in bytes
            filename: Optional filename to display above bars

        Raises:
            ValueError: If compressed_size > original_size or sizes are negative

        Example:
            >>> chart.set_data(5242880, 2097152, "document.pdf")
        """
        if original_size < 0 or compressed_size < 0:
            raise ValueError("File sizes cannot be negative")

        if compressed_size > original_size:
            raise ValueError("Compressed size cannot exceed original size")

        self._original_size = original_size
        self._compressed_size = compressed_size
        self._filename = filename

        self._clear()
        self._draw()

    def _clear(self) -> None:
        """Clear all canvas items."""
        self.delete("all")

    def _draw(self) -> None:
        """Draw the comparison bars and labels."""
        if self._original_size is None or self._compressed_size is None:
            return

        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()

        # Use requested dimensions if not yet realized
        if canvas_width <= 1:
            canvas_width = int(self.cget("width"))
        if canvas_height <= 1:
            canvas_height = int(self.cget("height"))

        # Layout constants
        label_width = 120  # Space for size labels on right
        bar_area_width = canvas_width - label_width - 20  # 20px total padding
        bar_height = 18
        bar_spacing = 8
        top_margin = 8

        # Draw filename if provided
        y_offset = top_margin
        if self._filename:
            # Truncate long filenames
            display_name = self._filename
            if len(display_name) > 40:
                display_name = display_name[:37] + "..."

            self.create_text(
                10,
                y_offset,
                text=display_name,
                fill=self._colors["text"],
                anchor="w",
                font=("Arial", 9, "bold"),
                tags="label",
            )
            y_offset += 16

        # Calculate bar widths
        if self._original_size > 0:
            original_width = bar_area_width
            compressed_width = int(
                (self._compressed_size / self._original_size) * bar_area_width
            )
        else:
            original_width = 0
            compressed_width = 0

        # Draw "Original" label
        self.create_text(
            10,
            y_offset + bar_height // 2,
            text="Original",
            fill=self._colors["text"],
            anchor="w",
            font=("Arial", 8),
            tags="label",
        )

        # Draw original size bar
        bar_start_x = 70
        self.create_rectangle(
            bar_start_x,
            y_offset,
            bar_start_x + original_width,
            y_offset + bar_height,
            fill=self._colors["primary"],
            outline=self._colors["border"],
            tags="bar",
        )

        # Draw original size label
        original_text = ChartTheme.format_size(self._original_size)
        self.create_text(
            bar_start_x + original_width + 10,
            y_offset + bar_height // 2,
            text=original_text,
            fill=self._colors["text"],
            anchor="w",
            font=("Arial", 9),
            tags="label",
        )

        y_offset += bar_height + bar_spacing

        # Draw "Compressed" label
        self.create_text(
            10,
            y_offset + bar_height // 2,
            text="Compressed",
            fill=self._colors["text"],
            anchor="w",
            font=("Arial", 8),
            tags="label",
        )

        # Draw compressed size bar
        self.create_rectangle(
            bar_start_x,
            y_offset,
            bar_start_x + compressed_width,
            y_offset + bar_height,
            fill=self._colors["success"],
            outline=self._colors["border"],
            tags="bar",
        )

        # Draw compressed size label
        compressed_text = ChartTheme.format_size(self._compressed_size)
        self.create_text(
            bar_start_x + compressed_width + 10,
            y_offset + bar_height // 2,
            text=compressed_text,
            fill=self._colors["text"],
            anchor="w",
            font=("Arial", 9),
            tags="label",
        )

        # Draw reduction summary
        if self._original_size > 0:
            reduction_bytes = self._original_size - self._compressed_size
            reduction_percent = (reduction_bytes / self._original_size) * 100
            reduction_mb = reduction_bytes / (1024 * 1024)

            reduction_text = (
                f"Reduction: {reduction_mb:.1f} MB ({reduction_percent:.1f}%)"
            )

            self.create_text(
                bar_start_x,
                y_offset + bar_height + 10,
                text=reduction_text,
                fill=self._colors["success"],
                anchor="w",
                font=("Arial", 9, "italic"),
                tags="label",
            )

    def refresh_theme(self) -> None:
        """Refresh chart colors based on current theme.

        Call this method after theme changes to update colors.
        """
        self._colors = ChartTheme.get_colors()
        self.configure(bg=self._colors["bg"])
        if self._original_size is not None:
            self._clear()
            self._draw()


class TrendLineChart(tk.Canvas):
    """Line chart showing compression ratio trends over time.

    Displays compression ratios as a line chart with time-based X-axis
    and percentage Y-axis.

    Example:
        >>> chart = TrendLineChart(parent, width=600, height=300)
        >>> data = [(datetime(2026, 1, 1), 60.5), (datetime(2026, 1, 2), 65.0)]
        >>> chart.set_data(data)
        >>> chart.pack(padx=20, pady=20)
    """

    def __init__(self, parent, width: int = 600, height: int = 300, **kwargs):
        """Initialize trend chart canvas.

        Args:
            parent: Parent widget
            width: Canvas width in pixels (default 600)
            height: Canvas height in pixels (default 300)
            **kwargs: Additional canvas options
        """
        colors = ChartTheme.get_colors()
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=colors["bg"],
            highlightthickness=0,
            **kwargs,
        )
        self._colors = colors
        self._data: List[Tuple[datetime, float]] = []

    def set_data(self, entries: List[Tuple[datetime, float]]) -> None:
        """Plot compression ratios over time.

        Args:
            entries: List of (timestamp, compression_ratio) tuples sorted by time

        Example:
            >>> data = [
            ...     (datetime(2026, 1, 1), 60.0),
            ...     (datetime(2026, 1, 2), 65.0),
            ...     (datetime(2026, 1, 3), 58.0)
            ... ]
            >>> chart.set_data(data)
        """
        self._data = entries
        self._clear()
        self._draw()

    def _clear(self) -> None:
        """Clear all canvas items."""
        self.delete("all")

    def _draw(self) -> None:
        """Draw the trend line chart."""
        if not self._data:
            self._show_empty_state()
            return

        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()

        # Use requested dimensions if not yet realized
        if canvas_width <= 1:
            canvas_width = int(self.cget("width"))
        if canvas_height <= 1:
            canvas_height = int(self.cget("height"))

        # Layout constants
        margin_left = 60
        margin_right = 20
        margin_top = 30
        margin_bottom = 40

        plot_width = canvas_width - margin_left - margin_right
        plot_height = canvas_height - margin_top - margin_bottom

        # Draw axes
        self._draw_axes(margin_left, margin_top, plot_width, plot_height)

        # Draw grid
        self._draw_grid(margin_left, margin_top, plot_width, plot_height)

        # Plot data
        if len(self._data) == 1:
            self._plot_single_point(
                margin_left, margin_top, plot_width, plot_height
            )
        else:
            self._plot_line(margin_left, margin_top, plot_width, plot_height)

        # Draw statistics
        self._draw_statistics(margin_left, canvas_height - 10)

    def _show_empty_state(self) -> None:
        """Display message when no data available."""
        canvas_width = int(self.cget("width"))
        canvas_height = int(self.cget("height"))

        self.create_text(
            canvas_width // 2,
            canvas_height // 2,
            text="No compression history available",
            fill=self._colors["text"],
            font=("Arial", 12, "italic"),
            tags="empty",
        )

    def _draw_axes(
        self, margin_left: int, margin_top: int, width: int, height: int
    ) -> None:
        """Draw X and Y axes."""
        # Y-axis (vertical)
        self.create_line(
            margin_left,
            margin_top,
            margin_left,
            margin_top + height,
            fill=self._colors["axis"],
            width=2,
            tags="axis",
        )

        # X-axis (horizontal)
        self.create_line(
            margin_left,
            margin_top + height,
            margin_left + width,
            margin_top + height,
            fill=self._colors["axis"],
            width=2,
            tags="axis",
        )

        # Y-axis labels (0%, 25%, 50%, 75%, 100%)
        for i, percent in enumerate([0, 25, 50, 75, 100]):
            y = margin_top + height - (i * height / 4)
            self.create_text(
                margin_left - 10,
                y,
                text=f"{percent}%",
                fill=self._colors["text"],
                anchor="e",
                font=("Arial", 9),
                tags="label",
            )

        # Y-axis title
        # Rotate text 90 degrees (not directly supported, use vertical text)
        self.create_text(
            15,
            margin_top + height // 2,
            text="Compression Ratio",
            fill=self._colors["text"],
            anchor="center",
            font=("Arial", 10, "bold"),
            angle=90,
            tags="label",
        )

    def _draw_grid(
        self, margin_left: int, margin_top: int, width: int, height: int
    ) -> None:
        """Draw horizontal grid lines."""
        for i in range(5):  # 0%, 25%, 50%, 75%, 100%
            y = margin_top + height - (i * height / 4)
            self.create_line(
                margin_left,
                y,
                margin_left + width,
                y,
                fill=self._colors["grid"],
                width=1,
                dash=(2, 4),
                tags="grid",
            )

    def _plot_single_point(
        self, margin_left: int, margin_top: int, width: int, height: int
    ) -> None:
        """Plot a single data point as a circle."""
        timestamp, ratio = self._data[0]

        # Position in center horizontally
        x = margin_left + width // 2
        y = margin_top + height - (ratio / 100) * height

        # Draw point
        radius = 5
        self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=self._colors["primary"],
            outline=self._colors["border"],
            width=2,
            tags="point",
        )

        # Draw date label
        date_str = timestamp.strftime("%b %d")
        self.create_text(
            x,
            margin_top + height + 15,
            text=date_str,
            fill=self._colors["text"],
            anchor="n",
            font=("Arial", 9),
            tags="label",
        )

    def _plot_line(
        self, margin_left: int, margin_top: int, width: int, height: int
    ) -> None:
        """Plot connected line through multiple data points."""
        if len(self._data) < 2:
            return

        # Convert data to canvas coordinates
        coords = []
        for timestamp, ratio in self._data:
            # Map timestamp to x position (linear interpolation)
            time_range = (self._data[-1][0] - self._data[0][0]).total_seconds()
            if time_range > 0:
                time_offset = (timestamp - self._data[0][0]).total_seconds()
                x = margin_left + (time_offset / time_range) * width
            else:
                x = margin_left + width // 2

            # Map ratio to y position (0-100% -> height-0)
            y = margin_top + height - (ratio / 100) * height

            coords.extend([x, y])

        # Draw line
        if len(coords) >= 4:  # At least 2 points
            self.create_line(
                *coords,
                fill=self._colors["primary"],
                width=2,
                smooth=True,
                tags="line",
            )

        # Draw points
        for i in range(0, len(coords), 2):
            x, y = coords[i], coords[i + 1]
            radius = 4
            self.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=self._colors["primary"],
                outline=self._colors["border"],
                width=2,
                tags="point",
            )

        # Draw date labels (show first, middle, last)
        label_indices = [0, len(self._data) // 2, len(self._data) - 1]
        for idx in label_indices:
            if idx < len(self._data):
                timestamp, _ = self._data[idx]
                x = coords[idx * 2]
                date_str = timestamp.strftime("%b %d")
                self.create_text(
                    x,
                    margin_top + height + 15,
                    text=date_str,
                    fill=self._colors["text"],
                    anchor="n",
                    font=("Arial", 9),
                    tags="label",
                )

    def _draw_statistics(self, x: int, y: int) -> None:
        """Draw summary statistics below the chart."""
        if not self._data:
            return

        ratios = [ratio for _, ratio in self._data]
        avg_ratio = sum(ratios) / len(ratios)
        best_ratio = max(ratios)
        worst_ratio = min(ratios)

        stats_text = (
            f"Average: {avg_ratio:.1f}%  |  "
            f"Best: {best_ratio:.1f}%  |  "
            f"Worst: {worst_ratio:.1f}%"
        )

        self.create_text(
            x,
            y,
            text=stats_text,
            fill=self._colors["text"],
            anchor="w",
            font=("Arial", 9),
            tags="stats",
        )

    def refresh_theme(self) -> None:
        """Refresh chart colors based on current theme."""
        self._colors = ChartTheme.get_colors()
        self.configure(bg=self._colors["bg"])
        if self._data:
            self._clear()
            self._draw()


class PresetComparisonBar(tk.Canvas):
    """Grouped bar chart comparing average compression by preset.

    Displays bars for each preset showing average compression ratio,
    file count, and total bytes saved.

    Example:
        >>> chart = PresetComparisonBar(parent, width=600, height=250)
        >>> stats = {
        ...     "small": {"avg_ratio": 65.2, "count": 15, "total_saved_mb": 45.3},
        ...     "medium": {"avg_ratio": 58.1, "count": 22, "total_saved_mb": 38.7}
        ... }
        >>> chart.set_data(stats)
        >>> chart.pack(padx=20, pady=20)
    """

    def __init__(self, parent, width: int = 600, height: int = 250, **kwargs):
        """Initialize preset comparison chart.

        Args:
            parent: Parent widget
            width: Canvas width in pixels (default 600)
            height: Canvas height in pixels (default 250)
            **kwargs: Additional canvas options
        """
        colors = ChartTheme.get_colors()
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=colors["bg"],
            highlightthickness=0,
            **kwargs,
        )
        self._colors = colors
        self._data: Dict[str, Dict[str, float]] = {}

    def set_data(self, stats: Dict[str, Dict[str, float]]) -> None:
        """Display bars for each preset's statistics.

        Args:
            stats: Dictionary mapping preset names to statistics:
                {
                    "small": {
                        "avg_ratio": 65.2,
                        "count": 15,
                        "total_saved_mb": 45.3
                    },
                    ...
                }

        Example:
            >>> stats = {
            ...     "small": {"avg_ratio": 65.2, "count": 15},
            ...     "medium": {"avg_ratio": 58.1, "count": 22}
            ... }
            >>> chart.set_data(stats)
        """
        self._data = stats
        self._clear()
        self._draw()

    def _clear(self) -> None:
        """Clear all canvas items."""
        self.delete("all")

    def _draw(self) -> None:
        """Draw the preset comparison bars."""
        if not self._data:
            self._show_empty_state()
            return

        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()

        # Use requested dimensions if not yet realized
        if canvas_width <= 1:
            canvas_width = int(self.cget("width"))
        if canvas_height <= 1:
            canvas_height = int(self.cget("height"))

        # Layout constants
        margin_left = 60
        margin_right = 20
        margin_top = 30
        margin_bottom = 80

        plot_width = canvas_width - margin_left - margin_right
        plot_height = canvas_height - margin_top - margin_bottom

        # Draw axes
        self._draw_axes(margin_left, margin_top, plot_width, plot_height)

        # Draw bars
        self._draw_bars(margin_left, margin_top, plot_width, plot_height)

    def _show_empty_state(self) -> None:
        """Display message when no data available."""
        canvas_width = int(self.cget("width"))
        canvas_height = int(self.cget("height"))

        self.create_text(
            canvas_width // 2,
            canvas_height // 2,
            text="No preset statistics available",
            fill=self._colors["text"],
            font=("Arial", 12, "italic"),
            tags="empty",
        )

    def _draw_axes(
        self, margin_left: int, margin_top: int, width: int, height: int
    ) -> None:
        """Draw axes and labels."""
        # Y-axis (vertical)
        self.create_line(
            margin_left,
            margin_top,
            margin_left,
            margin_top + height,
            fill=self._colors["axis"],
            width=2,
            tags="axis",
        )

        # X-axis (horizontal)
        self.create_line(
            margin_left,
            margin_top + height,
            margin_left + width,
            margin_top + height,
            fill=self._colors["axis"],
            width=2,
            tags="axis",
        )

        # Y-axis labels (0%, 25%, 50%, 75%, 100%)
        for i, percent in enumerate([0, 25, 50, 75, 100]):
            y = margin_top + height - (i * height / 4)
            self.create_text(
                margin_left - 10,
                y,
                text=f"{percent}%",
                fill=self._colors["text"],
                anchor="e",
                font=("Arial", 9),
                tags="label",
            )

        # Y-axis title
        self.create_text(
            15,
            margin_top + height // 2,
            text="Avg Compression Ratio",
            fill=self._colors["text"],
            anchor="center",
            font=("Arial", 10, "bold"),
            angle=90,
            tags="label",
        )

    def _draw_bars(
        self, margin_left: int, margin_top: int, width: int, height: int
    ) -> None:
        """Draw bars for each preset."""
        if not self._data:
            return

        preset_count = len(self._data)
        bar_width = min(80, width // (preset_count + 1))
        spacing = (width - (bar_width * preset_count)) / (preset_count + 1)

        # Sort presets by average ratio (descending)
        sorted_presets = sorted(
            self._data.items(), key=lambda x: x[1].get("avg_ratio", 0), reverse=True
        )

        for i, (preset_name, stats) in enumerate(sorted_presets):
            avg_ratio = stats.get("avg_ratio", 0)
            count = stats.get("count", 0)
            saved_mb = stats.get("total_saved_mb", 0)

            # Calculate bar position
            x = margin_left + spacing + i * (bar_width + spacing)
            bar_height = (avg_ratio / 100) * height
            y = margin_top + height - bar_height

            # Draw bar
            self.create_rectangle(
                x,
                y,
                x + bar_width,
                margin_top + height,
                fill=self._colors["primary"],
                outline=self._colors["border"],
                width=2,
                tags="bar",
            )

            # Draw ratio percentage on bar
            self.create_text(
                x + bar_width // 2,
                y - 10,
                text=f"{avg_ratio:.1f}%",
                fill=self._colors["text"],
                anchor="s",
                font=("Arial", 10, "bold"),
                tags="label",
            )

            # Draw preset name below axis
            self.create_text(
                x + bar_width // 2,
                margin_top + height + 15,
                text=preset_name.capitalize(),
                fill=self._colors["text"],
                anchor="n",
                font=("Arial", 10, "bold"),
                tags="label",
            )

            # Draw statistics below preset name
            stats_text = f"{count} files\n{saved_mb:.1f} MB saved"
            self.create_text(
                x + bar_width // 2,
                margin_top + height + 35,
                text=stats_text,
                fill=self._colors["text"],
                anchor="n",
                font=("Arial", 8),
                tags="label",
            )

    def refresh_theme(self) -> None:
        """Refresh chart colors based on current theme."""
        self._colors = ChartTheme.get_colors()
        self.configure(bg=self._colors["bg"])
        if self._data:
            self._clear()
            self._draw()
