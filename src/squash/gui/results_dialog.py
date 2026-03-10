"""
Results dialog for Squash PDF Compressor.

Modal dialog displaying compression results with visual before/after comparisons.
"""

import logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from ..core.batch import BatchResult
from .components.charts import ComparisonBarChart
from ._icon import apply_icon

logger = logging.getLogger(__name__)


class ResultsDialog(ctk.CTkToplevel):
    """Modal dialog displaying compression results with visual comparisons.

    Shows:
    - Batch summary statistics (total files, success/failure counts)
    - Per-file comparison charts showing size reduction
    - Total size reduction and compression ratio

    Attributes:
        batch_result: BatchResult from compression operation
    """

    def __init__(self, parent, batch_result: BatchResult):
        """Initialize results dialog.

        Args:
            parent: Parent window (MainWindow)
            batch_result: BatchResult with compression data for all files
        """
        super().__init__(parent)

        self.batch_result = batch_result

        # Configure window
        self.title("Compression Results")
        self.geometry("750x650")
        self.resizable(True, True)

        # Modal settings
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self._center_on_parent(parent)

        # Setup UI
        self._setup_ui()

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())

        apply_icon(self)
        self.focus()

    def _center_on_parent(self, parent) -> None:
        """Center dialog on parent window.

        Args:
            parent: Parent window
        """
        self.update_idletasks()

        # Get parent geometry
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Get dialog size
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # Set position
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self) -> None:
        """Build dialog layout."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header with summary
        self._create_summary_header()

        # Scrollable frame with per-file comparisons
        self._create_file_comparisons()

        # Close button
        self._create_button_frame()

    def _create_summary_header(self) -> None:
        """Create header section with batch summary statistics."""
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Compression Complete",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Summary statistics
        successful = self.batch_result.successful
        failed = self.batch_result.failed
        total = self.batch_result.total_files

        # Calculate size reduction
        original_mb = self.batch_result.total_size_before / (1024 * 1024)
        compressed_mb = self.batch_result.total_size_after / (1024 * 1024)
        saved_mb = original_mb - compressed_mb
        reduction_percent = self.batch_result.total_reduction_percent

        # Build summary text
        if failed == 0:
            status_icon = "✓"
            status_text = f"Successfully compressed {successful} of {total} files"
            status_color = ("green", "#50C878")
        else:
            status_icon = "⚠"
            status_text = (
                f"Compressed {successful} of {total} files ({failed} failed)"
            )
            status_color = ("orange", "#FFA500")

        # Status line
        status_label = ctk.CTkLabel(
            header_frame,
            text=f"{status_icon} {status_text}",
            font=ctk.CTkFont(size=13),
            text_color=status_color,
        )
        status_label.grid(row=1, column=0, padx=20, pady=5, sticky="w")

        # Size reduction line
        size_text = (
            f"Total reduction: {saved_mb:.1f} MB "
            f"({original_mb:.1f} MB → {compressed_mb:.1f} MB)"
        )
        size_label = ctk.CTkLabel(
            header_frame, text=size_text, font=ctk.CTkFont(size=12)
        )
        size_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        # Compression ratio line
        ratio_text = f"Average compression ratio: {reduction_percent:.1f}%"
        ratio_label = ctk.CTkLabel(
            header_frame, text=ratio_text, font=ctk.CTkFont(size=12)
        )
        ratio_label.grid(row=3, column=0, padx=20, pady=5, sticky="w")

        # Duration line
        duration_text = f"Duration: {self.batch_result.duration:.1f} seconds"
        duration_label = ctk.CTkLabel(
            header_frame,
            text=duration_text,
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray40"),
        )
        duration_label.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="w")

    def _create_file_comparisons(self) -> None:
        """Create scrollable list of per-file comparison charts."""
        # Label
        label = ctk.CTkLabel(
            self,
            text="File-by-File Comparison:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        label.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="w")

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(self, height=350)
        scroll_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        # Add comparison chart for each file
        chart_count = 0
        for result in self.batch_result.file_results:
            if result.success and result.compressed_size is not None:
                # Create frame for this file's chart
                chart_frame = ctk.CTkFrame(scroll_frame, corner_radius=8)
                chart_frame.grid(
                    row=chart_count, column=0, padx=5, pady=8, sticky="ew"
                )
                chart_frame.grid_columnconfigure(0, weight=1)

                # Warn if output is larger than input
                if getattr(result, "size_increased", False):
                    warn_label = ctk.CTkLabel(
                        chart_frame,
                        text="⚠ Output is larger than input — this PDF may already be optimised",
                        font=ctk.CTkFont(size=11),
                        text_color=("orange", "#FFA500"),
                    )
                    warn_label.grid(row=0, column=0, padx=15, pady=(10, 0), sticky="w")

                # Create comparison chart
                try:
                    filename = Path(result.input_path).name
                    chart = ComparisonBarChart(chart_frame, width=680, height=90)
                    chart.set_data(
                        result.original_size, result.compressed_size, filename
                    )
                    chart.grid(row=1, column=0, padx=15, pady=15, sticky="ew")

                    chart_count += 1

                except Exception as e:
                    logger.error(f"Failed to create chart for {result.input_path}: {e}")
                    # Show error label instead
                    error_label = ctk.CTkLabel(
                        chart_frame,
                        text=f"Error displaying chart for {Path(result.input_path).name}",
                        text_color=("red", "#E74C3C"),
                    )
                    error_label.grid(row=1, column=0, padx=15, pady=10)

            elif not result.success:
                # Show failed file
                failed_frame = ctk.CTkFrame(
                    scroll_frame, corner_radius=8, fg_color=("gray90", "gray20")
                )
                failed_frame.grid(
                    row=chart_count, column=0, padx=5, pady=8, sticky="ew"
                )

                filename = Path(result.input_path).name
                error_msg = result.error_message or "Unknown error"

                fail_label = ctk.CTkLabel(
                    failed_frame,
                    text=f"✗ {filename} - Failed: {error_msg}",
                    text_color=("red", "#E74C3C"),
                    font=ctk.CTkFont(size=11),
                )
                fail_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")

                chart_count += 1

        # Show message if no charts to display
        if chart_count == 0:
            no_results_label = ctk.CTkLabel(
                scroll_frame,
                text="No compression results to display",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color=("gray60", "gray40"),
            )
            no_results_label.grid(row=0, column=0, padx=20, pady=20)

    def _create_button_frame(self) -> None:
        """Create button frame with Close button."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        # Close button (right-aligned)
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=120,
            height=36,
            font=ctk.CTkFont(size=13),
        )
        close_button.grid(row=0, column=1, padx=5)
