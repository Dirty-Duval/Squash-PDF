"""
History dialog for Squash PDF Compressor.

Modal dialog displaying compression history with search and statistics.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import customtkinter as ctk

from ..utils.history import HistoryEntry, HistoryManager
from ._icon import apply_icon

logger = logging.getLogger(__name__)


class HistoryDialog(ctk.CTkToplevel):
    """Modal dialog displaying compression history.

    Shows the last 50 compression operations with:
    - Date/time, filename, preset, sizes, and reduction percentage
    - Search functionality to filter by filename
    - Statistics showing total files and bytes saved
    - Clear history button with confirmation
    - Close button to dismiss dialog

    Attributes:
        history_manager: HistoryManager instance for database access
        current_entries: Currently displayed history entries
        search_var: StringVar for search entry
    """

    def __init__(self, parent, history_manager: HistoryManager):
        """Initialize history dialog.

        Args:
            parent: Parent window (MainWindow)
            history_manager: HistoryManager instance for database access
        """
        super().__init__(parent)

        self.history_manager = history_manager
        self.current_entries: List[HistoryEntry] = []
        self.search_var = ctk.StringVar()

        # Configure window
        self.title("Compression History")
        self.geometry("900x600")
        self.resizable(True, True)

        # Center on parent
        self._center_on_parent(parent)

        # Set up UI
        self._setup_ui()

        # Load history
        self._load_history()

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self.destroy())

        # Make modal
        self.transient(parent)
        self.grab_set()

        apply_icon(self)
        logger.info("History dialog opened")

    def _center_on_parent(self, parent) -> None:
        """Center dialog on parent window.

        Args:
            parent: Parent window
        """
        self.update_idletasks()

        # Get parent position and size
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Get dialog size
        dialog_width = self.winfo_reqwidth()
        dialog_height = self.winfo_reqheight()

        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"+{x}+{y}")

    def _setup_ui(self) -> None:
        """Set up dialog UI components with tabbed interface."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self._create_header()

        # Tabbed interface
        self.tabview = ctk.CTkTabview(self, width=850, height=480)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # Tab 1: History table (existing functionality)
        self.tab_history = self.tabview.add("History")
        self._create_history_tab()

        # Tab 2: Trend chart
        self.tab_trends = self.tabview.add("Trends")
        self._create_trends_tab()

        # Tab 3: Preset comparison
        self.tab_presets = self.tabview.add("Presets")
        self._create_presets_tab()

        # Statistics frame (below tabs)
        self._create_statistics_frame()

        # Button frame
        self._create_button_frame()

    def _create_header(self) -> None:
        """Create header with title."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame, text="Compression History", font=("", 18, "bold")
        )
        title_label.pack(side="left")

    def _create_search_frame(self) -> None:
        """Create search input and button."""
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        # Search label
        search_label = ctk.CTkLabel(search_frame, text="Search:")
        search_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # Search entry
        self.search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var, placeholder_text="Enter filename to search..."
        )
        self.search_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._perform_search())

        # Search button
        search_button = ctk.CTkButton(
            search_frame, text="Search", command=self._perform_search, width=100
        )
        search_button.grid(row=0, column=2, padx=5)

        # Clear search button
        clear_search_button = ctk.CTkButton(
            search_frame, text="Clear", command=self._clear_search, width=80
        )
        clear_search_button.grid(row=0, column=3, padx=5)

    def _create_history_table(self) -> None:
        """Create scrollable history table."""
        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        # Table textbox (scrollable, read-only)
        self.table_text = ctk.CTkTextbox(table_frame, wrap="none", font=("Courier New", 10))
        self.table_text.grid(row=0, column=0, sticky="nsew")

    def _create_statistics_frame(self) -> None:
        """Create statistics display."""
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # Statistics labels
        self.stats_label = ctk.CTkLabel(
            stats_frame, text="Loading statistics...", font=("", 11)
        )
        self.stats_label.pack(side="left")

    def _create_button_frame(self) -> None:
        """Create bottom button frame."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")

        # Clear history button (left)
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear History",
            command=self._confirm_clear_history,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            width=120,
        )
        self.clear_button.pack(side="left")

        # Close button (right)
        close_button = ctk.CTkButton(
            button_frame, text="Close", command=self.destroy, width=100
        )
        close_button.pack(side="right")

    def _create_history_tab(self) -> None:
        """Create history table tab with search and table."""
        # Configure grid for history tab
        self.tab_history.grid_columnconfigure(0, weight=1)
        self.tab_history.grid_rowconfigure(1, weight=1)

        # Search frame in tab
        self._create_search_frame_in_tab()

        # Table in tab
        self._create_history_table_in_tab()

    def _create_search_frame_in_tab(self) -> None:
        """Create search input and button in history tab."""
        search_frame = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        search_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        search_frame.grid_columnconfigure(1, weight=1)

        # Search label
        search_label = ctk.CTkLabel(search_frame, text="Search:")
        search_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # Search entry
        self.search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var, placeholder_text="Enter filename to search..."
        )
        self.search_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._perform_search())

        # Search button
        search_button = ctk.CTkButton(
            search_frame, text="Search", command=self._perform_search, width=100
        )
        search_button.grid(row=0, column=2, padx=5)

        # Clear search button
        clear_search_button = ctk.CTkButton(
            search_frame, text="Clear", command=self._clear_search, width=80
        )
        clear_search_button.grid(row=0, column=3, padx=5)

    def _create_history_table_in_tab(self) -> None:
        """Create scrollable history table in history tab."""
        table_frame = ctk.CTkFrame(self.tab_history)
        table_frame.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        # Table textbox (scrollable, read-only)
        self.table_text = ctk.CTkTextbox(table_frame, wrap="none", font=("Courier New", 10))
        self.table_text.grid(row=0, column=0, sticky="nsew")

    def _create_trends_tab(self) -> None:
        """Create trend chart tab."""
        # Configure grid
        self.tab_trends.grid_columnconfigure(0, weight=1)
        self.tab_trends.grid_rowconfigure(0, weight=1)

        # Create trend chart
        try:
            from .components.charts import TrendLineChart

            self.trend_chart = TrendLineChart(self.tab_trends, width=820, height=400)
            self.trend_chart.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

            # Load trend data
            trend_data = self.history_manager.get_trend_data(days=30)
            self.trend_chart.set_data(trend_data)

            logger.debug(f"Loaded trend chart with {len(trend_data)} data points")

        except Exception as e:
            logger.error(f"Failed to create trend chart: {e}")
            # Show error message
            error_label = ctk.CTkLabel(
                self.tab_trends,
                text=f"Error loading trend chart:\n{str(e)}",
                font=("Arial", 12),
                text_color=("red", "#E74C3C"),
            )
            error_label.grid(row=0, column=0, padx=20, pady=20)

    def _create_presets_tab(self) -> None:
        """Create preset comparison tab."""
        # Configure grid
        self.tab_presets.grid_columnconfigure(0, weight=1)
        self.tab_presets.grid_rowconfigure(0, weight=1)

        # Create preset comparison chart
        try:
            from .components.charts import PresetComparisonBar

            self.preset_chart = PresetComparisonBar(self.tab_presets, width=820, height=400)
            self.preset_chart.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

            # Load preset statistics
            stats = self.history_manager.get_preset_statistics()
            self.preset_chart.set_data(stats)

            logger.debug(f"Loaded preset chart with {len(stats)} presets")

        except Exception as e:
            logger.error(f"Failed to create preset chart: {e}")
            # Show error message
            error_label = ctk.CTkLabel(
                self.tab_presets,
                text=f"Error loading preset chart:\n{str(e)}",
                font=("Arial", 12),
                text_color=("red", "#E74C3C"),
            )
            error_label.grid(row=0, column=0, padx=20, pady=20)

    def _load_history(self, entries: Optional[List[HistoryEntry]] = None) -> None:
        """Load and display history entries.

        Args:
            entries: Optional list of entries to display. If None, loads recent entries.
        """
        try:
            # Get entries
            if entries is None:
                self.current_entries = self.history_manager.get_recent()
            else:
                self.current_entries = entries

            # Clear table
            self.table_text.configure(state="normal")
            self.table_text.delete("1.0", "end")

            if not self.current_entries:
                self.table_text.insert("1.0", "No history entries found.\n\n")
                self.table_text.insert("end", "Compress some files to see them appear here!")
                self.table_text.configure(state="disabled")
                self._update_statistics()
                return

            # Add header
            header = (
                f"{'Date/Time':<20} {'Filename':<35} {'Preset':<10} "
                f"{'Original':<12} {'Compressed':<12} {'Reduction':<10}\n"
            )
            separator = "=" * 110 + "\n"

            self.table_text.insert("1.0", header)
            self.table_text.insert("end", separator)

            # Add entries
            for entry in self.current_entries:
                timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                filename = Path(entry.input_path).name

                # Truncate long filenames
                if len(filename) > 33:
                    filename = filename[:30] + "..."

                original_mb = entry.original_size / (1024 * 1024)
                compressed_mb = entry.compressed_size / (1024 * 1024)

                # Format sizes
                if original_mb < 1:
                    original_str = f"{entry.original_size / 1024:.1f} KB"
                else:
                    original_str = f"{original_mb:.2f} MB"

                if compressed_mb < 1:
                    compressed_str = f"{entry.compressed_size / 1024:.1f} KB"
                else:
                    compressed_str = f"{compressed_mb:.2f} MB"

                # Format row
                row = (
                    f"{timestamp_str:<20} {filename:<35} {entry.preset_name.capitalize():<10} "
                    f"{original_str:<12} {compressed_str:<12} {entry.compression_ratio:>6.1f}%\n"
                )

                self.table_text.insert("end", row)

            self.table_text.configure(state="disabled")

            # Update statistics
            self._update_statistics()

            logger.debug(f"Displayed {len(self.current_entries)} history entries")

        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            self.table_text.configure(state="normal")
            self.table_text.delete("1.0", "end")
            self.table_text.insert("1.0", f"Error loading history: {str(e)}")
            self.table_text.configure(state="disabled")

    def _update_statistics(self) -> None:
        """Update statistics display."""
        try:
            stats = self.history_manager.get_statistics()

            total_files = stats["total_files"]
            bytes_saved = stats["bytes_saved"]

            # Format bytes saved
            if bytes_saved < 1024:
                saved_str = f"{bytes_saved} bytes"
            elif bytes_saved < 1024 * 1024:
                saved_str = f"{bytes_saved / 1024:.1f} KB"
            elif bytes_saved < 1024 * 1024 * 1024:
                saved_str = f"{bytes_saved / (1024 * 1024):.2f} MB"
            else:
                saved_str = f"{bytes_saved / (1024 * 1024 * 1024):.2f} GB"

            avg_ratio = stats["average_ratio"]

            stats_text = (
                f"Total Files: {total_files}  |  "
                f"Total Saved: {saved_str}  |  "
                f"Average Reduction: {avg_ratio:.1f}%"
            )

            self.stats_label.configure(text=stats_text)

        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            self.stats_label.configure(text="Statistics unavailable")

    def _perform_search(self) -> None:
        """Perform search based on search entry."""
        query = self.search_var.get().strip()

        if not query:
            # Empty search, show all
            self._load_history()
            return

        try:
            results = self.history_manager.search(query)
            self._load_history(entries=results)

            logger.debug(f"Search for '{query}' returned {len(results)} results")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            self._show_error("Search Error", f"Failed to search history: {str(e)}")

    def _clear_search(self) -> None:
        """Clear search and show all history."""
        self.search_var.set("")
        self._load_history()

    def _confirm_clear_history(self) -> None:
        """Show confirmation dialog before clearing history."""
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Clear History")
        dialog.geometry("400x150")
        dialog.resizable(False, False)

        # Center on parent
        dialog.transient(self)
        dialog.grab_set()
        apply_icon(dialog)

        # Calculate center position
        self.update_idletasks()
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()

        dialog_width = 400
        dialog_height = 150

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # Message
        message = ctk.CTkLabel(
            dialog,
            text="Are you sure you want to clear all history?\n\nThis action cannot be undone.",
            font=("", 12),
        )
        message.pack(pady=30, padx=20)

        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        def on_confirm():
            dialog.destroy()
            self._clear_history()

        def on_cancel():
            dialog.destroy()

        cancel_button = ctk.CTkButton(
            button_frame, text="Cancel", command=on_cancel, width=100
        )
        cancel_button.pack(side="left", padx=10)

        confirm_button = ctk.CTkButton(
            button_frame,
            text="Clear History",
            command=on_confirm,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            width=120,
        )
        confirm_button.pack(side="right", padx=10)

        # Keyboard shortcuts
        dialog.bind("<Escape>", lambda e: on_cancel())
        dialog.bind("<Return>", lambda e: on_confirm())

    def _clear_history(self) -> None:
        """Clear all history entries."""
        try:
            success = self.history_manager.clear_history()

            if success:
                logger.info("History cleared by user")
                self._load_history()
            else:
                self._show_error("Clear Failed", "Failed to clear history")

        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            self._show_error("Error", f"Failed to clear history: {str(e)}")

    def _show_error(self, title: str, message: str) -> None:
        """Show error dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.resizable(False, False)

        # Center on parent
        dialog.transient(self)
        dialog.grab_set()
        apply_icon(dialog)

        # Calculate center position
        self.update_idletasks()
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()

        dialog_width = 400
        dialog_height = 150

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # Message
        msg_label = ctk.CTkLabel(dialog, text=message, font=("", 12), wraplength=350)
        msg_label.pack(pady=30, padx=20)

        # OK button
        ok_button = ctk.CTkButton(dialog, text="OK", command=dialog.destroy, width=100)
        ok_button.pack(pady=10)

        # Keyboard shortcut
        dialog.bind("<Return>", lambda e: dialog.destroy())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
