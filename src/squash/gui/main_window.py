"""
Main GUI window for Squash PDF Compressor.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional, Tuple

import customtkinter as ctk

from .. import APP_NAME, GITHUB_REPO, __version__
from ..config.manager import ConfigManager
from ..core.batch import BatchProcessor, BatchProgress, BatchResult
from ..core.compression import CompressionEngine, CompressionResult
from ..utils.filesystem import FileSystemHelper
from ..utils.history import HistoryManager
from ..utils.updater import UpdateChecker
from ._icon import apply_icon
from .appearance import apply_appearance
from .components.progress_tracker import EnhancedProgressTracker
from .dialogs import ask_yes_no, fit_to_content, show_error, show_info, show_warning

logger = logging.getLogger(__name__)

_APP_MUTEX_NAME = "SquashPDFCompressor"
_UI_QUEUE_POLL_MS = 40
_DROP_IDLE_TEXT = "Drag & drop PDF files here\nor click to browse"
_DROP_ACTIVE_TEXT = "Release to add files"
_DROP_BUSY_TEXT = "Compressing... please wait"
_PROGRESS_THROTTLE_S = 0.05
_PRESETS_PER_ROW = 3
_MUTED = ("gray45", "gray60")


class StartupError(RuntimeError):
    """Raised when the main window cannot start (the user has already been told why)."""


def _register_app_mutex():
    """Create a named Windows mutex so Inno Setup can locate and close this process.

    The handle is intentionally never released - it lives for the lifetime of
    the process. Returns None on non-Windows platforms or if the call fails.
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


# Optional drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DRAG_DROP_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on environment
    DRAG_DROP_AVAILABLE = False
    TkinterDnD = None
    DND_FILES = None
    logger.warning("tkinterdnd2 not available - drag-and-drop disabled")

if DRAG_DROP_AVAILABLE:

    class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        """CustomTkinter root window with drag-and-drop support."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

else:
    CTkDnD = ctk.CTk  # type: ignore[misc,assignment]


class MainWindow(CTkDnD):
    """Main application window."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Args:
            config_manager: Loaded ConfigManager. Created and loaded if omitted.

        Raises:
            StartupError: If Ghostscript cannot be found (after telling the user).
        """
        super().__init__()
        # Do NOT call withdraw() here. CustomTkinter keeps the root hidden until
        # mainloop() on Windows and only reveals it then if withdraw() was never
        # called beforehand; an early withdraw() leaves the app running invisibly.

        self.config_manager = config_manager or ConfigManager()
        if config_manager is None:
            self.config_manager.load_settings()
        settings = self.config_manager.settings

        self.title(APP_NAME)
        apply_icon(self)

        # Work handed over from background threads is executed here, on the Tk
        # thread, by a poller started below. (Calling ``after`` directly from a
        # worker thread only works while the main loop happens to be running.)
        self._ui_queue: "queue.Queue[Tuple[Callable, tuple]]" = queue.Queue()

        # Compression engine (hard requirement)
        try:
            gs_path = Path(settings.ghostscript_path) if settings.ghostscript_path else None
            self.engine = CompressionEngine(gs_path)
        except RuntimeError as exc:
            logger.critical(f"Ghostscript not available: {exc}")
            show_error(
                self,
                "Ghostscript Not Found",
                "Squash needs Ghostscript to compress PDFs, but it could not be found.\n\n"
                "Please reinstall Squash, or install Ghostscript and point to it in "
                f"Settings.\n\nDetail: {exc}",
            )
            self.destroy()
            raise StartupError(str(exc)) from exc

        self.batch_processor = BatchProcessor(self.engine)

        try:
            self.history_manager: Optional[HistoryManager] = HistoryManager()
        except Exception as exc:
            logger.error(f"History unavailable: {exc}")
            self.history_manager = None

        # State
        self.selected_files: List[Path] = []
        self._remove_buttons: List[ctk.CTkButton] = []
        self._compressing = False
        self._cancel_event: Optional[threading.Event] = None
        self._worker: Optional[threading.Thread] = None
        self._last_progress_emit = 0.0

        self._create_widgets()
        self._setup_drag_drop()
        self._refresh_output_hint()
        self._apply_initial_geometry(settings.window_width, settings.window_height)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._bind_shortcuts()
        self._mutex_handle = _register_app_mutex()
        self.after(_UI_QUEUE_POLL_MS, self._drain_ui_queue)

        if settings.window_maximized:
            self.after(0, lambda: self.state("zoomed"))

        if settings.check_updates:
            self.after(3000, self._start_update_check)

        logger.info("Main window initialized")

    # ------------------------------------------------------------------ #
    # Keyboard shortcuts                                                   #
    # ------------------------------------------------------------------ #

    def _bind_shortcuts(self) -> None:
        """Ctrl+O add files, Ctrl+Shift+O add folder, Ctrl+Enter compress, Esc cancel, F1 about."""
        self.bind("<Control-o>", lambda _e: self.add_files())
        self.bind("<Control-O>", lambda _e: self.add_folder())  # Shift held
        self.bind("<Control-Return>", lambda _e: self.start_compression())
        self.bind("<Escape>", lambda _e: self.cancel_compression())
        self.bind("<F1>", lambda _e: self.show_about())

    # ------------------------------------------------------------------ #
    # Thread → UI hand-off                                                 #
    # ------------------------------------------------------------------ #

    def _post(self, func: Callable, *args) -> None:
        """Queue ``func(*args)`` to run on the Tk thread (safe from any thread)."""
        self._ui_queue.put((func, args))

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                func, args = self._ui_queue.get_nowait()
                try:
                    func(*args)
                except Exception:
                    logger.exception("UI callback failed")
        except queue.Empty:
            pass
        try:
            if self.winfo_exists():
                self.after(_UI_QUEUE_POLL_MS, self._drain_ui_queue)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Geometry                                                             #
    # ------------------------------------------------------------------ #

    def _apply_initial_geometry(self, saved_width: int, saved_height: int) -> None:
        """Open large enough that every control is visible, honouring a larger saved size."""
        req_w, req_h = fit_to_content(self)
        self.minsize(req_w, req_h)
        width = max(req_w, saved_width)
        height = max(req_h, saved_height)
        # Keep within the screen; fit_to_content already clamped the required size.
        width = min(width, self.winfo_screenwidth() - 60)
        height = min(height, self.winfo_screenheight() - 60)
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _ensure_content_visible(self) -> None:
        """Grow the window if newly shown widgets (e.g. the progress panel) need room."""
        try:
            if self.state() == "zoomed":
                return
        except Exception:
            return
        fit_to_content(self, grow_only=True)

    # ------------------------------------------------------------------ #
    # Widgets                                                              #
    # ------------------------------------------------------------------ #

    def _create_widgets(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_NAME, font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, padx=20, pady=14, sticky="w"
        )
        ctk.CTkLabel(
            header, text=f"v{__version__}", font=ctk.CTkFont(size=11), text_color=_MUTED
        ).grid(row=0, column=1, padx=20, sticky="e")

        # Drop zone
        self.drop_frame = ctk.CTkFrame(self, corner_radius=12, border_width=2)
        self.drop_frame.grid(row=1, column=0, padx=20, pady=(18, 8), sticky="ew")
        self.drop_frame.grid_columnconfigure(0, weight=1)
        self.drop_label = ctk.CTkLabel(
            self.drop_frame, text=_DROP_IDLE_TEXT, font=ctk.CTkFont(size=15), height=96
        )
        self.drop_label.grid(row=0, column=0, padx=10, pady=6, sticky="ew")
        for widget in (self.drop_frame, self.drop_label):
            widget.bind("<Button-1>", lambda _e: self.add_files())
            widget.configure(cursor="hand2")

        # File toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=2, column=0, padx=20, pady=(4, 2), sticky="ew")
        toolbar.grid_columnconfigure(2, weight=1)
        self.add_files_btn = ctk.CTkButton(
            toolbar, text="Add Files...", width=110, command=self.add_files
        )
        self.add_files_btn.grid(row=0, column=0, padx=(0, 6))
        self.add_folder_btn = ctk.CTkButton(
            toolbar, text="Add Folder...", width=110, command=self.add_folder
        )
        self.add_folder_btn.grid(row=0, column=1)
        self.clear_btn = ctk.CTkButton(
            toolbar,
            text="Clear All",
            width=90,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=self.clear_files,
        )
        self.clear_btn.grid(row=0, column=3, sticky="e")

        # File list (hidden while a batch runs; the progress panel lists the same files)
        self.files_frame = ctk.CTkFrame(self)
        self.files_frame.grid(row=3, column=0, padx=20, pady=6, sticky="nsew")
        self.files_frame.grid_columnconfigure(0, weight=1)
        self.files_frame.grid_rowconfigure(1, weight=1)
        self.files_label = ctk.CTkLabel(
            self.files_frame, text="No files selected", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.files_label.grid(row=0, column=0, padx=12, pady=(8, 4), sticky="w")
        self.files_list = ctk.CTkScrollableFrame(self.files_frame, height=120)
        self.files_list.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self.files_list.grid_columnconfigure(0, weight=1)

        # Quality presets
        self.quality_frame = ctk.CTkFrame(self)
        self.quality_frame.grid(row=4, column=0, padx=20, pady=6, sticky="ew")
        self.quality_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.quality_frame, text="Quality:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=12, pady=10, sticky="nw"
        )
        self.quality_var = ctk.StringVar(value=self.config_manager.settings.default_preset)
        self.quality_var.trace_add("write", lambda *_: self._refresh_preset_description())
        self.quality_radio_frame = ctk.CTkFrame(self.quality_frame, fg_color="transparent")
        self.quality_radio_frame.grid(row=0, column=1, padx=6, pady=8, sticky="w")
        self.manage_presets_btn = ctk.CTkButton(
            self.quality_frame,
            text="Manage Presets...",
            width=140,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=self._open_preset_editor,
        )
        self.manage_presets_btn.grid(row=0, column=2, padx=12, pady=10, sticky="ne")

        self.preset_description = ctk.CTkLabel(
            self.quality_frame, text="", font=ctk.CTkFont(size=11), text_color=_MUTED, anchor="w"
        )
        self.preset_description.grid(
            row=1, column=0, columnspan=3, padx=12, pady=(0, 2), sticky="w"
        )
        self.output_hint = ctk.CTkLabel(
            self.quality_frame, text="", font=ctk.CTkFont(size=11), text_color=_MUTED, anchor="w"
        )
        self.output_hint.grid(row=2, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")
        self._setup_quality_presets()

        # Progress tracker (takes the file list's place while a batch runs)
        self.progress_tracker = EnhancedProgressTracker(self)
        self.progress_tracker.grid(row=5, column=0, padx=20, pady=(0, 6), sticky="nsew")
        self.progress_tracker.grid_remove()

        # Primary action
        self.compress_button = ctk.CTkButton(
            self,
            text="COMPRESS NOW",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            command=self._on_primary_action,
        )
        self.compress_button.grid(row=6, column=0, padx=20, pady=(8, 14), sticky="ew")

        # Status bar
        status = ctk.CTkFrame(self, corner_radius=0)
        status.grid(row=7, column=0, sticky="ew")
        status.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(status, text="Ready", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, padx=12, pady=6, sticky="w")

        def _status_button(column: int, text: str, command) -> ctk.CTkButton:
            button = ctk.CTkButton(
                status,
                text=text,
                width=88,
                height=28,
                fg_color="transparent",
                border_width=1,
                text_color=("#1A1208", "#F0E8DC"),
                command=command,
            )
            button.grid(row=0, column=column, padx=4, pady=6)
            return button

        self.history_button = _status_button(1, "History", self.show_history)
        self.settings_button = _status_button(2, "Settings", self.open_settings)
        self.update_button = _status_button(3, "Updates", self.check_for_updates)
        self.about_button = _status_button(4, "About", self.show_about)

    def _setup_quality_presets(self) -> None:
        """(Re)build preset radio buttons from the PresetManager."""
        for widget in self.quality_radio_frame.winfo_children():
            widget.destroy()
        self._preset_radios: List[ctk.CTkRadioButton] = []

        for index, preset in enumerate(self.engine.preset_manager.list_presets()):
            radio = ctk.CTkRadioButton(
                self.quality_radio_frame,
                text=preset.display_name,
                variable=self.quality_var,
                value=preset.name,
            )
            radio.grid(
                row=index // _PRESETS_PER_ROW,
                column=index % _PRESETS_PER_ROW,
                padx=(4, 14),
                pady=3,
                sticky="w",
            )
            self._preset_radios.append(radio)

        if self.quality_var.get() not in self.engine.preset_manager.get_preset_names():
            self.quality_var.set(self.engine.preset_manager.get_default_preset().name)
        self._refresh_preset_description()

    def _refresh_preset_description(self) -> None:
        try:
            preset = self.engine.preset_manager.get_preset(self.quality_var.get())
        except KeyError:
            self.preset_description.configure(text="")
            return
        self.preset_description.configure(
            text=f"{preset.description}  •  typical reduction {preset.target_reduction}"
        )

    def _refresh_output_hint(self) -> None:
        settings = self.config_manager.settings
        if settings.output_dir is None:
            where = "same folder as each original"
        else:
            where = str(settings.output_dir)
        self.output_hint.configure(
            text=f"Output: {where}  •  named {settings.output_naming_pattern}"
        )

    # ------------------------------------------------------------------ #
    # Drag and drop                                                        #
    # ------------------------------------------------------------------ #

    def _setup_drag_drop(self) -> None:
        if not DRAG_DROP_AVAILABLE:
            logger.info("Drag-and-drop not available - install tkinterdnd2")
            return
        try:
            # Accept drops anywhere in the window, with highlighting on the drop zone.
            for target in (self, self.drop_frame, self.drop_label):
                target.drop_target_register(DND_FILES)
                target.dnd_bind("<<Drop>>", self._on_drop)
                target.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                target.dnd_bind("<<DragLeave>>", self._on_drag_leave)
            logger.info("Drag-and-drop enabled")
        except Exception as exc:
            logger.error(f"Failed to enable drag-and-drop: {exc}")

    def _on_drop(self, event):
        self._on_drag_leave(None)
        if self._compressing:
            return event.action
        try:
            dropped = [Path(p) for p in self.tk.splitlist(event.data)]
        except Exception as exc:
            logger.error(f"Could not parse dropped data: {exc}")
            return event.action
        self._add_paths(dropped, source="drag-and-drop")
        return event.action

    def _on_drag_enter(self, event):
        if not self._compressing:
            self.drop_label.configure(text=_DROP_ACTIVE_TEXT)
            self.drop_frame.configure(border_color=("#C86B00", "#E07B10"))
        return event.action

    def _on_drag_leave(self, event):
        self.drop_label.configure(text=_DROP_BUSY_TEXT if self._compressing else _DROP_IDLE_TEXT)
        self.drop_frame.configure(border_color=("#C2B8AC", "#5A4A3A"))
        if event is not None:
            return event.action

    # ------------------------------------------------------------------ #
    # File list                                                            #
    # ------------------------------------------------------------------ #

    def add_files(self) -> None:
        if self._compressing:
            return
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            parent=self,
        )
        if files:
            self._add_paths([Path(f) for f in files], source="file dialog")

    def add_folder(self) -> None:
        if self._compressing:
            return
        folder = filedialog.askdirectory(title="Select a folder containing PDFs", parent=self)
        if not folder:
            return
        folder_path = Path(folder)
        pdfs = sorted(p for p in folder_path.glob("*.pdf") if p.is_file())
        if not pdfs:
            show_info(self, "No PDFs Found", f"There are no PDF files in:\n{folder_path}")
            return
        self._add_paths(pdfs, source="folder")

    def _add_paths(self, paths: List[Path], source: str) -> None:
        """Validate and add paths to the list, reporting anything skipped."""
        added: List[Path] = []
        rejected: List[str] = []
        for path in paths:
            if path.is_dir():
                added.extend(p for p in sorted(path.glob("*.pdf")) if p.is_file())
                continue
            if not path.is_file():
                rejected.append(f"{path.name} (not found)")
            elif path.suffix.lower() != ".pdf":
                rejected.append(f"{path.name} (not a PDF)")
            else:
                added.append(path)

        new_files = [p for p in added if p not in self.selected_files]
        if new_files:
            self.selected_files.extend(new_files)
            self._update_file_list()
            logger.info(f"Added {len(new_files)} file(s) via {source}")

        if rejected:
            shown = "\n".join(rejected[:6])
            if len(rejected) > 6:
                shown += f"\n... and {len(rejected) - 6} more"
            show_warning(
                self, "Some Files Were Skipped", f"Only PDF files can be compressed:\n\n{shown}"
            )

    def remove_file(self, file_path: Path) -> None:
        if self._compressing:
            return
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            self._update_file_list()

    def clear_files(self) -> None:
        if self._compressing or not self.selected_files:
            return
        self.selected_files.clear()
        self._update_file_list()

    def _update_file_list(self) -> None:
        for widget in self.files_list.winfo_children():
            widget.destroy()
        self._remove_buttons.clear()

        total = 0
        for row, file_path in enumerate(self.selected_files):
            try:
                size = file_path.stat().st_size
            except OSError:
                size = 0
            total += size

            item = ctk.CTkFrame(self.files_list, fg_color="transparent")
            item.grid(row=row, column=0, padx=4, pady=1, sticky="ew")
            item.grid_columnconfigure(0, weight=1)

            name = file_path.name if len(file_path.name) <= 70 else file_path.name[:67] + "..."
            ctk.CTkLabel(item, text=name, font=ctk.CTkFont(size=12), anchor="w").grid(
                row=0, column=0, padx=6, sticky="ew"
            )
            ctk.CTkLabel(
                item,
                text=FileSystemHelper.format_size(size),
                font=ctk.CTkFont(size=11),
                width=70,
                anchor="e",
            ).grid(row=0, column=1, padx=6)
            remove = ctk.CTkButton(
                item,
                text="✕",
                width=30,
                height=24,
                fg_color="transparent",
                border_width=1,
                text_color=("#1A1208", "#F0E8DC"),
                command=lambda f=file_path: self.remove_file(f),
            )
            remove.grid(row=0, column=2, padx=(4, 2))
            self._remove_buttons.append(remove)

        count = len(self.selected_files)
        if count == 0:
            self.files_label.configure(text="No files selected")
        else:
            self.files_label.configure(
                text=f"{count} file{'s' if count != 1 else ''} selected  •  {FileSystemHelper.format_size(total)}"
            )

    # ------------------------------------------------------------------ #
    # Compression                                                          #
    # ------------------------------------------------------------------ #

    def _on_primary_action(self) -> None:
        if self._compressing:
            self.cancel_compression()
        else:
            self.start_compression()

    def start_compression(self) -> None:
        if self._compressing:
            return
        if not self.selected_files:
            show_warning(self, "No Files Selected", "Add one or more PDF files first.")
            return

        settings = self.config_manager.settings
        preset = self.quality_var.get()
        if preset not in self.engine.preset_manager.get_preset_names():
            preset = self.engine.preset_manager.get_default_preset().name
            self.quality_var.set(preset)

        output_dir = settings.output_dir
        if (
            output_dir is not None
            and output_dir.exists()
            and not FileSystemHelper.is_writable_directory(output_dir)
        ):
            show_error(
                self,
                "Output Folder Not Writable",
                f"Squash cannot write to the output folder:\n{output_dir}\n\n"
                "Choose a different folder in Settings.",
            )
            return

        files = list(self.selected_files)
        self._cancel_event = threading.Event()
        self._set_busy(True)
        self.files_frame.grid_remove()
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(5, weight=1)
        self.progress_tracker.grid()
        self.progress_tracker.start_batch(files)
        self._ensure_content_visible()
        self.status_label.configure(
            text=f"Compressing {len(files)} file(s) with '{preset}' preset..."
        )

        self._worker = threading.Thread(
            target=self._compress_worker,
            args=(
                files,
                preset,
                output_dir,
                settings.output_naming_pattern,
                settings.compression_timeout,
                settings.keep_larger_output,
            ),
            name="squash-batch",
            daemon=True,
        )
        self._worker.start()

    def cancel_compression(self) -> None:
        if not self._compressing or self._cancel_event is None:
            return
        self._cancel_event.set()
        self.compress_button.configure(state="disabled", text="CANCELLING...")
        self.progress_tracker.set_cancelling()
        self.status_label.configure(text="Cancelling after the current page...")
        logger.info("User requested cancellation")

    def _compress_worker(
        self,
        files: List[Path],
        preset: str,
        output_dir: Optional[Path],
        pattern: str,
        timeout: int,
        keep_larger: bool,
    ) -> None:
        """Background thread: run the batch and hand results back to the UI thread."""
        try:
            result = self.batch_processor.process_batch(
                files,
                preset=preset,
                output_dir=output_dir,
                naming_pattern=pattern,
                timeout=timeout,
                progress_callback=self._on_batch_progress,
                cancel_event=self._cancel_event,
                result_callback=self._on_file_result,
                keep_larger=keep_larger,
            )
        except Exception as exc:
            logger.exception("Batch compression failed")
            self._post(self._on_compression_failed, str(exc))
            return
        self._post(self._on_compression_complete, result)

    def _on_batch_progress(self, progress: BatchProgress) -> None:
        """Called from the worker thread; throttled and handed to the UI thread."""
        now = time.monotonic()
        final = progress.detail in ("done", "starting") or progress.file_progress >= 1.0
        if not final and now - self._last_progress_emit < _PROGRESS_THROTTLE_S:
            return
        self._last_progress_emit = now
        self._post(self.progress_tracker.update, progress)

    def _on_file_result(self, result: CompressionResult) -> None:
        self._post(self.progress_tracker.mark_result, result)

    def _on_compression_failed(self, message: str) -> None:
        self._finish_batch_ui()
        show_error(self, "Compression Error", f"The batch could not be run:\n\n{message}")

    def _on_compression_complete(self, result: BatchResult) -> None:
        self._finish_batch_ui()

        if self.history_manager and self.config_manager.settings.store_history:
            recordable = [r for r in result.file_results if not r.cancelled]
            if recordable:
                try:
                    self.history_manager.add_entries(recordable)
                except Exception as exc:
                    logger.error(f"Failed to record history: {exc}")

        # Keep failed and unprocessed files in the list so the user can retry them.
        done = {Path(r.input_path) for r in result.file_results if r.success}
        self.selected_files = [p for p in self.selected_files if p not in done]
        self._update_file_list()

        try:
            from .results_dialog import ResultsDialog

            dialog = ResultsDialog(self, result)
            self.wait_window(dialog)
        except Exception as exc:
            logger.exception("Failed to show results dialog")
            show_info(self, "Compression Finished", f"{result.get_summary()}\n\n({exc})")

    def _finish_batch_ui(self) -> None:
        self._set_busy(False)
        self.progress_tracker.grid_remove()
        self.progress_tracker.reset()
        self.grid_rowconfigure(5, weight=0)
        self.grid_rowconfigure(3, weight=1)
        self.files_frame.grid()
        self.status_label.configure(text="Ready")
        self._cancel_event = None
        self._worker = None

    def _set_busy(self, busy: bool) -> None:
        """Enable/disable controls that must not change during a batch."""
        self._compressing = busy
        state = "disabled" if busy else "normal"
        for widget in (
            self.add_files_btn,
            self.add_folder_btn,
            self.clear_btn,
            self.manage_presets_btn,
            self.settings_button,
            *self._remove_buttons,
            *self._preset_radios,
        ):
            widget.configure(state=state)
        self.drop_label.configure(text=_DROP_BUSY_TEXT if busy else _DROP_IDLE_TEXT)
        self.drop_frame.configure(cursor="arrow" if busy else "hand2")

        if busy:
            self.compress_button.configure(
                text="CANCEL",
                state="normal",
                fg_color=("gray55", "gray35"),
                hover_color=("gray45", "gray25"),
            )
        else:
            self.compress_button.configure(
                text="COMPRESS NOW",
                state="normal",
                fg_color=("#C86B00", "#E07B10"),
                hover_color=("#A85800", "#C86B00"),
            )

    # ------------------------------------------------------------------ #
    # Dialogs                                                              #
    # ------------------------------------------------------------------ #

    def open_settings(self) -> None:
        if self._compressing:
            return
        from .settings_dialog import SettingsDialog

        before = self.config_manager.settings
        old_gs_path = before.ghostscript_path
        dialog = SettingsDialog(self, self.config_manager)
        self.wait_window(dialog)

        settings = self.config_manager.settings
        apply_appearance(settings.normalized_theme)
        self._refresh_output_hint()

        if dialog.saved and settings.ghostscript_path != old_gs_path:
            try:
                gs_path = Path(settings.ghostscript_path) if settings.ghostscript_path else None
                self.engine = CompressionEngine(gs_path, preset_manager=self.engine.preset_manager)
                self.batch_processor.engine = self.engine
                logger.info("Compression engine rebuilt with new Ghostscript path")
            except RuntimeError as exc:
                show_error(self, "Ghostscript Not Found", str(exc))

    def show_history(self) -> None:
        if not self.history_manager:
            show_error(
                self,
                "History Unavailable",
                "The history database could not be opened. See the log for details.",
            )
            return
        try:
            from .history_dialog import HistoryDialog

            dialog = HistoryDialog(self, self.history_manager)
            self.wait_window(dialog)
        except Exception as exc:
            logger.exception("Failed to open history dialog")
            show_error(self, "History Error", f"Failed to open history:\n\n{exc}")

    def _open_preset_editor(self) -> None:
        if self._compressing:
            return
        try:
            from .preset_editor import PresetEditorDialog

            dialog = PresetEditorDialog(self, self.engine.preset_manager)
            self.wait_window(dialog)
        except Exception as exc:
            logger.exception("Error opening preset editor")
            show_error(self, "Preset Editor Error", f"Failed to open the preset editor:\n\n{exc}")
        finally:
            self._setup_quality_presets()

    def show_about(self) -> None:
        gs_version = self.engine.gs.get_version() or "unknown"
        show_info(
            self,
            "About Squash",
            f"{APP_NAME} v{__version__}\n\n"
            "Compress PDF files locally. Nothing is uploaded; your documents never leave "
            "this computer.\n\n"
            f"Ghostscript {gs_version}\n"
            f"License: AGPL-3.0\n"
            f"github.com/{GITHUB_REPO}",
        )

    # ------------------------------------------------------------------ #
    # Update checking                                                      #
    # ------------------------------------------------------------------ #

    def _start_update_check(self) -> None:
        UpdateChecker().check_async(callback=self._on_update_check_result)

    def _on_update_check_result(self, release, network_error: bool) -> None:
        self._post(self._show_update_dialog_if_needed, release)

    def _show_update_dialog_if_needed(self, release) -> None:
        if release is None:
            return
        if release.version == self.config_manager.settings.skip_version:
            logger.debug(f"Update {release.version} suppressed by skip_version setting")
            return
        self.update_button.configure(
            text="Update!", fg_color=("#C86B00", "#E07B10"), text_color=("#FFFFFF", "#FFFFFF")
        )
        from .update_dialog import UpdateDialog

        UpdateDialog(self, release, self.config_manager, quit_callback=self.destroy)

    def check_for_updates(self) -> None:
        self.update_button.configure(state="disabled")
        self.status_label.configure(text="Checking for updates...")
        UpdateChecker().check_async(callback=self._on_manual_update_result)

    def _on_manual_update_result(self, release, network_error: bool) -> None:
        self._post(self._handle_manual_update_result, release, network_error)

    def _handle_manual_update_result(self, release, network_error: bool) -> None:
        self.update_button.configure(state="normal")
        self.status_label.configure(text="Ready")
        if network_error:
            show_error(
                self,
                "Update Check Failed",
                "Could not reach GitHub to check for updates.\n"
                "Please check your internet connection and try again.",
            )
            return
        if release is None:
            show_info(self, "Up to Date", f"You already have the latest version (v{__version__}).")
            return
        from .update_dialog import UpdateDialog

        UpdateDialog(self, release, self.config_manager, quit_callback=self.destroy)

    # ------------------------------------------------------------------ #
    # Shutdown                                                             #
    # ------------------------------------------------------------------ #

    def _on_close(self) -> None:
        if self._compressing:
            if not ask_yes_no(
                self,
                "Compression in Progress",
                "Files are still being compressed.\n\nStop and quit Squash?",
                yes_text="Stop and Quit",
                no_text="Keep Working",
                danger=True,
            ):
                return
            if self._cancel_event is not None:
                self._cancel_event.set()
            worker = self._worker
            if worker is not None:
                worker.join(timeout=5)  # lets the Ghostscript process be killed cleanly

        self._save_window_state()
        self.destroy()

    def _save_window_state(self) -> None:
        settings = self.config_manager.settings
        try:
            maximized = self.state() == "zoomed"
            settings.window_maximized = maximized
            if not maximized:
                settings.window_width = max(self.winfo_width(), 600)
                settings.window_height = max(self.winfo_height(), 500)
            settings.default_preset = self.quality_var.get()
            self.config_manager.save_settings(settings)
        except Exception as exc:
            logger.debug(f"Could not save window state: {exc}")
