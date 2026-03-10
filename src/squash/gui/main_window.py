"""
Main GUI window for Squash PDF Compressor.
"""

import sys
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import List, Optional
import threading
import logging

from ..core.compression import CompressionEngine
from ..core.batch import BatchProcessor
from ..config.manager import ConfigManager
from ..utils.history import HistoryManager
from ..utils.updater import UpdateChecker
from ._icon import apply_icon

logger = logging.getLogger(__name__)

_APP_MUTEX_NAME = "SquashPDFCompressor"


def _register_app_mutex():
    """Create a named Windows mutex so Inno Setup can locate and close this process.

    The handle is intentionally never released — it is kept alive for the
    lifetime of the process and freed automatically on exit.  Returns None
    on non-Windows platforms or if the call fails.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, _APP_MUTEX_NAME)
        if handle:
            logger.debug(f"Registered app mutex: {_APP_MUTEX_NAME}")
        return handle
    except Exception as exc:
        logger.warning(f"Could not register app mutex: {exc}")
        return None


# Import tkinterdnd2 if available
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
    TkinterDnD = None
    logger.warning("tkinterdnd2 not available - drag-and-drop disabled")

# Create custom CTk class with drag-and-drop support
if DRAG_DROP_AVAILABLE:
    class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        """CustomTkinter window with drag-and-drop support."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    # Fallback to regular CTk if tkinterdnd2 not available
    CTkDnD = ctk.CTk


class MainWindow(CTkDnD):
    """Main application window with drag-and-drop support."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Enable drag-and-drop on the root window if available
        if DRAG_DROP_AVAILABLE:
            try:
                self.drop_target_register(DND_FILES)
            except Exception as e:
                logger.warning(f"Could not enable drag-and-drop: {e}")

        # Initialize components
        self.config_manager = ConfigManager()
        self.config_manager.load_settings()

        try:
            gs_path = self.config_manager.settings.ghostscript_path
            self.engine = CompressionEngine(
                Path(gs_path) if gs_path else None
            )
        except RuntimeError as e:
            self._show_ghostscript_error(str(e))
            self.destroy()
            return

        self.batch_processor = BatchProcessor(self.engine)

        # Initialize history manager
        try:
            self.history_manager = HistoryManager()
            logger.info("History manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize history manager: {e}")
            self.history_manager = None

        # Window configuration
        self.title("Squash - PDF Compressor")
        self.geometry(
            f"{self.config_manager.settings.window_width}x"
            f"{self.config_manager.settings.window_height}"
        )
        self.minsize(600, 500)
        self._set_window_icon()

        # Selected files
        self.selected_files: List[Path] = []

        # Create UI
        self._create_widgets()
        self._setup_drag_drop()

        # Restore window state
        if self.config_manager.settings.window_maximized:
            self.state("zoomed")

        # Register named mutex so Inno Setup's CloseApplications can find this process
        self._mutex_handle = _register_app_mutex()

        # Schedule update check after window is fully visible (3 s delay)
        if self.config_manager.settings.check_updates:
            self.after(3000, self._start_update_check)

        logger.info("Main window initialized")

    def _create_widgets(self):
        """Create GUI widgets."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Squash PDF Compressor",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        # Drop zone frame
        self.drop_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.drop_frame.grid(row=1, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.drop_frame.grid_columnconfigure(0, weight=1)

        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="📁 Drag & Drop PDFs Here\n\nor click to Browse Files",
            font=ctk.CTkFont(size=16),
            height=100,
        )
        self.drop_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.drop_label.bind("<Button-1>", lambda e: self.add_files())

        # File list frame
        self.files_frame = ctk.CTkFrame(self)
        self.files_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.files_frame.grid_columnconfigure(0, weight=1)
        self.files_frame.grid_rowconfigure(1, weight=1)

        self.files_label = ctk.CTkLabel(
            self.files_frame,
            text="Selected Files (0)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.files_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # Scrollable frame for file list
        self.files_list = ctk.CTkScrollableFrame(self.files_frame, height=150)
        self.files_list.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.files_list.grid_columnconfigure(0, weight=1)

        # Quality preset frame
        self.quality_frame = ctk.CTkFrame(self)
        self.quality_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.quality_frame.grid_columnconfigure(1, weight=1)

        self.quality_label = ctk.CTkLabel(
            self.quality_frame,
            text="Quality Preset:",
            font=ctk.CTkFont(size=14),
        )
        self.quality_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Radio buttons for quality (dynamically generated)
        self.quality_var = ctk.StringVar(
            value=self.config_manager.settings.default_preset
        )

        self.quality_radio_frame = ctk.CTkFrame(self.quality_frame, fg_color="transparent")
        self.quality_radio_frame.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Build preset radio buttons dynamically
        self._setup_quality_presets()

        # Manage Presets button
        self.manage_presets_btn = ctk.CTkButton(
            self.quality_frame,
            text="⚙️ Manage Presets",
            width=130,
            command=self._open_preset_editor
        )
        self.manage_presets_btn.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # Enhanced progress tracker (hidden initially)
        from .components.progress_tracker import EnhancedProgressTracker
        self.progress_tracker = EnhancedProgressTracker(self)
        self.progress_tracker.grid_remove()  # Hide initially

        # Simple progress bar (fallback, hidden initially)
        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate")
        self.progress_bar.set(0)

        # Compress button
        self.compress_button = ctk.CTkButton(
            self,
            text="COMPRESS NOW",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            command=self.start_compression,
        )
        self.compress_button.grid(row=4, column=0, padx=20, pady=20, sticky="ew")

        # Status bar
        self.status_frame = ctk.CTkFrame(self, corner_radius=0)
        self.status_frame.grid(row=5, column=0, sticky="ew", padx=0, pady=0)
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready to compress",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # History button
        self.history_button = ctk.CTkButton(
            self.status_frame,
            text="📊",
            width=30,
            command=self.show_history,
        )
        self.history_button.grid(row=0, column=1, padx=5, pady=5)

        # Settings button
        self.settings_button = ctk.CTkButton(
            self.status_frame,
            text="⚙️",
            width=30,
            command=self.open_settings,
        )
        self.settings_button.grid(row=0, column=2, padx=5, pady=5)

        # About button
        self.about_button = ctk.CTkButton(
            self.status_frame,
            text="❓",
            width=30,
            command=self.show_about,
        )
        self.about_button.grid(row=0, column=3, padx=5, pady=5)

        # Check for updates button
        self.update_button = ctk.CTkButton(
            self.status_frame,
            text="↑",
            width=30,
            command=self.check_for_updates,
        )
        self.update_button.grid(row=0, column=4, padx=5, pady=5)

    def _setup_drag_drop(self):
        """Set up drag and drop functionality."""
        if not DRAG_DROP_AVAILABLE:
            logger.info("Drag-and-drop not available - install tkinterdnd2")
            return

        # Register drop zone
        try:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind('<<Drop>>', self._on_drop)
            self.drop_label.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.drop_label.dnd_bind('<<DragLeave>>', self._on_drag_leave)
            logger.info("Drag-and-drop enabled successfully")
        except Exception as e:
            logger.error(f"Failed to enable drag-and-drop: {e}")

    def _on_drop(self, event):
        """Handle file drop event."""
        # Parse dropped files (comes as space-separated string with braces)
        files_str = event.data

        # Handle different formats (Windows uses {} braces for paths with spaces)
        if files_str.startswith('{'):
            # Parse brace-enclosed paths
            files = []
            current = ""
            in_braces = False

            for char in files_str:
                if char == '{':
                    in_braces = True
                    current = ""
                elif char == '}':
                    in_braces = False
                    if current:
                        files.append(current.strip())
                    current = ""
                elif in_braces:
                    current += char
                elif char == ' ' and not in_braces:
                    if current:
                        files.append(current.strip())
                    current = ""
                else:
                    current += char

            if current and not in_braces:
                files.append(current.strip())
        else:
            # Simple space-separated paths
            files = files_str.split()

        # Process dropped files
        valid_files = []
        invalid_files = []

        for file_str in files:
            file_path = Path(file_str)

            # Validate file
            if not file_path.exists():
                invalid_files.append(f"{file_path.name} (not found)")
                continue

            if not file_path.is_file():
                invalid_files.append(f"{file_path.name} (not a file)")
                continue

            if file_path.suffix.lower() != '.pdf':
                invalid_files.append(f"{file_path.name} (not a PDF)")
                continue

            # Add valid file
            if file_path not in self.selected_files:
                valid_files.append(file_path)

        # Update file list
        if valid_files:
            self.selected_files.extend(valid_files)
            self._update_file_list()
            logger.info(f"Added {len(valid_files)} files via drag-and-drop")

        # Show warning for invalid files
        if invalid_files:
            invalid_list = "\n".join(invalid_files[:5])  # Show first 5
            if len(invalid_files) > 5:
                invalid_list += f"\n... and {len(invalid_files) - 5} more"

            self.show_error(
                "Invalid Files",
                f"The following files were not added:\n\n{invalid_list}\n\n"
                f"Only PDF files can be compressed."
            )

        # Reset drop zone appearance
        self._on_drag_leave(None)

        return event.action

    def _on_drag_enter(self, event):
        """Handle drag enter event (visual feedback)."""
        # Change drop zone appearance to indicate ready to drop
        self.drop_label.configure(
            text="📥 Release to Add Files",
            fg_color=("gray75", "gray25")  # Highlighted background
        )
        return event.action

    def _on_drag_leave(self, event):
        """Handle drag leave event (reset visual feedback)."""
        # Reset drop zone appearance
        self.drop_label.configure(
            text="📁 Drag & Drop PDFs Here\n\nor click to Browse Files",
            fg_color="transparent"
        )
        if event:
            return event.action

    def add_files(self):
        """Open file dialog to add PDF files."""
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )

        if files:
            for file in files:
                file_path = Path(file)
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)

            self._update_file_list()
            logger.info(f"Added {len(files)} files")

    def add_folder(self):
        """Open folder dialog to add all PDFs in a folder."""
        folder = filedialog.askdirectory(title="Select folder with PDFs")

        if folder:
            folder_path = Path(folder)
            pdf_files = list(folder_path.glob("*.pdf"))

            for file_path in pdf_files:
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)

            self._update_file_list()
            logger.info(f"Added {len(pdf_files)} files from folder")

    def _update_file_list(self):
        """Update the file list display."""
        # Clear existing list
        for widget in self.files_list.winfo_children():
            widget.destroy()

        # Update label
        total_size = sum(f.stat().st_size for f in self.selected_files)
        total_size_mb = total_size / (1024 * 1024)
        self.files_label.configure(
            text=f"Selected Files ({len(self.selected_files)}) - Total: {total_size_mb:.1f} MB"
        )

        # Add file items
        for idx, file_path in enumerate(self.selected_files):
            file_size = file_path.stat().st_size / (1024 * 1024)

            file_frame = ctk.CTkFrame(self.files_list, fg_color="transparent")
            file_frame.grid(row=idx, column=0, padx=5, pady=2, sticky="ew")
            file_frame.grid_columnconfigure(0, weight=1)

            file_label = ctk.CTkLabel(
                file_frame,
                text=f"📄 {file_path.name}",
                font=ctk.CTkFont(size=12),
                anchor="w",
            )
            file_label.grid(row=0, column=0, padx=5, sticky="w")

            size_label = ctk.CTkLabel(
                file_frame,
                text=f"{file_size:.1f} MB",
                font=ctk.CTkFont(size=11),
            )
            size_label.grid(row=0, column=1, padx=5)

            remove_button = ctk.CTkButton(
                file_frame,
                text="✕",
                width=30,
                command=lambda f=file_path: self.remove_file(f),
            )
            remove_button.grid(row=0, column=2, padx=5)

    def remove_file(self, file_path: Path):
        """Remove file from selected list."""
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            self._update_file_list()

    def start_compression(self):
        """Start compression process."""
        if not self.selected_files:
            self.show_error("No files selected", "Please add PDF files to compress.")
            return

        # Disable UI during compression
        self.compress_button.configure(state="disabled")
        self.status_label.configure(text="Compressing...")

        # Show enhanced progress tracker
        self.progress_tracker.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_tracker.start_batch(self.selected_files)
        self.compress_button.grid(row=5, column=0, padx=20, pady=20, sticky="ew")

        # Start compression in background thread
        preset = self.quality_var.get()
        thread = threading.Thread(target=self._compress_files, args=(preset,))
        thread.daemon = True
        thread.start()

    def _compress_files(self, preset: str):
        """Compress files in background thread with enhanced progress."""

        def progress_callback(
            current: int,
            total: int,
            filename: str,
            file_progress: float = 0.0,
            overall_progress: float = 0.0,
            metrics: dict = None,
        ):
            """Handle progress updates from batch processor."""
            from .components.progress_tracker import ProgressMetrics

            # Update progress tracker
            if metrics and len(self.selected_files) >= current:
                current_file = self.selected_files[current - 1]
                progress_metrics = ProgressMetrics(
                    speed_mbps=metrics.get("speed_mbps", 0.0),
                    eta_seconds=metrics.get("eta_seconds", 0.0),
                    bytes_processed=0,
                    bytes_remaining=0,
                )

                self.after(
                    0,
                    lambda: self.progress_tracker.update_progress(
                        current_file, file_progress, overall_progress, progress_metrics
                    ),
                )

            # Update status label
            self.after(
                0,
                lambda: self.status_label.configure(
                    text=f"Processing {current}/{total}: {filename}"
                ),
            )

        try:
            # Run batch compression
            result = self.batch_processor.process_batch(
                self.selected_files,
                preset=preset,
                progress_callback=progress_callback,
            )

            # Mark completed files in tracker
            for file_result in result.file_results:
                file_path = Path(file_result.input_path)
                if file_result.success:
                    self.after(
                        0,
                        lambda fp=file_path, fr=file_result: self.progress_tracker.mark_complete(
                            fp, fr
                        ),
                    )
                else:
                    error_msg = file_result.error_message or "Unknown error"
                    self.after(
                        0,
                        lambda fp=file_path, em=error_msg: self.progress_tracker.mark_failed(
                            fp, em
                        ),
                    )

            # Update UI on completion
            self.after(0, lambda: self._on_compression_complete(result))

        except Exception as e:
            logger.error(f"Compression error: {e}")
            self.after(
                0,
                lambda: self.show_error("Compression Error", f"An error occurred: {str(e)}"),
            )
            self.after(0, self._reset_ui)

    def _on_compression_complete(self, result):
        """Handle compression completion."""
        self._reset_ui()

        # Record successful compressions to history
        if self.history_manager:
            try:
                successful_results = [
                    r for r in result.file_results if r.success
                ]
                if successful_results:
                    self.history_manager.add_entries(successful_results)
                    logger.info(f"Recorded {len(successful_results)} entries to history")
            except Exception as e:
                logger.error(f"Failed to record history: {e}")

        # Show ResultsDialog with visual comparisons
        try:
            from .results_dialog import ResultsDialog
            dialog = ResultsDialog(self, result)
            dialog.grab_set()
            self.wait_window(dialog)
        except Exception as e:
            logger.error(f"Failed to show results dialog: {e}")
            # Fallback to simple success dialog
            self._show_simple_success(result)

        # Clear file list
        self.selected_files.clear()
        self._update_file_list()

    def _show_simple_success(self, result):
        """Fallback simple success dialog when ResultsDialog fails.

        Args:
            result: BatchResult from compression
        """
        saved_mb = (result.total_size_before - result.total_size_after) / (1024 * 1024)
        message = (
            f"Successfully compressed {result.successful} of {result.total_files} files!\n\n"
            f"Total size reduced: {saved_mb:.1f} MB ({result.total_reduction_percent:.1f}%)\n"
            f"Duration: {result.duration:.1f} seconds"
        )

        if result.failed > 0:
            message += f"\n\n⚠️ {result.failed} file(s) failed to compress."

        self.show_success("Compression Complete", message)

    def _reset_ui(self):
        """Reset UI after compression."""
        self.compress_button.configure(state="normal")
        self.compress_button.grid(row=4, column=0, padx=20, pady=20, sticky="ew")
        self.progress_tracker.grid_remove()
        self.progress_tracker.reset()
        self.progress_bar.grid_remove()
        self.status_label.configure(text="Ready to compress")

    def open_settings(self):
        """Open settings dialog."""
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(self, self.config_manager)
        dialog.grab_set()  # Make modal
        self.wait_window(dialog)  # Wait for close

        # Apply theme change if modified
        theme = self.config_manager.get("theme", "system")
        ctk.set_appearance_mode(theme.capitalize())

    def show_history(self):
        """Open compression history dialog."""
        if not self.history_manager:
            self.show_error(
                "History Unavailable",
                "History tracking is not available.\n\nPlease check the logs for more information."
            )
            return

        try:
            from .history_dialog import HistoryDialog
            dialog = HistoryDialog(self, self.history_manager)
            dialog.grab_set()
            self.wait_window(dialog)
        except Exception as e:
            logger.error(f"Failed to open history dialog: {e}")
            self.show_error(
                "History Error",
                f"Failed to open history:\n\n{str(e)}"
            )

    def _setup_quality_presets(self) -> None:
        """Build preset radio buttons dynamically from PresetManager."""
        # Clear existing radio buttons
        for widget in self.quality_radio_frame.winfo_children():
            widget.destroy()

        # Get all presets from manager
        presets = self.engine.preset_manager.list_presets()

        # Create radio buttons dynamically
        for i, preset in enumerate(presets):
            radio = ctk.CTkRadioButton(
                self.quality_radio_frame,
                text=f"{preset.display_name} ({preset.dpi} DPI)",
                variable=self.quality_var,
                value=preset.name,
            )
            radio.grid(row=0, column=i, padx=10, sticky="w")

    def _refresh_presets(self) -> None:
        """Reload presets from manager and rebuild UI."""
        # Store current selection
        current_selection = self.quality_var.get()

        # Rebuild preset radio buttons
        self._setup_quality_presets()

        # Restore selection if it still exists
        if current_selection in self.engine.preset_manager.get_preset_names():
            self.quality_var.set(current_selection)
        else:
            # Default to medium if current selection no longer exists
            self.quality_var.set(self.config_manager.settings.default_preset)

        logger.info("Preset list refreshed")

    def _open_preset_editor(self) -> None:
        """Open custom preset editor dialog."""
        try:
            from .preset_editor import PresetEditorDialog

            dialog = PresetEditorDialog(self, self.engine.preset_manager)
            self.wait_window(dialog)  # Wait for dialog to close

            # Refresh presets after dialog closes
            self._refresh_presets()

            logger.info("Preset editor closed, presets refreshed")

        except Exception as e:
            logger.error(f"Error opening preset editor: {e}")
            self.show_error(
                "Preset Editor Error",
                f"Failed to open preset editor:\n\n{str(e)}"
            )

    # ------------------------------------------------------------------ #
    # Update checking                                                      #
    # ------------------------------------------------------------------ #

    def _start_update_check(self) -> None:
        """Kick off a background update check (called once on startup)."""
        checker = UpdateChecker()
        checker.check_async(callback=self._on_update_check_result)

    def _on_update_check_result(self, release, network_error: bool) -> None:
        """Receive update-check result from background thread — bounce to main thread."""
        self.after(0, lambda: self._show_update_dialog_if_needed(release))

    def _show_update_dialog_if_needed(self, release) -> None:
        if release is None:
            logger.debug("Already up to date or check failed silently")
            return
        # Honour "skip this version" preference
        if release.version == self.config_manager.settings.skip_version:
            logger.debug(f"Update {release.version} suppressed by skip_version setting")
            return
        # Highlight the update button as a subtle badge
        self.update_button.configure(
            text="↑ Update",
            fg_color=("darkorange", "#E07B10"),
        )
        from .update_dialog import UpdateDialog
        UpdateDialog(self, release, self.config_manager, quit_callback=self.destroy)

    def check_for_updates(self) -> None:
        """Manually trigger an update check (called from update button)."""
        self.update_button.configure(state="disabled")
        self.status_label.configure(text="Checking for updates…")
        checker = UpdateChecker()
        checker.check_async(callback=self._on_manual_update_result)

    def _on_manual_update_result(self, release, network_error: bool) -> None:
        self.after(0, lambda: self._handle_manual_update_result(release, network_error))

    def _handle_manual_update_result(self, release, network_error: bool) -> None:
        self.update_button.configure(state="normal")
        self.status_label.configure(text="Ready to compress")
        if network_error:
            self.show_error(
                "Update Check Failed",
                "Could not reach GitHub to check for updates.\n"
                "Please check your internet connection and try again.",
            )
            return
        if release is None:
            self.show_info("Up to date", "You already have the latest version of Squash.")
            return
        from .update_dialog import UpdateDialog
        UpdateDialog(self, release, self.config_manager, quit_callback=self.destroy)

    def show_about(self):
        """Show about dialog."""
        about_text = (
            "Squash PDF Compressor v2.0\n\n"
            "Simple, user-friendly PDF compression tool\n\n"
            "Features:\n"
            "• Fast local compression\n"
            "• 100% privacy - no cloud uploads\n"
            "• Multiple quality presets\n\n"
            "License: AGPL-3.0\n"
            "Powered by Ghostscript"
        )
        self.show_info("About Squash", about_text)

    def _set_window_icon(self) -> None:
        """Set the window/taskbar icon to the Squash logo.

        Uses a 200ms delay (self.after) required on Windows so CustomTkinter
        doesn't override the icon after window creation.
        """
        if getattr(sys, "frozen", False):
            # Running as PyInstaller bundle
            icon_path = Path(sys.executable).parent / "_internal" / "assets" / "squash.ico"
        else:
            icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "squash.ico"

        if icon_path.exists():
            self.after(200, lambda: self.iconbitmap(str(icon_path)))
        else:
            logger.debug(f"Window icon not found at {icon_path}")

    def _show_ghostscript_error(self, detail: str) -> None:
        """Show a startup error when Ghostscript cannot be found.

        Args:
            detail: Error detail from RuntimeError
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("Ghostscript Not Found")
        dialog.geometry("480x220")
        dialog.transient(self)
        dialog.grab_set()
        apply_icon(dialog)

        msg = (
            "Squash could not find Ghostscript, which is required for PDF compression.\n\n"
            "Please reinstall the application or set the Ghostscript path in Settings.\n\n"
            f"Detail: {detail}"
        )
        label = ctk.CTkLabel(dialog, text=msg, wraplength=440, justify="left")
        label.pack(padx=20, pady=20)

        button = ctk.CTkButton(dialog, text="OK", command=dialog.destroy)
        button.pack(pady=10)

        dialog.wait_window()

    def show_error(self, title: str, message: str):
        """Show error dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        apply_icon(dialog)

        label = ctk.CTkLabel(dialog, text=f"❌ {message}", wraplength=350)
        label.pack(padx=20, pady=20)

        button = ctk.CTkButton(dialog, text="OK", command=dialog.destroy)
        button.pack(pady=10)

    def show_success(self, title: str, message: str):
        """Show success dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        apply_icon(dialog)

        label = ctk.CTkLabel(dialog, text=f"✅ {message}", wraplength=350)
        label.pack(padx=20, pady=20)

        button = ctk.CTkButton(dialog, text="OK", command=dialog.destroy)
        button.pack(pady=10)

    def show_info(self, title: str, message: str):
        """Show info dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        apply_icon(dialog)

        label = ctk.CTkLabel(dialog, text=message, wraplength=350, justify="left")
        label.pack(padx=20, pady=20)

        button = ctk.CTkButton(dialog, text="OK", command=dialog.destroy)
        button.pack(pady=10)
