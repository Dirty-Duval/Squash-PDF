"""
Progress tracker component for Squash PDF Compressor.

Shows live batch progress: the current file and page, an overall
byte-weighted progress bar, speed/ETA, and a per-file status list that
fills in as results arrive.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk

from ...core.batch import BatchProgress
from ...core.compression import CompressionResult
from ...utils.filesystem import FileSystemHelper

logger = logging.getLogger(__name__)

_MAX_VISIBLE_FILES = 12
_SUCCESS = ("#43A047", "#50C878")
_WARNING = ("#E08A00", "#FFA500")
_FAILED = ("#C62828", "#E74C3C")
_MUTED = ("gray50", "gray60")


def _shorten(name: str, limit: int = 48) -> str:
    return name if len(name) <= limit else name[: limit - 3] + "..."


def _format_eta(seconds: float) -> str:
    seconds = int(seconds)
    if seconds <= 0:
        return "--"
    if seconds >= 3600:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"


class EnhancedProgressTracker(ctk.CTkFrame):
    """Batch progress widget.

    Example:
        >>> tracker = EnhancedProgressTracker(parent)
        >>> tracker.start_batch([Path("a.pdf"), Path("b.pdf")])
        >>> tracker.update(progress)        # BatchProgress from BatchProcessor
        >>> tracker.mark_result(result)     # CompressionResult per finished file
        >>> tracker.reset()
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.current_file: Optional[Path] = None
        self.file_list: List[Path] = []
        self.file_widgets: Dict[Path, Dict[str, ctk.CTkLabel]] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        self.current_label = ctk.CTkLabel(
            self, text="Preparing...", font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        )
        self.current_label.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")

        # Overall progress
        progress_row = ctk.CTkFrame(self, fg_color="transparent")
        progress_row.grid(row=1, column=0, padx=12, pady=2, sticky="ew")
        progress_row.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(progress_row)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.progress_label = ctk.CTkLabel(progress_row, text="0%", width=48, anchor="e")
        self.progress_label.grid(row=0, column=1)

        # Current-file progress (thin bar)
        self.file_bar = ctk.CTkProgressBar(self, height=4)
        self.file_bar.set(0)
        self.file_bar.grid(row=2, column=0, padx=12, pady=(0, 4), sticky="ew")

        self.metrics_label = ctk.CTkLabel(
            self, text="Speed: -- MB/s  |  ETA: --", font=ctk.CTkFont(size=11), anchor="w"
        )
        self.metrics_label.grid(row=3, column=0, padx=12, pady=(0, 4), sticky="ew")

        self.file_list_frame = ctk.CTkScrollableFrame(self, height=140, fg_color="transparent")
        self.file_list_frame.grid(row=4, column=0, padx=6, pady=(2, 8), sticky="nsew")
        self.file_list_frame.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def start_batch(self, files: List[Path]) -> None:
        """Prepare the widget for a new batch."""
        self.reset()
        self.file_list = list(files)
        self._create_file_items()
        self.current_label.configure(text=f"Starting {len(self.file_list)} file(s)...")

    def update(self, progress: BatchProgress) -> None:
        """Apply a progress snapshot from the batch processor."""
        if progress.path != self.current_file:
            self.current_file = progress.path
            widgets = self.file_widgets.get(progress.path)
            if widgets:
                widgets["icon"].configure(text="▶")
                widgets["result"].configure(text="Processing...", text_color=_MUTED)

        detail = f" ({progress.detail})" if progress.detail and progress.detail != "done" else ""
        self.current_label.configure(
            text=f"File {progress.index} of {progress.total}: "
            f"{_shorten(progress.path.name)}{detail}"
        )
        self.progress_bar.set(progress.overall_progress)
        self.progress_label.configure(text=f"{progress.overall_progress * 100:.0f}%")
        self.file_bar.set(progress.file_progress)

        speed = f"{progress.speed_mbps:.1f} MB/s" if progress.speed_mbps > 0 else "-- MB/s"
        self.metrics_label.configure(
            text=f"Speed: {speed}  |  ETA: {_format_eta(progress.eta_seconds)}"
        )

    def mark_result(self, result: CompressionResult) -> None:
        """Show the outcome for a finished file."""
        widgets = self.file_widgets.get(Path(result.input_path))
        if not widgets:
            return

        if result.cancelled:
            widgets["icon"].configure(text="■")
            widgets["result"].configure(text="Cancelled", text_color=_MUTED)
        elif result.output_discarded:
            widgets["icon"].configure(text="=")
            widgets["result"].configure(
                text="Already optimised, original kept", text_color=_WARNING
            )
        elif result.success and result.compressed_size is not None:
            ratio = result.reduction_percent or 0.0
            text = (
                f"{FileSystemHelper.format_size(result.original_size)} → "
                f"{FileSystemHelper.format_size(result.compressed_size)} ({ratio:.0f}%)"
            )
            if result.size_increased:
                widgets["icon"].configure(text="⚠")
                widgets["result"].configure(text=f"{text} larger", text_color=_WARNING)
            else:
                widgets["icon"].configure(text="✓")
                widgets["result"].configure(text=text, text_color=_SUCCESS)
        else:
            widgets["icon"].configure(text="✕")
            error = result.error_message or "Unknown error"
            widgets["result"].configure(text=f"Failed: {_shorten(error, 60)}", text_color=_FAILED)

    def set_cancelling(self) -> None:
        """Indicate that a cancel request is being honoured."""
        self.current_label.configure(text="Cancelling after the current page...")

    def reset(self) -> None:
        """Clear all progress and return to the initial state."""
        self.current_file = None
        self.file_list = []
        self.progress_bar.set(0)
        self.file_bar.set(0)
        self.progress_label.configure(text="0%")
        self.current_label.configure(text="Preparing...")
        self.metrics_label.configure(text="Speed: -- MB/s  |  ETA: --")
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        self.file_widgets.clear()

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _create_file_items(self) -> None:
        for row, file_path in enumerate(self.file_list[:_MAX_VISIBLE_FILES]):
            icon_label = ctk.CTkLabel(self.file_list_frame, text="•", width=24)
            icon_label.grid(row=row, column=0, padx=(6, 4), pady=1, sticky="w")

            name_label = ctk.CTkLabel(
                self.file_list_frame, text=_shorten(file_path.name, 40), anchor="w"
            )
            name_label.grid(row=row, column=1, padx=4, pady=1, sticky="ew")

            result_label = ctk.CTkLabel(
                self.file_list_frame, text="Waiting", anchor="w", text_color=_MUTED
            )
            result_label.grid(row=row, column=2, padx=(4, 8), pady=1, sticky="w")

            self.file_widgets[file_path] = {
                "icon": icon_label,
                "name": name_label,
                "result": result_label,
            }

        remaining = len(self.file_list) - _MAX_VISIBLE_FILES
        if remaining > 0:
            ctk.CTkLabel(
                self.file_list_frame,
                text=f"... and {remaining} more file(s)",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=_MUTED,
            ).grid(row=_MAX_VISIBLE_FILES, column=0, columnspan=3, padx=8, pady=4, sticky="w")
