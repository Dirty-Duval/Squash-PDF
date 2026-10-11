"""
History dialog for Squash PDF Compressor.

Modal dialog displaying compression history with search, statistics and charts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import customtkinter as ctk

from ..utils.filesystem import FileSystemHelper
from ..utils.history import HistoryEntry, HistoryManager
from ._icon import apply_icon
from .dialogs import ask_yes_no, center_on_parent, show_error

logger = logging.getLogger(__name__)


class HistoryDialog(ctk.CTkToplevel):
    """Tabbed history viewer: table with search, 30-day trend, preset comparison."""

    def __init__(self, parent, history_manager: HistoryManager):
        """
        Args:
            parent: Parent window (MainWindow).
            history_manager: HistoryManager instance for database access.
        """
        super().__init__(parent)
        self.history_manager = history_manager
        self.current_entries: List[HistoryEntry] = []
        self.search_var = ctk.StringVar()

        self.title("Compression History")
        self.geometry("940x640")
        self.minsize(760, 520)
        self.transient(parent)

        self._setup_ui()
        self._load_history()

        self.bind("<Escape>", lambda _e: self.destroy())

        apply_icon(self)
        center_on_parent(self, parent)
        self.grab_set()
        self.focus()

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Compression History", font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.tab_history = self.tabview.add("History")
        self._create_history_tab()

        self.tab_trends = self.tabview.add("Trends")
        self._create_trends_tab()

        self.tab_presets = self.tabview.add("Presets")
        self._create_presets_tab()

        self.stats_label = ctk.CTkLabel(
            self, text="Loading statistics...", font=ctk.CTkFont(size=11)
        )
        self.stats_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        buttons.grid_columnconfigure(1, weight=1)

        self.clear_button = ctk.CTkButton(
            buttons,
            text="Clear History",
            command=self._confirm_clear_history,
            fg_color=("#C62828", "#B71C1C"),
            hover_color=("#B71C1C", "#8E1414"),
            width=130,
        )
        self.clear_button.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(buttons, text="Close", command=self.destroy, width=110).grid(
            row=0, column=2, sticky="e"
        )

    def _create_history_tab(self) -> None:
        tab = self.tab_history
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        search = ctk.CTkFrame(tab, fg_color="transparent")
        search.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        search.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search, text="Search:").grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.search_entry = ctk.CTkEntry(
            search, textvariable=self.search_var, placeholder_text="Filter by file name..."
        )
        self.search_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.search_entry.bind("<Return>", lambda _e: self._perform_search())

        ctk.CTkButton(search, text="Search", command=self._perform_search, width=90).grid(
            row=0, column=2, padx=5
        )
        ctk.CTkButton(
            search,
            text="Clear",
            command=self._clear_search,
            width=70,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
        ).grid(row=0, column=3, padx=5)

        table_frame = ctk.CTkFrame(tab)
        table_frame.grid(row=1, column=0, padx=10, pady=(4, 8), sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.table_text = ctk.CTkTextbox(table_frame, wrap="none", font=("Consolas", 11))
        self.table_text.grid(row=0, column=0, sticky="nsew")

    def _create_trends_tab(self) -> None:
        tab = self.tab_trends
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        try:
            from .components.charts import TrendLineChart

            chart = TrendLineChart(tab, width=840, height=400)
            chart.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
            chart.set_data(self.history_manager.get_trend_data(days=30))
        except Exception as exc:
            logger.error(f"Failed to create trend chart: {exc}")
            ctk.CTkLabel(tab, text=f"Could not load trend chart:\n{exc}").grid(
                row=0, column=0, padx=20, pady=20
            )

    def _create_presets_tab(self) -> None:
        tab = self.tab_presets
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        try:
            from .components.charts import PresetComparisonBar

            chart = PresetComparisonBar(tab, width=840, height=400)
            chart.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
            chart.set_data(self.history_manager.get_preset_statistics())
        except Exception as exc:
            logger.error(f"Failed to create preset chart: {exc}")
            ctk.CTkLabel(tab, text=f"Could not load preset chart:\n{exc}").grid(
                row=0, column=0, padx=20, pady=20
            )

    # ------------------------------------------------------------------ #
    # Data                                                                 #
    # ------------------------------------------------------------------ #

    def _load_history(self, entries: Optional[List[HistoryEntry]] = None) -> None:
        """Fill the table with ``entries`` (or the most recent records)."""
        try:
            self.current_entries = self.history_manager.get_recent() if entries is None else entries

            self.table_text.configure(state="normal")
            self.table_text.delete("1.0", "end")

            if not self.current_entries:
                self.table_text.insert(
                    "1.0",
                    "No history entries found.\n\nCompress some files and they will appear here.",
                )
            else:
                header = (
                    f"{'Date/Time':<20} {'File':<36} {'Preset':<12} "
                    f"{'Original':>10} {'Result':>10} {'Saved':>8}\n"
                )
                self.table_text.insert("1.0", header)
                self.table_text.insert("end", "-" * 102 + "\n")
                for entry in self.current_entries:
                    self.table_text.insert("end", self._format_row(entry))

            self.table_text.configure(state="disabled")
            self._update_statistics()
        except Exception as exc:
            logger.error(f"Failed to load history: {exc}")
            self.table_text.configure(state="normal")
            self.table_text.delete("1.0", "end")
            self.table_text.insert("1.0", f"Error loading history: {exc}")
            self.table_text.configure(state="disabled")

    @staticmethod
    def _format_row(entry: HistoryEntry) -> str:
        when = entry.timestamp.strftime("%Y-%m-%d %H:%M")
        name = Path(entry.input_path).name
        if len(name) > 34:
            name = name[:31] + "..."
        preset = entry.preset_name[:12]
        original = FileSystemHelper.format_size(entry.original_size)
        if entry.success:
            result = FileSystemHelper.format_size(entry.compressed_size)
            saved = f"{entry.compression_ratio:.0f}%"
        else:
            result = "FAILED"
            saved = "--"
        return f"{when:<20} {name:<36} {preset:<12} {original:>10} {result:>10} {saved:>8}\n"

    def _update_statistics(self) -> None:
        try:
            stats = self.history_manager.get_statistics()
            self.stats_label.configure(
                text=(
                    f"Files: {stats['total_files']}   |   "
                    f"Total saved: {FileSystemHelper.format_size(stats['bytes_saved'])}   |   "
                    f"Average reduction: {stats['average_ratio']:.1f}%   |   "
                    f"Success rate: {stats['success_rate']:.0f}%"
                )
            )
        except Exception as exc:
            logger.error(f"Failed to update statistics: {exc}")
            self.stats_label.configure(text="Statistics unavailable")

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #

    def _perform_search(self) -> None:
        query = self.search_var.get().strip()
        if not query:
            self._load_history()
            return
        try:
            self._load_history(entries=self.history_manager.search(query))
        except Exception as exc:
            logger.error(f"Search failed: {exc}")
            show_error(self, "Search Error", f"Failed to search history:\n{exc}")

    def _clear_search(self) -> None:
        self.search_var.set("")
        self._load_history()

    def _confirm_clear_history(self) -> None:
        if not ask_yes_no(
            self,
            "Clear History",
            "Delete all compression history?\n\nThis only removes the records; "
            "your PDF files are not affected.",
            yes_text="Clear History",
            no_text="Cancel",
            danger=True,
        ):
            return
        try:
            if self.history_manager.clear_history():
                logger.info("History cleared by user")
                self._load_history()
            else:
                show_error(self, "Clear Failed", "Failed to clear history.")
        except Exception as exc:
            logger.error(f"Failed to clear history: {exc}")
            show_error(self, "Error", f"Failed to clear history:\n{exc}")
