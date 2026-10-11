"""
Results dialog for Squash PDF Compressor.

Modal dialog displaying compression results with visual before/after comparisons.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from ..core.batch import BatchResult
from ..utils.filesystem import FileSystemHelper
from ._icon import apply_icon
from .components.charts import ComparisonBarChart
from .dialogs import center_on_parent

logger = logging.getLogger(__name__)

_SUCCESS = ("#43A047", "#50C878")
_WARNING = ("#E08A00", "#FFA500")
_FAILED = ("#C62828", "#E74C3C")
_MUTED = ("gray50", "gray60")


class ResultsDialog(ctk.CTkToplevel):
    """Modal dialog displaying compression results with visual comparisons."""

    def __init__(self, parent, batch_result: BatchResult):
        """
        Args:
            parent: Parent window (MainWindow).
            batch_result: BatchResult with compression data for all files.
        """
        super().__init__(parent)
        self.batch_result = batch_result

        self.title("Compression Results")
        self.geometry("780x680")
        self.minsize(620, 480)
        self.transient(parent)

        self._setup_ui()

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self.destroy())

        apply_icon(self)
        center_on_parent(self, parent)
        self.grab_set()
        self.focus()

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._create_summary_header()
        self._create_file_comparisons()
        self._create_button_frame()

    def _create_summary_header(self) -> None:
        result = self.batch_result
        header = ctk.CTkFrame(self, corner_radius=10)
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = "Compression Cancelled" if result.cancelled else "Compression Complete"
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(15, 5), sticky="w"
        )

        if result.cancelled:
            status_text = (
                f"Stopped after {result.processed} of {result.total_files} file(s): "
                f"{result.successful} compressed, {result.failed} failed, "
                f"{result.skipped} not started"
            )
            status_color = _MUTED
        elif result.failed == 0:
            status_text = (
                f"✓ Successfully compressed {result.successful} of {result.total_files} files"
            )
            status_color = _SUCCESS
        else:
            status_text = (
                f"⚠ Compressed {result.successful} of {result.total_files} files "
                f"({result.failed} failed)"
            )
            status_color = _WARNING

        ctk.CTkLabel(
            header, text=status_text, font=ctk.CTkFont(size=13), text_color=status_color
        ).grid(row=1, column=0, padx=20, pady=5, sticky="w")

        saved = result.total_size_before - result.total_size_after
        before = FileSystemHelper.format_size(result.total_size_before)
        after = FileSystemHelper.format_size(result.total_size_after)
        if saved >= 0:
            size_text = f"Total saved: {FileSystemHelper.format_size(saved)}  ({before} → {after})"
            ratio_text = f"Overall reduction: {result.total_reduction_percent:.1f}%"
        else:
            size_text = (
                f"Total size increased by {FileSystemHelper.format_size(-saved)}  "
                f"({before} → {after})"
            )
            ratio_text = (
                f"Overall change: +{-result.total_reduction_percent:.1f}% "
                "(these PDFs were already well optimised)"
            )
        ctk.CTkLabel(header, text=size_text, font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, padx=20, pady=5, sticky="w"
        )

        ctk.CTkLabel(header, text=ratio_text, font=ctk.CTkFont(size=12)).grid(
            row=3, column=0, padx=20, pady=5, sticky="w"
        )

        ctk.CTkLabel(
            header,
            text=f"Duration: {result.duration:.1f} seconds",
            font=ctk.CTkFont(size=11),
            text_color=_MUTED,
        ).grid(row=4, column=0, padx=20, pady=(5, 15), sticky="w")

    def _create_file_comparisons(self) -> None:
        ctk.CTkLabel(
            self, text="File-by-file comparison", font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=1, column=0, padx=20, pady=(5, 5), sticky="w")

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        row = 0
        for result in self.batch_result.file_results:
            filename = Path(result.input_path).name

            if result.cancelled:
                frame = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("gray90", "gray20"))
                frame.grid(row=row, column=0, padx=5, pady=6, sticky="ew")
                ctk.CTkLabel(
                    frame,
                    text=f"■ {filename} - cancelled",
                    text_color=_MUTED,
                    font=ctk.CTkFont(size=11),
                ).grid(row=0, column=0, padx=15, pady=10, sticky="w")

            elif result.output_discarded:
                frame = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("gray90", "gray20"))
                frame.grid(row=row, column=0, padx=5, pady=6, sticky="ew")
                frame.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(
                    frame,
                    text=f"= {filename}  ({FileSystemHelper.format_size(result.original_size)})",
                    text_color=_WARNING,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    anchor="w",
                ).grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")
                ctk.CTkLabel(
                    frame,
                    text=result.note or "Already optimised; the original was kept.",
                    font=ctk.CTkFont(size=11),
                    text_color=_MUTED,
                    wraplength=640,
                    justify="left",
                    anchor="w",
                ).grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

            elif result.success and result.compressed_size is not None:
                frame = ctk.CTkFrame(scroll, corner_radius=8)
                frame.grid(row=row, column=0, padx=5, pady=6, sticky="ew")
                frame.grid_columnconfigure(0, weight=1)

                if result.size_increased:
                    ctk.CTkLabel(
                        frame,
                        text="⚠ Output is larger than the original - this PDF was already "
                        "well optimised. You may prefer to keep the original.",
                        font=ctk.CTkFont(size=11),
                        text_color=_WARNING,
                        wraplength=640,
                        justify="left",
                    ).grid(row=0, column=0, padx=15, pady=(10, 0), sticky="w")

                try:
                    chart = ComparisonBarChart(frame, width=680, height=92)
                    chart.set_data(result.original_size, result.compressed_size, filename)
                    chart.grid(row=1, column=0, padx=15, pady=12, sticky="ew")
                except Exception as exc:
                    logger.error(f"Failed to create chart for {result.input_path}: {exc}")
                    ctk.CTkLabel(
                        frame,
                        text=f"{filename}: {result.format_sizes()}",
                        font=ctk.CTkFont(size=11),
                    ).grid(row=1, column=0, padx=15, pady=10, sticky="w")

            else:
                frame = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("gray90", "gray20"))
                frame.grid(row=row, column=0, padx=5, pady=6, sticky="ew")
                frame.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(
                    frame,
                    text=f"✕ {filename}",
                    text_color=_FAILED,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    anchor="w",
                ).grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")
                ctk.CTkLabel(
                    frame,
                    text=result.error_message or "Unknown error",
                    text_color=_FAILED,
                    font=ctk.CTkFont(size=11),
                    wraplength=640,
                    justify="left",
                    anchor="w",
                ).grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

            row += 1

        if row == 0:
            ctk.CTkLabel(
                scroll,
                text="No files were processed.",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color=_MUTED,
            ).grid(row=0, column=0, padx=20, pady=20)

    def _create_button_frame(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        bar.grid_columnconfigure(1, weight=1)

        folder = self._output_folder()
        if folder is not None:
            ctk.CTkButton(
                bar,
                text="Open Output Folder",
                width=160,
                fg_color="transparent",
                border_width=1,
                text_color=("#1A1208", "#F0E8DC"),
                command=lambda: FileSystemHelper.open_in_file_manager(folder),
            ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(bar, text="Close", width=120, height=36, command=self.destroy).grid(
            row=0, column=2, sticky="e"
        )

    def _output_folder(self) -> Optional[Path]:
        """Folder containing the first compressed file, if any."""
        for result in self.batch_result.file_results:
            if result.success and result.output_path:
                folder = Path(result.output_path).parent
                if folder.exists():
                    return folder
        return None
