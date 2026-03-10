"""
Enhanced progress tracker component for Squash PDF Compressor.

Provides real-time per-file progress tracking with speed metrics and ETA.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk

from ...core.compression import CompressionResult

logger = logging.getLogger(__name__)


@dataclass
class ProgressMetrics:
    """Real-time compression metrics.

    Attributes:
        speed_mbps: Current compression speed in megabytes per second
        eta_seconds: Estimated time remaining in seconds
        bytes_processed: Total bytes processed so far
        bytes_remaining: Bytes left to process
    """

    speed_mbps: float
    eta_seconds: float
    bytes_processed: int
    bytes_remaining: int


class EnhancedProgressTracker(ctk.CTkFrame):
    """Enhanced progress widget with per-file tracking and metrics.

    Displays:
    - Current file being processed
    - Overall progress bar with percentage
    - Speed (MB/s) and ETA
    - Scrollable list of all files with status icons

    Example:
        >>> tracker = EnhancedProgressTracker(parent)
        >>> tracker.grid(row=4, column=0, sticky="ew")
        >>> tracker.start_batch([Path("file1.pdf"), Path("file2.pdf")])
        >>> tracker.update_progress(...)
        >>> tracker.mark_complete(Path("file1.pdf"), result)
        >>> tracker.reset()
    """

    def __init__(self, parent):
        """Initialize progress tracker widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.current_file: Optional[Path] = None
        self.file_list: List[Path] = []
        self.file_widgets: Dict[Path, Dict[str, ctk.CTkLabel]] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build widget layout."""
        self.grid_columnconfigure(0, weight=1)

        # Current file label
        self.current_label = ctk.CTkLabel(
            self, text="Current: --", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.current_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # Progress bar with percentage
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="0%", width=50)
        self.progress_label.grid(row=0, column=1)

        # Metrics (speed + ETA)
        self.metrics_label = ctk.CTkLabel(
            self, text="Speed: -- MB/s  |  ETA: --", font=ctk.CTkFont(size=10)
        )
        self.metrics_label.grid(row=2, column=0, padx=10, pady=2, sticky="w")

        # File list (scrollable)
        self.file_list_frame = ctk.CTkScrollableFrame(
            self, height=150, fg_color="transparent"
        )
        self.file_list_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        self.file_list_frame.grid_columnconfigure(1, weight=1)

    def start_batch(self, files: List[Path]) -> None:
        """Initialize progress tracking for batch.

        Args:
            files: List of files to be processed
        """
        self.file_list = files
        self.current_file = None
        self._create_file_items()

    def _create_file_items(self) -> None:
        """Create status items for each file."""
        # Clear existing widgets
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        self.file_widgets.clear()

        # Create item for each file
        max_display = 10  # Show first 10 files
        for i, file_path in enumerate(self.file_list[:max_display]):
            # Status icon
            icon_label = ctk.CTkLabel(self.file_list_frame, text="⏸", width=30)
            icon_label.grid(row=i, column=0, padx=5, pady=2, sticky="w")

            # Filename
            name_label = ctk.CTkLabel(
                self.file_list_frame, text=file_path.name, anchor="w"
            )
            name_label.grid(row=i, column=1, padx=5, pady=2, sticky="w")

            # Result label (empty initially)
            result_label = ctk.CTkLabel(
                self.file_list_frame, text="Waiting...", width=250, anchor="w"
            )
            result_label.grid(row=i, column=2, padx=5, pady=2, sticky="w")

            self.file_widgets[file_path] = {
                "icon": icon_label,
                "name": name_label,
                "result": result_label,
            }

        # Show "... and N more files" if needed
        if len(self.file_list) > max_display:
            remaining = len(self.file_list) - max_display
            more_label = ctk.CTkLabel(
                self.file_list_frame,
                text=f"... and {remaining} more files",
                font=ctk.CTkFont(size=10, slant="italic"),
                text_color=("gray60", "gray40"),
            )
            more_label.grid(row=max_display, column=0, columnspan=3, pady=5, sticky="w")

    def update_progress(
        self,
        current_file: Path,
        file_progress: float,
        overall_progress: float,
        metrics: ProgressMetrics,
    ) -> None:
        """Update progress display with current status.

        Args:
            current_file: File currently being processed
            file_progress: Progress for current file (0.0-1.0)
            overall_progress: Overall batch progress (0.0-1.0)
            metrics: Speed and ETA metrics
        """
        # Update current file
        if current_file != self.current_file:
            self.current_file = current_file
            filename = current_file.name
            if len(filename) > 50:
                filename = filename[:47] + "..."
            self.current_label.configure(text=f"Current: {filename}")

            # Update file list icon
            if current_file in self.file_widgets:
                self.file_widgets[current_file]["icon"].configure(text="⏳")
                self.file_widgets[current_file]["result"].configure(text="Processing...")

        # Update progress bar
        self.progress_bar.set(overall_progress)
        self.progress_label.configure(text=f"{overall_progress*100:.0f}%")

        # Update metrics
        if metrics.eta_seconds > 60:
            eta_text = f"{int(metrics.eta_seconds / 60)}m {int(metrics.eta_seconds % 60)}s"
        else:
            eta_text = f"{int(metrics.eta_seconds)}s"

        self.metrics_label.configure(
            text=f"Speed: {metrics.speed_mbps:.1f} MB/s  |  ETA: {eta_text} remaining"
        )

    def mark_complete(self, file_path: Path, result: CompressionResult) -> None:
        """Mark file as complete with results.

        Args:
            file_path: Completed file path
            result: CompressionResult with size information
        """
        if file_path not in self.file_widgets:
            return

        widgets = self.file_widgets[file_path]
        widgets["icon"].configure(text="✓")

        # Format result
        if result.success and result.compressed_size is not None:
            orig_mb = result.original_size / (1024 * 1024)
            comp_mb = result.compressed_size / (1024 * 1024)
            ratio = result.reduction_percent if result.reduction_percent else 0

            result_text = f"{orig_mb:.1f} MB → {comp_mb:.1f} MB ({ratio:.0f}%)"
            widgets["result"].configure(
                text=result_text, text_color=("green", "#50C878")
            )
        else:
            widgets["result"].configure(
                text="Completed", text_color=("green", "#50C878")
            )

    def mark_failed(self, file_path: Path, error: str) -> None:
        """Mark file as failed with error.

        Args:
            file_path: Failed file path
            error: Error message
        """
        if file_path not in self.file_widgets:
            return

        widgets = self.file_widgets[file_path]
        widgets["icon"].configure(text="✗")

        # Truncate long error messages
        if len(error) > 30:
            error = error[:27] + "..."

        widgets["result"].configure(
            text=f"Failed: {error}", text_color=("red", "#E74C3C")
        )

    def reset(self) -> None:
        """Clear all progress and reset to initial state."""
        self.current_file = None
        self.file_list.clear()
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.current_label.configure(text="Current: --")
        self.metrics_label.configure(text="Speed: -- MB/s  |  ETA: --")

        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        self.file_widgets.clear()
