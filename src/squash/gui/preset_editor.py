"""
Preset editor dialog for managing custom compression presets.

Provides a modal dialog interface for creating, editing, deleting, and
importing/exporting custom compression presets.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Tuple, List
import logging

from ..core.presets import PresetManager, Preset
from ._icon import apply_icon

logger = logging.getLogger(__name__)


class PresetEditorDialog(ctk.CTkToplevel):
    """
    Custom preset editor dialog.

    Provides a two-pane interface with preset list on the left and editor
    form on the right for managing custom compression presets.
    """

    def __init__(self, parent, preset_manager: PresetManager):
        """
        Initialize preset editor dialog.

        Args:
            parent: Parent window (MainWindow instance)
            preset_manager: PresetManager instance for preset operations
        """
        super().__init__(parent)

        self.preset_manager = preset_manager
        self.parent_window = parent
        self.current_preset: Optional[Preset] = None
        self.has_unsaved_changes = False

        # Configure dialog window
        self.title("Custom Preset Editor")
        self.geometry("850x650")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center dialog on parent
        self._center_on_parent()

        # Build UI
        self._setup_ui()

        # Load preset list
        self._refresh_preset_list()

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self._on_close())

        # Handle window close button
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        apply_icon(self)
        logger.info("Preset editor dialog opened")

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
        """Build the complete two-pane UI layout."""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Configure grid for two columns
        main_frame.grid_columnconfigure(0, weight=0, minsize=250)  # Preset list (fixed width)
        main_frame.grid_columnconfigure(1, weight=1)  # Editor form (expandable)
        main_frame.grid_rowconfigure(0, weight=1)

        # === LEFT PANE: Preset List ===
        self._create_preset_list_pane(main_frame)

        # === RIGHT PANE: Editor Form ===
        self._create_editor_pane(main_frame)

    def _create_preset_list_pane(self, parent) -> None:
        """Create left pane with preset list and management buttons."""
        list_frame = ctk.CTkFrame(parent)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Title
        title_label = ctk.CTkLabel(
            list_frame,
            text="Presets",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(padx=10, pady=(10, 5))

        # Scrollable preset list
        self.preset_list_frame = ctk.CTkScrollableFrame(list_frame, height=450)
        self.preset_list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.preset_list_frame.grid_columnconfigure(0, weight=1)

        # Management buttons
        button_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        # New button
        new_btn = ctk.CTkButton(
            button_frame,
            text="+ New",
            width=100,
            command=self._create_new_preset
        )
        new_btn.grid(row=0, column=0, padx=(0, 5), pady=2)

        # Delete button
        self.delete_btn = ctk.CTkButton(
            button_frame,
            text="- Delete",
            width=100,
            fg_color="darkred",
            hover_color="red",
            command=self._delete_preset,
            state="disabled"
        )
        self.delete_btn.grid(row=0, column=1, padx=(5, 0), pady=2)

        # Export button
        self.export_btn = ctk.CTkButton(
            button_frame,
            text="↑ Export",
            width=100,
            command=self._export_preset,
            state="disabled"
        )
        self.export_btn.grid(row=1, column=0, padx=(0, 5), pady=2)

        # Import button
        import_btn = ctk.CTkButton(
            button_frame,
            text="↓ Import",
            width=100,
            command=self._import_preset
        )
        import_btn.grid(row=1, column=1, padx=(5, 0), pady=2)

    def _create_editor_pane(self, parent) -> None:
        """Create right pane with preset editor form."""
        editor_frame = ctk.CTkFrame(parent)
        editor_frame.grid(row=0, column=1, sticky="nsew")
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(0, weight=1)

        # Scrollable form container
        self.editor_scroll = ctk.CTkScrollableFrame(editor_frame)
        self.editor_scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.editor_scroll.grid_columnconfigure(1, weight=1)

        current_row = 0

        # === SECTION 1: Basic Info ===
        current_row = self._create_basic_info_section(self.editor_scroll, current_row)

        # === SECTION 2: Quality Level ===
        current_row = self._create_quality_section(self.editor_scroll, current_row)

        # === SECTION 3: Image Resolution ===
        current_row = self._create_resolution_section(self.editor_scroll, current_row)

        # === SAVE/REVERT BUTTONS ===
        button_container = ctk.CTkFrame(editor_frame, fg_color="transparent")
        button_container.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        button_container.grid_columnconfigure(0, weight=1)

        btn_right_frame = ctk.CTkFrame(button_container, fg_color="transparent")
        btn_right_frame.grid(row=0, column=0, sticky="e")

        # Revert button
        self.revert_btn = ctk.CTkButton(
            btn_right_frame,
            text="Revert",
            width=100,
            fg_color="gray",
            hover_color="darkgray",
            command=self._revert_changes,
            state="disabled"
        )
        self.revert_btn.pack(side="left", padx=5)

        # Save button
        self.save_btn = ctk.CTkButton(
            btn_right_frame,
            text="Save",
            width=100,
            command=self._save_preset,
            state="disabled"
        )
        self.save_btn.pack(side="left", padx=5)

    def _create_basic_info_section(self, parent, start_row: int) -> int:
        """Create basic info section (name, display name, description)."""
        # Section title
        title = ctk.CTkLabel(
            parent,
            text="Basic Information",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.grid(row=start_row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        row = start_row + 1

        # Name field
        name_label = ctk.CTkLabel(parent, text="Name:")
        name_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.name_entry = ctk.CTkEntry(parent, placeholder_text="e.g., my_custom")
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.name_entry.bind("<KeyRelease>", lambda e: self._on_field_change())

        row += 1

        # Display name field
        display_label = ctk.CTkLabel(parent, text="Display Name:")
        display_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.display_entry = ctk.CTkEntry(parent, placeholder_text="e.g., My Custom Preset")
        self.display_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.display_entry.bind("<KeyRelease>", lambda e: self._on_field_change())

        row += 1

        # Description field
        desc_label = ctk.CTkLabel(parent, text="Description:")
        desc_label.grid(row=row, column=0, sticky="nw", padx=10, pady=5)

        self.desc_text = ctk.CTkTextbox(parent, height=60)
        self.desc_text.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.desc_text.bind("<KeyRelease>", lambda e: self._on_field_change())

        row += 1

        # Target reduction field
        reduction_label = ctk.CTkLabel(parent, text="Target Reduction:")
        reduction_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.reduction_entry = ctk.CTkEntry(parent, placeholder_text="e.g., 40-60%")
        self.reduction_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.reduction_entry.bind("<KeyRelease>", lambda e: self._on_field_change())

        return row + 1

    def _create_quality_section(self, parent, start_row: int) -> int:
        """Create quality level section (PDFSETTINGS)."""
        # Section title
        title = ctk.CTkLabel(
            parent,
            text="Quality Level",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.grid(row=start_row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))

        row = start_row + 1

        # PDF settings radio buttons
        settings_label = ctk.CTkLabel(parent, text="PDF Settings:")
        settings_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.pdf_settings_var = ctk.StringVar(value="/ebook")

        radio_frame = ctk.CTkFrame(parent, fg_color="transparent")
        radio_frame.grid(row=row, column=1, sticky="w", padx=10, pady=5)

        settings_options = [
            ("/screen", "Screen (72 DPI - smallest)"),
            ("/ebook", "Ebook (150 DPI - balanced)"),
            ("/printer", "Printer (300 DPI - high quality)"),
            ("/prepress", "Prepress (300 DPI - professional)"),
        ]

        for i, (value, text) in enumerate(settings_options):
            radio = ctk.CTkRadioButton(
                radio_frame,
                text=text,
                variable=self.pdf_settings_var,
                value=value,
                command=self._on_field_change
            )
            radio.grid(row=i, column=0, sticky="w", pady=2)

        return row + 5  # Account for radio buttons

    def _create_resolution_section(self, parent, start_row: int) -> int:
        """Create image resolution section (DPI settings)."""
        # Section title
        title = ctk.CTkLabel(
            parent,
            text="Image Resolution",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.grid(row=start_row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))

        row = start_row + 1

        # Color image resolution
        color_label = ctk.CTkLabel(parent, text="Color DPI:")
        color_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.color_dpi_entry = ctk.CTkEntry(parent, placeholder_text="50-2400")
        self.color_dpi_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.color_dpi_entry.bind("<KeyRelease>", lambda e: self._on_field_change())

        row += 1

        # Gray image resolution
        gray_label = ctk.CTkLabel(parent, text="Gray DPI:")
        gray_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.gray_dpi_entry = ctk.CTkEntry(parent, placeholder_text="50-2400")
        self.gray_dpi_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.gray_dpi_entry.bind("<KeyRelease>", lambda e: self._on_field_change())

        row += 1

        # Mono image resolution
        mono_label = ctk.CTkLabel(parent, text="Mono DPI:")
        mono_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.mono_dpi_entry = ctk.CTkEntry(parent, placeholder_text="50-2400")
        self.mono_dpi_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.mono_dpi_entry.bind("<KeyRelease>", lambda e: self._on_field_change())

        row += 1

        # Info label
        info = ctk.CTkLabel(
            parent,
            text="DPI values must be between 50 and 2400",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        info.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        return row + 1

    def _refresh_preset_list(self) -> None:
        """Reload preset list from manager and update UI."""
        # Clear existing items
        for widget in self.preset_list_frame.winfo_children():
            widget.destroy()

        # Get all presets
        presets = self.preset_manager.list_presets()

        # Create preset items
        for i, preset in enumerate(presets):
            self._create_preset_item(preset, i)

    def _create_preset_item(self, preset: Preset, row: int) -> None:
        """Create a single preset item in the list."""
        # Container frame
        item_frame = ctk.CTkFrame(self.preset_list_frame)
        item_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        item_frame.grid_columnconfigure(0, weight=1)

        # Preset name and badge
        name_text = preset.display_name
        if preset.is_custom:
            name_text += " (Custom)"

        name_button = ctk.CTkButton(
            item_frame,
            text=name_text,
            anchor="w",
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            command=lambda p=preset: self._select_preset(p)
        )
        name_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # DPI info
        dpi_label = ctk.CTkLabel(
            item_frame,
            text=f"{preset.dpi} DPI",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        dpi_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))

    def _select_preset(self, preset: Preset) -> None:
        """Load preset into editor form."""
        # Check for unsaved changes
        if self.has_unsaved_changes:
            if not self._confirm_discard_changes():
                return

        self.current_preset = preset

        # Populate form fields
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, preset.name)

        self.display_entry.delete(0, "end")
        self.display_entry.insert(0, preset.display_name)

        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", preset.description)

        self.reduction_entry.delete(0, "end")
        self.reduction_entry.insert(0, preset.target_reduction)

        self.pdf_settings_var.set(preset.pdf_settings)

        self.color_dpi_entry.delete(0, "end")
        self.color_dpi_entry.insert(0, str(preset.color_image_resolution))

        self.gray_dpi_entry.delete(0, "end")
        self.gray_dpi_entry.insert(0, str(preset.gray_image_resolution))

        self.mono_dpi_entry.delete(0, "end")
        self.mono_dpi_entry.insert(0, str(preset.mono_image_resolution))

        # Enable/disable buttons based on preset type
        if preset.is_custom:
            self.save_btn.configure(state="normal")
            self.delete_btn.configure(state="normal")
        else:
            self.save_btn.configure(state="disabled")
            self.delete_btn.configure(state="disabled")

        self.export_btn.configure(state="normal")
        self.revert_btn.configure(state="normal")

        # Clear unsaved changes flag
        self.has_unsaved_changes = False

        logger.info(f"Selected preset: {preset.name}")

    def _on_field_change(self) -> None:
        """Handle form field changes."""
        if self.current_preset and self.current_preset.is_custom:
            self.has_unsaved_changes = True
            self.save_btn.configure(state="normal")
            self.revert_btn.configure(state="normal")

    def _validate_preset_data(self) -> Tuple[bool, List[str]]:
        """
        Validate all form fields.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Get field values
        name = self.name_entry.get().strip()
        display_name = self.display_entry.get().strip()
        color_dpi = self.color_dpi_entry.get().strip()
        gray_dpi = self.gray_dpi_entry.get().strip()
        mono_dpi = self.mono_dpi_entry.get().strip()

        # Validate name
        if not name:
            errors.append("Name is required")
        elif len(name) > 50:
            errors.append("Name must be 50 characters or less")
        elif not name.replace("_", "").replace("-", "").replace(" ", "").isalnum():
            errors.append("Name can only contain letters, numbers, spaces, hyphens, and underscores")

        # Validate display name
        if not display_name:
            errors.append("Display name is required")
        elif len(display_name) > 100:
            errors.append("Display name must be 100 characters or less")

        # Validate DPI values
        try:
            color_val = int(color_dpi)
            if not (50 <= color_val <= 2400):
                errors.append("Color DPI must be between 50 and 2400")
        except ValueError:
            errors.append("Color DPI must be a valid number")

        try:
            gray_val = int(gray_dpi)
            if not (50 <= gray_val <= 2400):
                errors.append("Gray DPI must be between 50 and 2400")
        except ValueError:
            errors.append("Gray DPI must be a valid number")

        try:
            mono_val = int(mono_dpi)
            if not (50 <= mono_val <= 2400):
                errors.append("Mono DPI must be between 50 and 2400")
        except ValueError:
            errors.append("Mono DPI must be a valid number")

        return len(errors) == 0, errors

    def _save_preset(self) -> None:
        """Validate and save current preset."""
        if not self.current_preset:
            messagebox.showerror("Error", "No preset selected")
            return

        if not self.current_preset.is_custom:
            messagebox.showerror("Error", "Cannot modify built-in presets")
            return

        # Validate form data
        is_valid, errors = self._validate_preset_data()
        if not is_valid:
            error_msg = "Please fix the following errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            messagebox.showerror("Validation Errors", error_msg)
            return

        # Create updated preset
        try:
            updated_preset = Preset(
                name=self.name_entry.get().strip(),
                display_name=self.display_entry.get().strip(),
                description=self.desc_text.get("1.0", "end").strip(),
                dpi=int(self.color_dpi_entry.get().strip()),  # Use color DPI as main DPI
                color_image_resolution=int(self.color_dpi_entry.get().strip()),
                gray_image_resolution=int(self.gray_dpi_entry.get().strip()),
                mono_image_resolution=int(self.mono_dpi_entry.get().strip()),
                pdf_settings=self.pdf_settings_var.get(),
                target_reduction=self.reduction_entry.get().strip(),
                is_custom=True
            )

            # Update preset
            self.preset_manager.update_preset(self.current_preset.name, updated_preset)

            # Update current preset reference
            self.current_preset = updated_preset

            # Refresh list
            self._refresh_preset_list()

            # Clear unsaved changes flag
            self.has_unsaved_changes = False

            messagebox.showinfo("Success", f"Preset '{updated_preset.display_name}' saved successfully")
            logger.info(f"Saved preset: {updated_preset.name}")

        except Exception as e:
            logger.error(f"Error saving preset: {e}")
            messagebox.showerror("Error", f"Failed to save preset:\n\n{str(e)}")

    def _create_new_preset(self) -> None:
        """Create a new preset with default values."""
        # Check for unsaved changes
        if self.has_unsaved_changes:
            if not self._confirm_discard_changes():
                return

        # Generate unique name
        base_name = "new_preset"
        name = base_name
        counter = 1
        while name in self.preset_manager.get_preset_names():
            name = f"{base_name}_{counter}"
            counter += 1

        # Create new preset with defaults
        try:
            new_preset = Preset(
                name=name,
                display_name="New Preset",
                description="Custom compression preset",
                dpi=150,
                color_image_resolution=150,
                gray_image_resolution=150,
                mono_image_resolution=300,
                pdf_settings="/ebook",
                target_reduction="50-70%",
                is_custom=True
            )

            # Add to manager
            self.preset_manager.add_custom_preset(new_preset)

            # Refresh list and select new preset
            self._refresh_preset_list()
            self._select_preset(new_preset)

            messagebox.showinfo("Success", f"Created new preset '{new_preset.display_name}'")
            logger.info(f"Created new preset: {new_preset.name}")

        except Exception as e:
            logger.error(f"Error creating new preset: {e}")
            messagebox.showerror("Error", f"Failed to create new preset:\n\n{str(e)}")

    def _delete_preset(self) -> None:
        """Delete selected custom preset with confirmation."""
        if not self.current_preset:
            messagebox.showerror("Error", "No preset selected")
            return

        if not self.current_preset.is_custom:
            messagebox.showerror("Error", "Cannot delete built-in presets")
            return

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the preset '{self.current_preset.display_name}'?\n\nThis action cannot be undone."
        )

        if not result:
            return

        try:
            preset_name = self.current_preset.name
            self.preset_manager.delete_preset(preset_name)

            # Clear current preset
            self.current_preset = None

            # Clear form
            self._clear_form()

            # Refresh list
            self._refresh_preset_list()

            messagebox.showinfo("Success", f"Preset '{preset_name}' deleted successfully")
            logger.info(f"Deleted preset: {preset_name}")

        except Exception as e:
            logger.error(f"Error deleting preset: {e}")
            messagebox.showerror("Error", f"Failed to delete preset:\n\n{str(e)}")

    def _export_preset(self) -> None:
        """Export selected preset to JSON file."""
        if not self.current_preset:
            messagebox.showerror("Error", "No preset selected")
            return

        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            title="Export Preset",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.current_preset.name}.json"
        )

        if not file_path:
            return

        try:
            self.preset_manager.export_preset(self.current_preset.name, Path(file_path))
            messagebox.showinfo("Success", f"Preset exported to:\n{file_path}")
            logger.info(f"Exported preset to: {file_path}")

        except Exception as e:
            logger.error(f"Error exporting preset: {e}")
            messagebox.showerror("Error", f"Failed to export preset:\n\n{str(e)}")

    def _import_preset(self) -> None:
        """Import preset from JSON file."""
        # Ask for file location
        file_path = filedialog.askopenfilename(
            title="Import Preset",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Import preset (doesn't add yet)
            imported_preset = self.preset_manager.import_preset(Path(file_path))

            # Check if name conflicts
            if imported_preset.name in self.preset_manager.get_preset_names():
                result = messagebox.askyesno(
                    "Name Conflict",
                    f"A preset named '{imported_preset.name}' already exists.\n\nDo you want to overwrite it?"
                )

                if not result:
                    # Ask for new name
                    new_name = self._prompt_for_name(imported_preset.name)
                    if not new_name:
                        return
                    imported_preset.name = new_name

                    # Add preset
                    self.preset_manager.add_custom_preset(imported_preset)
                else:
                    # Overwrite existing
                    self.preset_manager.update_preset(imported_preset.name, imported_preset)
            else:
                # Add new preset
                self.preset_manager.add_custom_preset(imported_preset)

            # Refresh list and select imported preset
            self._refresh_preset_list()
            self._select_preset(imported_preset)

            messagebox.showinfo("Success", f"Preset '{imported_preset.display_name}' imported successfully")
            logger.info(f"Imported preset from: {file_path}")

        except Exception as e:
            logger.error(f"Error importing preset: {e}")
            messagebox.showerror("Error", f"Failed to import preset:\n\n{str(e)}")

    def _revert_changes(self) -> None:
        """Revert form to current preset values."""
        if self.current_preset:
            self._select_preset(self.current_preset)

    def _clear_form(self) -> None:
        """Clear all form fields."""
        self.name_entry.delete(0, "end")
        self.display_entry.delete(0, "end")
        self.desc_text.delete("1.0", "end")
        self.reduction_entry.delete(0, "end")
        self.pdf_settings_var.set("/ebook")
        self.color_dpi_entry.delete(0, "end")
        self.gray_dpi_entry.delete(0, "end")
        self.mono_dpi_entry.delete(0, "end")

        self.save_btn.configure(state="disabled")
        self.delete_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.revert_btn.configure(state="disabled")

    def _confirm_discard_changes(self) -> bool:
        """Confirm discarding unsaved changes."""
        result = messagebox.askyesno(
            "Unsaved Changes",
            "You have unsaved changes.\n\nDiscard changes and continue?"
        )
        return result

    def _prompt_for_name(self, suggested_name: str) -> Optional[str]:
        """Prompt user for a new preset name."""
        # Simple dialog for name input
        dialog = ctk.CTkInputDialog(
            text=f"Enter a new name for the preset:",
            title="Rename Preset"
        )
        new_name = dialog.get_input()
        return new_name if new_name else None

    def _on_close(self) -> None:
        """Handle dialog close event."""
        if self.has_unsaved_changes:
            if not self._confirm_discard_changes():
                return

        logger.info("Preset editor dialog closed")
        self.destroy()
