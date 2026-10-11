"""
Preset editor dialog for managing custom compression presets.

Two-pane modal: preset list on the left, editor form on the right. Built-in
presets are read-only but can be duplicated as a starting point.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog
from typing import List, Optional, Tuple

import customtkinter as ctk

from ..core.presets import COLOR_CONVERSION_OPTIONS, Preset, PresetManager
from ._icon import apply_icon
from .dialogs import ask_yes_no, fit_to_content, show_error

logger = logging.getLogger(__name__)

_MUTED = ("gray45", "gray60")
_OK = ("#43A047", "#50C878")

_PDF_SETTINGS_OPTIONS = (
    ("/screen", "Screen - smallest files, 72 DPI images"),
    ("/ebook", "Ebook - balanced, 150 DPI images"),
    ("/printer", "Printer - high quality, 300 DPI images"),
    ("/prepress", "Prepress - professional printing"),
)


class PresetEditorDialog(ctk.CTkToplevel):
    """Create, edit, duplicate, delete, import and export compression presets."""

    def __init__(self, parent, preset_manager: PresetManager):
        """
        Args:
            parent: Parent window (MainWindow instance).
            preset_manager: PresetManager instance for preset operations.
        """
        super().__init__(parent)
        self.preset_manager = preset_manager
        self.current_preset: Optional[Preset] = None
        self.has_unsaved_changes = False
        self._preset_buttons: dict[str, ctk.CTkButton] = {}

        self.title("Manage Presets")
        self.transient(parent)

        self._setup_ui()
        self._refresh_preset_list()
        self._clear_form()

        self.bind("<Escape>", lambda _e: self._on_close())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        apply_icon(self)
        width, height = fit_to_content(self, min_width=940, parent=parent)
        self.minsize(width, height)
        self.grab_set()
        self.focus()
        logger.info("Preset editor dialog opened")

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)
        main.grid_columnconfigure(0, weight=0, minsize=260)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self._create_list_pane(main)
        self._create_editor_pane(main)

    def _create_list_pane(self, parent) -> None:
        pane = ctk.CTkFrame(parent)
        pane.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        pane.grid_rowconfigure(1, weight=1)
        pane.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(pane, text="Presets", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )

        self.preset_list_frame = ctk.CTkScrollableFrame(pane, width=230, height=420)
        self.preset_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.preset_list_frame.grid_columnconfigure(0, weight=1)

        buttons = ctk.CTkFrame(pane, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        buttons.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(buttons, text="New", command=self._create_new_preset).grid(
            row=0, column=0, padx=(0, 4), pady=2, sticky="ew"
        )
        self.duplicate_btn = ctk.CTkButton(
            buttons, text="Duplicate", command=self._duplicate_preset, state="disabled"
        )
        self.duplicate_btn.grid(row=0, column=1, padx=(4, 0), pady=2, sticky="ew")

        self.import_btn = ctk.CTkButton(
            buttons,
            text="Import...",
            command=self._import_preset,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
        )
        self.import_btn.grid(row=1, column=0, padx=(0, 4), pady=2, sticky="ew")
        self.export_btn = ctk.CTkButton(
            buttons,
            text="Export...",
            command=self._export_preset,
            state="disabled",
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
        )
        self.export_btn.grid(row=1, column=1, padx=(4, 0), pady=2, sticky="ew")

        self.delete_btn = ctk.CTkButton(
            buttons,
            text="Delete",
            fg_color=("#C62828", "#B71C1C"),
            hover_color=("#B71C1C", "#8E1414"),
            command=self._delete_preset,
            state="disabled",
        )
        self.delete_btn.grid(row=2, column=0, columnspan=2, pady=(8, 2), sticky="ew")

    def _create_editor_pane(self, parent) -> None:
        pane = ctk.CTkFrame(parent)
        pane.grid(row=0, column=1, sticky="nsew")
        pane.grid_columnconfigure(0, weight=1)
        pane.grid_rowconfigure(0, weight=1)

        # Plain frame so the dialog sizes itself to show the whole form without scrolling.
        self.editor_scroll = ctk.CTkFrame(pane, fg_color="transparent")
        self.editor_scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.editor_scroll.grid_columnconfigure(1, weight=1)

        row = self._create_basic_info_section(self.editor_scroll, 0)
        row = self._create_quality_section(self.editor_scroll, row)
        self._create_resolution_section(self.editor_scroll, row)

        footer = ctk.CTkFrame(pane, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        footer.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            footer, text="", font=ctk.CTkFont(size=11), text_color=_MUTED, anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.revert_btn = ctk.CTkButton(
            footer,
            text="Revert",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("#1A1208", "#F0E8DC"),
            command=self._revert_changes,
            state="disabled",
        )
        self.revert_btn.grid(row=0, column=1, padx=(0, 8))
        self.save_btn = ctk.CTkButton(
            footer, text="Save", width=110, command=self._save_preset, state="disabled"
        )
        self.save_btn.grid(row=0, column=2)

    def _entry(self, parent, row: int, label: str, placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder)
        entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        entry.bind("<KeyRelease>", lambda _e: self._on_field_change())
        return entry

    def _create_basic_info_section(self, parent, start_row: int) -> int:
        ctk.CTkLabel(
            parent, text="Basic Information", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=start_row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row = start_row + 1
        self.name_entry = self._entry(parent, row, "Name:", "e.g. email_friendly")
        row += 1
        self.display_entry = self._entry(parent, row, "Display name:", "e.g. Email Friendly")
        row += 1

        ctk.CTkLabel(parent, text="Description:").grid(
            row=row, column=0, sticky="nw", padx=10, pady=5
        )
        self.desc_text = ctk.CTkTextbox(parent, height=60)
        self.desc_text.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.desc_text.bind("<KeyRelease>", lambda _e: self._on_field_change())
        row += 1

        self.reduction_entry = self._entry(parent, row, "Expected reduction:", "e.g. 40-60%")
        return row + 1

    def _create_quality_section(self, parent, start_row: int) -> int:
        ctk.CTkLabel(parent, text="Quality", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=start_row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5)
        )
        row = start_row + 1

        ctk.CTkLabel(parent, text="Base profile:").grid(
            row=row, column=0, sticky="nw", padx=10, pady=5
        )
        self.pdf_settings_var = ctk.StringVar(value="/ebook")
        profile_frame = ctk.CTkFrame(parent, fg_color="transparent")
        profile_frame.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        for i, (value, text) in enumerate(_PDF_SETTINGS_OPTIONS):
            ctk.CTkRadioButton(
                profile_frame,
                text=text,
                variable=self.pdf_settings_var,
                value=value,
                command=self._on_field_change,
            ).grid(row=i, column=0, sticky="w", pady=2)
        row += 1

        ctk.CTkLabel(parent, text="Colors:").grid(row=row, column=0, sticky="nw", padx=10, pady=5)
        self.color_var = ctk.StringVar(value="/RGB")
        color_frame = ctk.CTkFrame(parent, fg_color="transparent")
        color_frame.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        for i, (value, text) in enumerate(COLOR_CONVERSION_OPTIONS.items()):
            ctk.CTkRadioButton(
                color_frame,
                text=text,
                variable=self.color_var,
                value=value,
                command=self._on_field_change,
            ).grid(row=i, column=0, sticky="w", pady=2)
        row += 1

        ctk.CTkLabel(
            parent,
            text="Keep original colors for documents that will be printed professionally "
            "(CMYK). Grayscale gives the smallest files for text-only scans.",
            font=ctk.CTkFont(size=11),
            text_color=_MUTED,
            wraplength=520,
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))
        return row + 1

    def _create_resolution_section(self, parent, start_row: int) -> int:
        ctk.CTkLabel(
            parent, text="Image Resolution", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=start_row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
        row = start_row + 1
        self.color_dpi_entry = self._entry(parent, row, "Color images (DPI):", "50-2400")
        row += 1
        self.gray_dpi_entry = self._entry(parent, row, "Gray images (DPI):", "50-2400")
        row += 1
        self.mono_dpi_entry = self._entry(parent, row, "Black & white (DPI):", "50-2400")
        row += 1
        ctk.CTkLabel(
            parent,
            text="Images above these resolutions are downsampled. 72 = screen, 150 = good "
            "general use, 300 = print.",
            font=ctk.CTkFont(size=11),
            text_color=_MUTED,
            wraplength=520,
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))
        return row + 1

    # ------------------------------------------------------------------ #
    # Preset list                                                          #
    # ------------------------------------------------------------------ #

    def _refresh_preset_list(self) -> None:
        for widget in self.preset_list_frame.winfo_children():
            widget.destroy()
        self._preset_buttons.clear()

        for row, preset in enumerate(self.preset_manager.list_presets()):
            item = ctk.CTkFrame(self.preset_list_frame)
            item.grid(row=row, column=0, sticky="ew", padx=4, pady=3)
            item.grid_columnconfigure(0, weight=1)

            button = ctk.CTkButton(
                item,
                text=preset.display_name,
                anchor="w",
                fg_color=("gray85", "gray25"),
                hover_color=("gray75", "gray35"),
                text_color=("#1A1208", "#F0E8DC"),
                command=lambda p=preset: self._select_preset(p),
            )
            button.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
            self._preset_buttons[preset.name] = button

            kind = "Custom" if preset.is_custom else "Built-in"
            ctk.CTkLabel(
                item,
                text=f"{kind}  •  {preset.dpi} DPI  •  {preset.pdf_settings.lstrip('/')}",
                font=ctk.CTkFont(size=10),
                text_color=_MUTED,
            ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))

        self._highlight_selection()

    def _highlight_selection(self) -> None:
        for name, button in self._preset_buttons.items():
            selected = self.current_preset is not None and name == self.current_preset.name
            button.configure(
                fg_color=("#C86B00", "#E07B10") if selected else ("gray85", "gray25"),
                text_color=("#FFFFFF", "#FFFFFF") if selected else ("#1A1208", "#F0E8DC"),
            )

    def _select_preset(self, preset: Preset) -> None:
        if self.has_unsaved_changes and not self._confirm_discard_changes():
            return

        self.current_preset = preset
        self._fill_form(preset)

        editable = preset.is_custom
        for widget in (
            self.name_entry,
            self.display_entry,
            self.reduction_entry,
            self.color_dpi_entry,
            self.gray_dpi_entry,
            self.mono_dpi_entry,
        ):
            widget.configure(state="normal" if editable else "disabled")
        self.desc_text.configure(state="normal" if editable else "disabled")

        self.save_btn.configure(state="disabled")
        self.revert_btn.configure(state="disabled")
        self.delete_btn.configure(state="normal" if editable else "disabled")
        self.duplicate_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        self.has_unsaved_changes = False
        self._set_status(
            "Built-in presets cannot be edited. Use Duplicate to make your own copy."
            if not editable
            else ""
        )
        self._highlight_selection()
        logger.debug(f"Selected preset: {preset.name}")

    def _fill_form(self, preset: Preset) -> None:
        self._set_fields_enabled(True)
        self._set_entry(self.name_entry, preset.name)
        self._set_entry(self.display_entry, preset.display_name)
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", preset.description)
        self._set_entry(self.reduction_entry, preset.target_reduction)
        self.pdf_settings_var.set(preset.pdf_settings)
        self.color_var.set(preset.color_conversion)
        self._set_entry(self.color_dpi_entry, str(preset.color_image_resolution))
        self._set_entry(self.gray_dpi_entry, str(preset.gray_image_resolution))
        self._set_entry(self.mono_dpi_entry, str(preset.mono_image_resolution))

    def _set_fields_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in (
            self.name_entry,
            self.display_entry,
            self.reduction_entry,
            self.color_dpi_entry,
            self.gray_dpi_entry,
            self.mono_dpi_entry,
            self.desc_text,
        ):
            widget.configure(state=state)

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)

    def _clear_form(self) -> None:
        self.current_preset = None
        self._set_fields_enabled(True)
        for entry in (
            self.name_entry,
            self.display_entry,
            self.reduction_entry,
            self.color_dpi_entry,
            self.gray_dpi_entry,
            self.mono_dpi_entry,
        ):
            entry.delete(0, "end")
        self.desc_text.delete("1.0", "end")
        self.pdf_settings_var.set("/ebook")
        self.color_var.set("/RGB")
        self._set_fields_enabled(False)

        for button in (
            self.save_btn,
            self.revert_btn,
            self.delete_btn,
            self.duplicate_btn,
            self.export_btn,
        ):
            button.configure(state="disabled")
        self.has_unsaved_changes = False
        self._set_status("Select a preset to view it, or click New.")
        self._highlight_selection()

    def _set_status(self, text: str, ok: bool = False) -> None:
        self.status_label.configure(text=text, text_color=_OK if ok else _MUTED)

    def _on_field_change(self) -> None:
        if self.current_preset and self.current_preset.is_custom:
            self.has_unsaved_changes = True
            self.save_btn.configure(state="normal")
            self.revert_btn.configure(state="normal")
            self._set_status("Unsaved changes")

    # ------------------------------------------------------------------ #
    # Form → Preset                                                        #
    # ------------------------------------------------------------------ #

    def _read_form(self) -> Tuple[Optional[Preset], List[str]]:
        """Build a Preset from the form, returning (preset, errors)."""
        errors: List[str] = []

        def _dpi(entry: ctk.CTkEntry, label: str) -> int:
            try:
                return int(entry.get().strip())
            except ValueError:
                errors.append(f"{label} must be a whole number between 50 and 2400.")
                return 0

        color_dpi = _dpi(self.color_dpi_entry, "Color DPI")
        gray_dpi = _dpi(self.gray_dpi_entry, "Gray DPI")
        mono_dpi = _dpi(self.mono_dpi_entry, "Black & white DPI")
        if errors:
            return None, errors

        preset = Preset(
            name=self.name_entry.get().strip(),
            display_name=self.display_entry.get().strip(),
            description=self.desc_text.get("1.0", "end").strip(),
            dpi=color_dpi,
            color_image_resolution=color_dpi,
            gray_image_resolution=gray_dpi,
            mono_image_resolution=mono_dpi,
            pdf_settings=self.pdf_settings_var.get(),
            target_reduction=self.reduction_entry.get().strip() or "varies",
            is_custom=True,
            color_conversion=self.color_var.get(),
        )
        valid, error = self.preset_manager.validate_preset(preset)
        if not valid and error:
            errors.append(error)
        return preset, errors

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #

    def _save_preset(self) -> None:
        if not self.current_preset or not self.current_preset.is_custom:
            return
        preset, errors = self._read_form()
        if errors or preset is None:
            show_error(self, "Check the Preset", "\n".join(f"• {e}" for e in errors))
            return
        try:
            self.preset_manager.update_preset(self.current_preset.name, preset)
        except Exception as exc:
            logger.error(f"Error saving preset: {exc}")
            show_error(self, "Save Failed", str(exc))
            return

        self.current_preset = preset
        self.has_unsaved_changes = False
        self.save_btn.configure(state="disabled")
        self.revert_btn.configure(state="disabled")
        self._refresh_preset_list()
        self._set_status(f"Saved '{preset.display_name}'", ok=True)
        logger.info(f"Saved preset: {preset.name}")

    def _unique_name(self, base: str) -> str:
        name, counter = base, 1
        while name in self.preset_manager.get_preset_names():
            name = f"{base}_{counter}"
            counter += 1
        return name

    def _add_and_select(self, preset: Preset, verb: str) -> None:
        try:
            self.preset_manager.add_custom_preset(preset)
        except Exception as exc:
            logger.error(f"Error creating preset: {exc}")
            show_error(self, "Could Not Create Preset", str(exc))
            return
        self._refresh_preset_list()
        self.has_unsaved_changes = False
        self._select_preset(preset)
        self._set_status(f"{verb} '{preset.display_name}' - edit it and click Save.", ok=True)
        logger.info(f"{verb} preset: {preset.name}")

    def _create_new_preset(self) -> None:
        if self.has_unsaved_changes and not self._confirm_discard_changes():
            return
        preset = Preset(
            name=self._unique_name("new_preset"),
            display_name="New Preset",
            description="Custom compression preset",
            dpi=150,
            color_image_resolution=150,
            gray_image_resolution=150,
            mono_image_resolution=300,
            pdf_settings="/ebook",
            target_reduction="50-70%",
            is_custom=True,
        )
        self._add_and_select(preset, "Created")

    def _duplicate_preset(self) -> None:
        if not self.current_preset:
            return
        if self.has_unsaved_changes and not self._confirm_discard_changes():
            return
        source = self.current_preset
        copy = Preset(
            name=self._unique_name(f"{source.name}_copy"),
            display_name=f"{source.display_name} (Copy)",
            description=source.description,
            dpi=source.dpi,
            color_image_resolution=source.color_image_resolution,
            gray_image_resolution=source.gray_image_resolution,
            mono_image_resolution=source.mono_image_resolution,
            pdf_settings=source.pdf_settings,
            target_reduction=source.target_reduction,
            is_custom=True,
            color_conversion=source.color_conversion,
        )
        self._add_and_select(copy, "Duplicated")

    def _delete_preset(self) -> None:
        if not self.current_preset or not self.current_preset.is_custom:
            return
        if not ask_yes_no(
            self,
            "Delete Preset",
            f"Delete the preset '{self.current_preset.display_name}'?\n\nThis cannot be undone.",
            yes_text="Delete",
            no_text="Cancel",
            danger=True,
        ):
            return
        name = self.current_preset.name
        try:
            self.preset_manager.delete_preset(name)
        except Exception as exc:
            logger.error(f"Error deleting preset: {exc}")
            show_error(self, "Delete Failed", str(exc))
            return
        self._clear_form()
        self._refresh_preset_list()
        self._set_status(f"Deleted '{name}'", ok=True)
        logger.info(f"Deleted preset: {name}")

    def _export_preset(self) -> None:
        if not self.current_preset:
            return
        file_path = filedialog.asksaveasfilename(
            title="Export Preset",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.current_preset.name}.json",
            parent=self,
        )
        if not file_path:
            return
        if self.preset_manager.export_preset(self.current_preset.name, Path(file_path)):
            self._set_status(f"Exported to {Path(file_path).name}", ok=True)
        else:
            show_error(self, "Export Failed", f"Could not write {file_path}.")

    def _import_preset(self) -> None:
        if self.has_unsaved_changes and not self._confirm_discard_changes():
            return
        file_path = filedialog.askopenfilename(
            title="Import Preset",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self,
        )
        if not file_path:
            return
        try:
            imported = self.preset_manager.import_preset(Path(file_path))
            existing = self.preset_manager.get_preset_names()
            if imported.name in existing:
                target = self.preset_manager.get_preset(imported.name)
                if target.is_custom and ask_yes_no(
                    self,
                    "Preset Exists",
                    f"A preset named '{imported.name}' already exists.\n\nReplace it?",
                    yes_text="Replace",
                    no_text="Keep Both",
                ):
                    self.preset_manager.update_preset(imported.name, imported)
                else:
                    imported.name = self._unique_name(imported.name)
                    self.preset_manager.add_custom_preset(imported)
            else:
                self.preset_manager.add_custom_preset(imported)
        except Exception as exc:
            logger.error(f"Error importing preset: {exc}")
            show_error(self, "Import Failed", str(exc))
            return

        self._refresh_preset_list()
        self.has_unsaved_changes = False
        self._select_preset(imported)
        self._set_status(f"Imported '{imported.display_name}'", ok=True)
        logger.info(f"Imported preset from: {file_path}")

    def _revert_changes(self) -> None:
        if self.current_preset:
            self.has_unsaved_changes = False
            self._select_preset(self.current_preset)

    def _confirm_discard_changes(self) -> bool:
        return ask_yes_no(
            self,
            "Unsaved Changes",
            "You have unsaved changes to this preset.\n\nDiscard them?",
            yes_text="Discard",
            no_text="Keep Editing",
            danger=True,
        )

    def _on_close(self) -> None:
        if self.has_unsaved_changes and not self._confirm_discard_changes():
            return
        logger.info("Preset editor dialog closed")
        self.destroy()
