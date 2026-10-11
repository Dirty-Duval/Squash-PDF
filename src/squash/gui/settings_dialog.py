"""
Settings dialog for Squash PDF Compressor.

Modal dialog for theme, output location and naming, compression timeout,
Ghostscript path, logging and privacy preferences. Every option shown here
is actually honoured by the application.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog
from typing import List, Optional, Tuple

import customtkinter as ctk

from ..config.manager import SAME_FOLDER, VALID_LOG_LEVELS, ConfigManager, Settings
from ..core.batch import resolve_output_path
from ..core.ghostscript import GhostscriptWrapper, detect_ghostscript
from ..utils.filesystem import FileSystemHelper
from ..utils.logger import set_log_level
from ._icon import apply_icon
from .appearance import apply_appearance
from .dialogs import ask_yes_no, fit_to_content, show_error

logger = logging.getLogger(__name__)

_MIN_TIMEOUT = 30
_MAX_TIMEOUT = 3600
_HINT = ("gray45", "gray60")
_OK = ("#43A047", "#50C878")
_WARN = ("#E08A00", "#FFA500")


class SettingsDialog(ctk.CTkToplevel):
    """Settings configuration dialog with validation and live theme preview."""

    def __init__(self, parent, config_manager: ConfigManager):
        """
        Args:
            parent: Parent window (MainWindow instance).
            config_manager: ConfigManager used to read and persist settings.
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.parent_window = parent
        self.original_settings = Settings(**config_manager.settings.to_dict())
        self.saved = False

        self.title("Settings")
        self.resizable(False, False)
        self.transient(parent)

        self._setup_ui()
        self._load_settings(config_manager.settings)

        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        apply_icon(self)
        fit_to_content(self, min_width=640, parent=parent)
        self.grab_set()
        self.focus()
        logger.info("Settings dialog opened")

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Plain frame (not scrollable) so the dialog can size itself to show everything.
        self.scroll = ctk.CTkFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, padx=16, pady=(16, 0), sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self._create_appearance_section(0)
        self._create_output_section(1)
        self._create_compression_section(2)
        self._create_ghostscript_section(3)
        self._create_logging_section(4)
        self._create_button_bar()

    def _section(self, row: int, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.scroll)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(8, 4)
        )
        return frame

    @staticmethod
    def _hint(frame, row: int, text: str, columnspan: int = 3) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            frame,
            text=text,
            font=ctk.CTkFont(size=11),
            text_color=_HINT,
            justify="left",
            anchor="w",
            wraplength=540,
        )
        label.grid(row=row, column=0, columnspan=columnspan, sticky="w", padx=12, pady=(0, 8))
        return label

    def _create_appearance_section(self, row: int) -> None:
        frame = self._section(row, "Appearance")
        self.theme_var = ctk.StringVar(value="system")

        ctk.CTkLabel(frame, text="Theme:").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        radios = ctk.CTkFrame(frame, fg_color="transparent")
        radios.grid(row=1, column=1, columnspan=2, sticky="w", padx=12, pady=4)
        for value, text in (("system", "System"), ("light", "Light"), ("dark", "Dark")):
            ctk.CTkRadioButton(
                radios,
                text=text,
                variable=self.theme_var,
                value=value,
                command=self._on_theme_change,
            ).pack(side="left", padx=(0, 14))
        self._hint(frame, 2, "Changes preview immediately and are kept when you click Save.")

    def _create_output_section(self, row: int) -> None:
        frame = self._section(row, "Output")

        ctk.CTkLabel(frame, text="Save to:").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        self.output_folder_entry = ctk.CTkEntry(
            frame, placeholder_text="Same folder as the original (default)"
        )
        self.output_folder_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        folder_buttons = ctk.CTkFrame(frame, fg_color="transparent")
        folder_buttons.grid(row=1, column=2, sticky="e", padx=(0, 12), pady=4)
        ctk.CTkButton(
            folder_buttons, text="Browse", width=76, command=self._browse_output_folder
        ).pack(side="left")
        ctk.CTkButton(
            folder_buttons,
            text="Same folder",
            width=96,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=lambda: self.output_folder_entry.delete(0, "end"),
        ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(frame, text="File name:").grid(row=2, column=0, sticky="w", padx=12, pady=4)
        self.pattern_entry = ctk.CTkEntry(frame, placeholder_text="{filename}_compressed.pdf")
        self.pattern_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(6, 12), pady=4)
        self.pattern_entry.bind("<KeyRelease>", lambda _e: self._refresh_pattern_preview())

        self.pattern_preview = self._hint(
            frame,
            3,
            "Use {filename} for the original name. Existing files are never overwritten.",
        )

    def _create_compression_section(self, row: int) -> None:
        frame = self._section(row, "Compression")
        ctk.CTkLabel(frame, text="Time limit per file:").grid(
            row=1, column=0, sticky="w", padx=12, pady=4
        )
        timeout_row = ctk.CTkFrame(frame, fg_color="transparent")
        timeout_row.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=4)
        self.timeout_entry = ctk.CTkEntry(timeout_row, width=90, justify="right")
        self.timeout_entry.pack(side="left")
        ctk.CTkLabel(timeout_row, text="seconds").pack(side="left", padx=(8, 0))
        self._hint(
            frame,
            2,
            f"Files that take longer are stopped and reported as failed "
            f"({_MIN_TIMEOUT}-{_MAX_TIMEOUT} seconds). Very large scanned PDFs may need more "
            "than the default of 300.",
        )
        self.keep_larger_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame,
            text="Keep the compressed file even when it is larger than the original",
            variable=self.keep_larger_var,
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 4))
        self._hint(
            frame,
            4,
            "Off (recommended): PDFs that are already well optimised keep their original "
            "and are reported as such instead of producing a bigger file.",
        )

    def _create_ghostscript_section(self, row: int) -> None:
        frame = self._section(row, "Ghostscript")

        ctk.CTkLabel(frame, text="Executable:").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        self.gs_path_entry = ctk.CTkEntry(frame, placeholder_text="Bundled copy (auto-detect)")
        self.gs_path_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        gs_buttons = ctk.CTkFrame(frame, fg_color="transparent")
        gs_buttons.grid(row=1, column=2, sticky="e", padx=(0, 12), pady=4)
        ctk.CTkButton(gs_buttons, text="Browse", width=76, command=self._browse_ghostscript).pack(
            side="left"
        )
        ctk.CTkButton(
            gs_buttons,
            text="Auto-detect",
            width=96,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=self._auto_detect_ghostscript,
        ).pack(side="left", padx=(6, 0))

        self.gs_status_label = self._hint(
            frame, 2, "Leave empty to use the Ghostscript copy that ships with Squash."
        )

    def _create_logging_section(self, row: int) -> None:
        frame = self._section(row, "Logging & Privacy")
        ctk.CTkLabel(frame, text="Log level:").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        self.log_level_var = ctk.StringVar(value="INFO")
        ctk.CTkOptionMenu(
            frame, variable=self.log_level_var, values=list(VALID_LOG_LEVELS), width=140
        ).grid(row=1, column=1, sticky="w", padx=6, pady=4)
        ctk.CTkButton(
            frame,
            text="Open Log Folder",
            width=140,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=self._open_log_folder,
        ).grid(row=1, column=2, sticky="e", padx=(0, 12), pady=4)
        self._hint(
            frame, 2, "DEBUG records every Ghostscript command; use it when reporting a problem."
        )

        self.check_updates_var = ctk.BooleanVar(value=True)
        self.store_history_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame,
            text="Check for updates on startup (contacts GitHub)",
            variable=self.check_updates_var,
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 6))
        ctk.CTkCheckBox(
            frame,
            text="Keep a local history of compressed files",
            variable=self.store_history_var,
        ).grid(row=4, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))

    def _create_button_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=16, pady=14)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            bar,
            text="Reset to Defaults",
            width=140,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=self._reset_to_defaults,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            bar,
            text="Cancel",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=self._on_cancel,
        ).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(bar, text="Save", width=110, command=self._on_ok).grid(row=0, column=3)

    # ------------------------------------------------------------------ #
    # Loading                                                              #
    # ------------------------------------------------------------------ #

    def _set_entry(self, entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)

    def _load_settings(self, settings: Settings) -> None:
        self.theme_var.set(settings.normalized_theme)
        self._set_entry(
            self.output_folder_entry,
            "" if settings.output_dir is None else str(settings.output_dir),
        )
        self._set_entry(self.pattern_entry, settings.output_naming_pattern)
        self._set_entry(self.timeout_entry, str(settings.compression_timeout))
        self.keep_larger_var.set(settings.keep_larger_output)
        self._set_entry(self.gs_path_entry, settings.ghostscript_path or "")
        if settings.ghostscript_path:
            self._validate_ghostscript_path(Path(settings.ghostscript_path))
        self.log_level_var.set(settings.normalized_log_level)
        self.check_updates_var.set(settings.check_updates)
        self.store_history_var.set(settings.store_history)
        self._refresh_pattern_preview()

    def _reset_to_defaults(self) -> None:
        defaults = Settings()
        self._load_settings(defaults)
        apply_appearance(defaults.theme)
        self.gs_status_label.configure(
            text="Leave empty to use the Ghostscript copy that ships with Squash.", text_color=_HINT
        )

    # ------------------------------------------------------------------ #
    # Field handlers                                                       #
    # ------------------------------------------------------------------ #

    def _on_theme_change(self) -> None:
        apply_appearance(self.theme_var.get())

    def _refresh_pattern_preview(self) -> None:
        pattern = self.pattern_entry.get().strip()
        if not pattern:
            pattern = Settings().output_naming_pattern
        if "{filename}" not in pattern:
            self.pattern_preview.configure(
                text="The pattern must contain {filename}.", text_color=_WARN
            )
            return
        example = resolve_output_path(Path("Report.pdf"), Path("."), pattern).name
        self.pattern_preview.configure(
            text=f"Example: Report.pdf  →  {example}    (existing files are never overwritten)",
            text_color=_HINT,
        )

    def _browse_output_folder(self) -> None:
        current = self.output_folder_entry.get().strip()
        initial = current if current and Path(current).is_dir() else str(Path.home())
        folder = filedialog.askdirectory(
            title="Select Output Folder", initialdir=initial, parent=self
        )
        if folder:
            self._set_entry(self.output_folder_entry, str(Path(folder)))

    def _browse_ghostscript(self) -> None:
        file = filedialog.askopenfilename(
            title="Select Ghostscript Executable",
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")],
            parent=self,
        )
        if file:
            self._set_entry(self.gs_path_entry, file)
            self._validate_ghostscript_path(Path(file))

    def _auto_detect_ghostscript(self) -> None:
        found = detect_ghostscript()
        if found is None:
            self.gs_status_label.configure(
                text="⚠ No Ghostscript installation found.", text_color=_WARN
            )
            return
        self._set_entry(self.gs_path_entry, str(found))
        self._validate_ghostscript_path(found)

    def _open_log_folder(self) -> None:
        log_dir = FileSystemHelper.get_app_data_dir() / "logs"
        FileSystemHelper.ensure_directory(log_dir)
        FileSystemHelper.open_in_file_manager(log_dir)

    def _validate_ghostscript_path(self, path: Path) -> Tuple[bool, str]:
        """Check that ``path`` is a runnable Ghostscript and update the status line."""
        if not path.is_file():
            self.gs_status_label.configure(text="⚠ File not found.", text_color=_WARN)
            return False, "File not found"
        try:
            version = GhostscriptWrapper(path).get_version()
        except Exception as exc:
            version = None
            logger.debug(f"Ghostscript validation failed: {exc}")
        if version:
            self.gs_status_label.configure(text=f"✓ Ghostscript {version}", text_color=_OK)
            return True, version
        self.gs_status_label.configure(
            text="⚠ This file did not respond like Ghostscript.", text_color=_WARN
        )
        return False, "Not a working Ghostscript executable"

    # ------------------------------------------------------------------ #
    # Save / cancel                                                        #
    # ------------------------------------------------------------------ #

    def _validate(self) -> Tuple[bool, List[str], Optional[Path]]:
        """Validate all fields.

        Returns:
            (ok, errors, output_dir) where output_dir is None for "same folder".
        """
        errors: List[str] = []

        output_dir: Optional[Path] = None
        folder_text = self.output_folder_entry.get().strip()
        if folder_text and folder_text != SAME_FOLDER:
            output_dir = Path(folder_text)
            if not output_dir.exists():
                if ask_yes_no(
                    self,
                    "Create Folder?",
                    f"The output folder does not exist:\n{output_dir}\n\nCreate it now?",
                    yes_text="Create",
                    no_text="Cancel",
                ):
                    try:
                        output_dir.mkdir(parents=True, exist_ok=True)
                    except OSError as exc:
                        errors.append(f"Could not create output folder: {exc}")
                else:
                    errors.append("Choose an existing output folder or leave it empty.")
            elif not FileSystemHelper.is_writable_directory(output_dir):
                errors.append(f"The output folder is not writable: {output_dir}")

        pattern = self.pattern_entry.get().strip()
        if pattern and "{filename}" not in pattern:
            errors.append("The file name pattern must contain {filename}.")

        try:
            timeout = int(self.timeout_entry.get().strip())
            if not (_MIN_TIMEOUT <= timeout <= _MAX_TIMEOUT):
                raise ValueError
        except ValueError:
            errors.append(
                f"Time limit must be a whole number between {_MIN_TIMEOUT} and {_MAX_TIMEOUT}."
            )

        gs_text = self.gs_path_entry.get().strip()
        if gs_text:
            ok, detail = self._validate_ghostscript_path(Path(gs_text))
            if not ok:
                errors.append(f"Ghostscript: {detail}")

        return not errors, errors, output_dir

    def _on_ok(self) -> None:
        ok, errors, output_dir = self._validate()
        if not ok:
            show_error(self, "Check Your Settings", "\n".join(f"• {e}" for e in errors))
            return

        settings = self.config_manager.settings
        settings.theme = self.theme_var.get()
        settings.output_location = str(output_dir) if output_dir else SAME_FOLDER
        settings.output_naming_pattern = (
            self.pattern_entry.get().strip() or Settings().output_naming_pattern
        )
        settings.compression_timeout = int(self.timeout_entry.get().strip())
        settings.keep_larger_output = self.keep_larger_var.get()
        settings.ghostscript_path = self.gs_path_entry.get().strip() or None
        settings.log_level = self.log_level_var.get()
        settings.check_updates = self.check_updates_var.get()
        settings.store_history = self.store_history_var.get()

        if not self.config_manager.save_settings(settings):
            show_error(
                self,
                "Save Failed",
                "Settings could not be written to disk.\nCheck that the AppData folder is writable.",
            )
            return

        set_log_level(settings.normalized_log_level)
        self.saved = True
        logger.info("Settings saved")
        self.destroy()

    def _on_cancel(self) -> None:
        apply_appearance(self.original_settings.normalized_theme)
        logger.info("Settings dialog cancelled")
        self.destroy()
