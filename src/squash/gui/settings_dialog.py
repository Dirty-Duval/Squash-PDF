"""
Settings dialog for Squash PDF Compressor.

Provides a modal dialog interface for configuring application settings including
theme, output location, Ghostscript path, and logging level.
"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, Tuple, List
import subprocess
import logging

from ..config.manager import ConfigManager, Settings
from ._icon import apply_icon

logger = logging.getLogger(__name__)


class SettingsDialog(ctk.CTkToplevel):
    """
    Settings configuration dialog.

    Provides UI for modifying application settings with validation and
    immediate theme preview.
    """

    def __init__(self, parent, config_manager: ConfigManager):
        """
        Initialize settings dialog.

        Args:
            parent: Parent window (MainWindow instance)
            config_manager: ConfigManager instance for settings persistence
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.parent_window = parent

        # Store original settings for Cancel operation
        self.original_settings = Settings(**self.config_manager.settings.to_dict())

        # Configure dialog window
        self.title("Settings")
        self.geometry("600x550")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center dialog on parent
        self._center_on_parent()

        # Build UI
        self._setup_ui()

        # Load current settings
        self._load_settings()

        # Bind keyboard shortcuts
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Return>", lambda e: self._on_ok())

        apply_icon(self)
        logger.info("Settings dialog opened")

    def _center_on_parent(self) -> None:
        """Center dialog on parent window."""
        self.update_idletasks()

        parent_x = self.parent_window.winfo_x()
        parent_y = self.parent_window.winfo_y()
        parent_width = self.parent_window.winfo_width()
        parent_height = self.parent_window.winfo_height()

        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"+{x}+{y}")

    def _setup_ui(self) -> None:
        """Build the complete UI layout."""
        # Main container with padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Configure grid
        main_frame.grid_columnconfigure(0, weight=1)

        # === SECTION 1: Appearance ===
        self._create_appearance_section(main_frame, row=0)

        # === SECTION 2: Output Location ===
        self._create_output_section(main_frame, row=1)

        # === SECTION 3: Ghostscript ===
        self._create_ghostscript_section(main_frame, row=2)

        # === SECTION 4: Logging ===
        self._create_logging_section(main_frame, row=3)

        # === SECTION 5: Privacy ===
        self._create_privacy_section(main_frame, row=4)

        # === DIALOG BUTTONS ===
        self._create_button_section(main_frame, row=5)

    def _create_appearance_section(self, parent, row: int) -> None:
        """Create appearance/theme section."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        # Label
        label = ctk.CTkLabel(
            frame,
            text="Appearance",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))

        # Theme selection
        self.theme_var = ctk.StringVar(value="system")

        theme_label = ctk.CTkLabel(frame, text="Theme:")
        theme_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        radio_frame = ctk.CTkFrame(frame, fg_color="transparent")
        radio_frame.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        self.system_radio = ctk.CTkRadioButton(
            radio_frame,
            text="System",
            variable=self.theme_var,
            value="system",
            command=self._on_theme_change
        )
        self.system_radio.pack(side="left", padx=(0, 10))

        self.light_radio = ctk.CTkRadioButton(
            radio_frame,
            text="Light",
            variable=self.theme_var,
            value="light",
            command=self._on_theme_change
        )
        self.light_radio.pack(side="left", padx=(0, 10))

        self.dark_radio = ctk.CTkRadioButton(
            radio_frame,
            text="Dark",
            variable=self.theme_var,
            value="dark",
            command=self._on_theme_change
        )
        self.dark_radio.pack(side="left")

        # Description
        desc = ctk.CTkLabel(
            frame,
            text="Choose application color theme",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        desc.grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

    def _create_output_section(self, parent, row: int) -> None:
        """Create output location section."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        # Label
        label = ctk.CTkLabel(
            frame,
            text="Default Output Location",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))

        # Path entry
        path_label = ctk.CTkLabel(frame, text="Folder:")
        path_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.output_folder_entry = ctk.CTkEntry(frame, placeholder_text="same_folder")
        self.output_folder_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        browse_btn = ctk.CTkButton(
            frame,
            text="Browse",
            width=80,
            command=self._browse_output_folder
        )
        browse_btn.grid(row=1, column=2, sticky="e", padx=10, pady=5)

        # Description
        desc = ctk.CTkLabel(
            frame,
            text='Leave empty for "same_folder" or specify a custom directory',
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        desc.grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

    def _create_ghostscript_section(self, parent, row: int) -> None:
        """Create Ghostscript configuration section."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        # Label
        label = ctk.CTkLabel(
            frame,
            text="Ghostscript",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))

        # Path entry
        path_label = ctk.CTkLabel(frame, text="Executable:")
        path_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.gs_path_entry = ctk.CTkEntry(frame, placeholder_text="Auto-detect")
        self.gs_path_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        browse_btn = ctk.CTkButton(
            frame,
            text="Browse",
            width=80,
            command=self._browse_ghostscript
        )
        browse_btn.grid(row=1, column=2, sticky="e", padx=10, pady=5)

        # Status label
        self.gs_status_label = ctk.CTkLabel(
            frame,
            text="Status: Not validated",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.gs_status_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=5)

        # Auto-detect button
        auto_detect_btn = ctk.CTkButton(
            frame,
            text="Auto-Detect",
            width=120,
            command=self._auto_detect_ghostscript
        )
        auto_detect_btn.grid(row=3, column=0, sticky="w", padx=10, pady=(5, 10))

    def _create_logging_section(self, parent, row: int) -> None:
        """Create logging configuration section."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        # Label
        label = ctk.CTkLabel(
            frame,
            text="Logging",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        # Log level dropdown
        level_label = ctk.CTkLabel(frame, text="Log Level:")
        level_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.log_level_var = ctk.StringVar(value="WARNING")
        self.log_level_dropdown = ctk.CTkOptionMenu(
            frame,
            variable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"]
        )
        self.log_level_dropdown.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Description
        desc = ctk.CTkLabel(
            frame,
            text="Higher levels show fewer messages",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        desc.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

    def _create_privacy_section(self, parent, row: int) -> None:
        """Create privacy / update preferences section."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="Privacy",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        self.check_updates_var = ctk.BooleanVar(
            value=self.config_manager.settings.check_updates
        )
        ctk.CTkCheckBox(
            frame,
            text="Check for updates automatically on startup",
            variable=self.check_updates_var,
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

    def _create_button_section(self, parent, row: int) -> None:
        """Create dialog control buttons."""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.grid(row=row, column=0, sticky="ew", pady=(10, 0))
        button_frame.grid_columnconfigure(0, weight=1)

        # Button container (right-aligned)
        btn_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        btn_container.grid(row=0, column=0, sticky="e")

        # Cancel button
        cancel_btn = ctk.CTkButton(
            btn_container,
            text="Cancel",
            width=100,
            fg_color="gray",
            hover_color="dark gray",
            command=self._on_cancel
        )
        cancel_btn.pack(side="left", padx=5)

        # OK button
        ok_btn = ctk.CTkButton(
            btn_container,
            text="OK",
            width=100,
            command=self._on_ok
        )
        ok_btn.pack(side="left", padx=5)

    def _load_settings(self) -> None:
        """Load current settings from ConfigManager into UI."""
        settings = self.config_manager.settings

        # Load theme
        theme = settings.theme
        self.theme_var.set(theme)

        # Load output location
        if settings.output_location != "same_folder":
            self.output_folder_entry.delete(0, "end")
            self.output_folder_entry.insert(0, settings.output_location)

        # Load Ghostscript path
        if settings.ghostscript_path:
            self.gs_path_entry.delete(0, "end")
            self.gs_path_entry.insert(0, settings.ghostscript_path)
            # Validate loaded path
            self._validate_ghostscript_path(Path(settings.ghostscript_path))

        # Load log level
        self.log_level_var.set(settings.log_level)

        logger.debug("Settings loaded into UI")

    def _on_theme_change(self) -> None:
        """Handle theme change with live preview."""
        theme = self.theme_var.get()
        ctk.set_appearance_mode(theme.capitalize())
        logger.debug(f"Theme changed to: {theme}")

    def _browse_output_folder(self) -> None:
        """Open directory chooser for output folder."""
        current_path = self.output_folder_entry.get().strip()
        initial_dir = current_path if current_path and Path(current_path).exists() else Path.home()

        folder = filedialog.askdirectory(
            title="Select Default Output Folder",
            initialdir=initial_dir
        )

        if folder:
            self.output_folder_entry.delete(0, "end")
            self.output_folder_entry.insert(0, folder)
            logger.debug(f"Selected output folder: {folder}")

    def _browse_ghostscript(self) -> None:
        """Open file chooser for Ghostscript executable."""
        file = filedialog.askopenfilename(
            title="Select Ghostscript Executable",
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")]
        )

        if file:
            self.gs_path_entry.delete(0, "end")
            self.gs_path_entry.insert(0, file)
            self._validate_ghostscript_path(Path(file))
            logger.debug(f"Selected Ghostscript: {file}")

    def _auto_detect_ghostscript(self) -> None:
        """Auto-detect Ghostscript installation using the same logic as the engine."""
        logger.info("Running Ghostscript auto-detection...")

        from ..core.ghostscript import GhostscriptWrapper
        gs_path = GhostscriptWrapper._detect_ghostscript(GhostscriptWrapper.__new__(GhostscriptWrapper))

        if gs_path and gs_path.exists():
            # Trust the engine's detection — it uses the same path at startup successfully.
            # Skipping subprocess --version check which can fail in packaged environments.
            self.gs_path_entry.delete(0, "end")
            self.gs_path_entry.insert(0, str(gs_path))
            self.gs_status_label.configure(
                text=f"✅ Auto-detected: {gs_path.name}",
                text_color="green"
            )
            logger.info(f"Auto-detected Ghostscript: {gs_path}")
            return

        # Not found
        self.gs_status_label.configure(
            text="⚠️ Auto-detect failed - Ghostscript not found",
            text_color="orange"
        )
        self._show_error(
            "Ghostscript Not Found",
            "Could not auto-detect Ghostscript installation.\n\n"
            "Please use the Browse button to manually select the executable."
        )

    def _validate_ghostscript_path(self, path: Path) -> Tuple[bool, str]:
        """
        Validate Ghostscript executable path.

        Args:
            path: Path to Ghostscript executable

        Returns:
            Tuple of (is_valid, version_or_error_message)
        """
        if not path.exists():
            self.gs_status_label.configure(
                text="⚠️ File not found",
                text_color="orange"
            )
            return False, "File not found"

        if not path.is_file():
            self.gs_status_label.configure(
                text="⚠️ Not a file",
                text_color="orange"
            )
            return False, "Not a file"

        # Try to run --version
        try:
            result = subprocess.run(
                [str(path), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse version from output
                version_line = result.stdout.split("\n")[0]
                self.gs_status_label.configure(
                    text=f"✅ {version_line}",
                    text_color="green"
                )
                return True, version_line
            else:
                self.gs_status_label.configure(
                    text="⚠️ Executable failed to run",
                    text_color="orange"
                )
                return False, "Executable failed"

        except subprocess.TimeoutExpired:
            self.gs_status_label.configure(
                text="⚠️ Execution timeout",
                text_color="orange"
            )
            return False, "Timeout"
        except Exception as e:
            self.gs_status_label.configure(
                text=f"⚠️ Error: {str(e)}",
                text_color="orange"
            )
            return False, str(e)

    def _validate_all_settings(self) -> Tuple[bool, List[str]]:
        """
        Validate all settings before saving.

        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []

        # Validate output folder if specified
        output_folder = self.output_folder_entry.get().strip()
        if output_folder and output_folder != "same_folder":
            path = Path(output_folder)
            if not path.exists():
                errors.append(f"Output folder does not exist: {output_folder}")
            elif not path.is_dir():
                errors.append(f"Output path is not a directory: {output_folder}")
            else:
                # Check write permissions
                try:
                    test_file = path / ".squash_write_test"
                    test_file.touch()
                    test_file.unlink()
                except Exception:
                    errors.append(f"No write permission for folder: {output_folder}")

        # Validate Ghostscript path if specified
        gs_path = self.gs_path_entry.get().strip()
        if gs_path:
            is_valid, error = self._validate_ghostscript_path(Path(gs_path))
            if not is_valid:
                errors.append(f"Invalid Ghostscript path: {error}")

        return len(errors) == 0, errors

    def _on_ok(self) -> None:
        """Handle OK button - validate and save settings."""
        # Validate all settings
        is_valid, errors = self._validate_all_settings()

        if not is_valid:
            error_msg = "Please fix the following errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            self._show_error("Validation Errors", error_msg)
            return

        # Save settings
        try:
            settings = self.config_manager.settings

            # Update theme
            settings.theme = self.theme_var.get()

            # Update output location
            output_folder = self.output_folder_entry.get().strip()
            settings.output_location = output_folder if output_folder else "same_folder"

            # Update Ghostscript path
            gs_path = self.gs_path_entry.get().strip()
            settings.ghostscript_path = gs_path if gs_path else None

            # Update log level
            settings.log_level = self.log_level_var.get()

            # Update privacy preferences
            settings.check_updates = self.check_updates_var.get()

            # Save to file
            success = self.config_manager.save_settings(settings)

            if success:
                logger.info("Settings saved successfully")
                self.destroy()
            else:
                self._show_error(
                    "Save Failed",
                    "Failed to save settings to file.\nPlease check file permissions."
                )

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            self._show_error("Error", f"An error occurred while saving settings:\n\n{str(e)}")

    def _on_cancel(self) -> None:
        """Handle Cancel button - discard changes and close."""
        # Restore original theme
        original_theme = self.original_settings.theme
        ctk.set_appearance_mode(original_theme.capitalize())

        logger.info("Settings dialog cancelled")
        self.destroy()

    def _show_error(self, title: str, message: str) -> None:
        """
        Show error dialog.

        Args:
            title: Error dialog title
            message: Error message
        """
        error_dialog = ctk.CTkToplevel(self)
        error_dialog.title(title)
        error_dialog.geometry("450x250")
        error_dialog.transient(self)
        error_dialog.grab_set()
        apply_icon(error_dialog)

        # Center on settings dialog
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 450) // 2
        y = self.winfo_y() + (self.winfo_height() - 250) // 2
        error_dialog.geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(
            error_dialog,
            text=f"❌ {message}",
            wraplength=400,
            justify="left"
        )
        label.pack(padx=20, pady=20)

        button = ctk.CTkButton(
            error_dialog,
            text="OK",
            command=error_dialog.destroy
        )
        button.pack(pady=10)
