"""
Update-available dialog for Squash PDF Compressor.

Shows release notes, a progress bar during download, and launches the
installer when the user confirms.
"""

import logging
import threading
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from ..config.manager import ConfigManager
from ..utils.updater import ReleaseInfo, UpdateChecker
from ._icon import apply_icon

logger = logging.getLogger(__name__)


class UpdateDialog(ctk.CTkToplevel):
    """Modal dialog shown when a new version is available.

    Presents release notes, a download progress bar, and an "Update Now" /
    "Skip This Version" / "Later" choice.  Drives the full download-then-
    install flow internally.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        release: ReleaseInfo,
        config_manager: ConfigManager,
        quit_callback: Callable,
    ):
        """Initialise the update dialog.

        Args:
            parent: The main application window.
            release: ReleaseInfo describing the available update.
            config_manager: App config manager (used to persist skip_version).
            quit_callback: Called to close the main window after the
                           installer is launched.
        """
        super().__init__(parent)
        self._release = release
        self._config = config_manager
        self._checker = UpdateChecker()
        self._quit_callback = quit_callback
        self._installer_path: Path | None = None
        self._download_thread: threading.Thread | None = None

        self.title("Update Available")
        self.geometry("520x500")
        self.minsize(480, 440)
        self.resizable(False, False)
        self.grab_set()  # modal
        self.focus()

        # Centre over parent after geometry is applied
        self.after(50, self._centre_on_parent)

        apply_icon(self)
        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ────────────────────────────────────────────────────── #
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=f"Squash {self._release.version} is available",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(16, 2), sticky="w")

        ctk.CTkLabel(
            header,
            text=f"You have version {self._current_version()}.  "
                 f"Would you like to update now?",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        # ── Release notes ─────────────────────────────────────────────── #
        ctk.CTkLabel(
            self,
            text="What's new:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=1, column=0, padx=20, pady=(12, 2), sticky="w")

        self._notes_box = ctk.CTkTextbox(
            self,
            corner_radius=6,
            border_width=1,
            font=ctk.CTkFont(size=11),
            wrap="word",
            state="normal",
        )
        self._notes_box.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="nsew")
        self._notes_box.insert("end", self._release.body or "No release notes provided.")
        self._notes_box.configure(state="disabled")

        # ── Progress area ─────────────────────────────────────────────── #
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=3, column=0, padx=20, pady=4, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self._progress_bar = ctk.CTkProgressBar(progress_frame)
        self._progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._progress_bar.set(0)
        self._progress_bar.grid_remove()  # hidden until download starts

        self._status_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
        )
        self._status_label.grid(row=1, column=0, sticky="w")

        # ── Buttons ───────────────────────────────────────────────────── #
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=20, pady=(4, 16), sticky="ew")

        self._skip_btn = ctk.CTkButton(
            btn_frame,
            text="Skip This Version",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=self._on_skip,
        )
        self._skip_btn.pack(side="left")

        self._later_btn = ctk.CTkButton(
            btn_frame,
            text="Later",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._on_later,
        )
        self._later_btn.pack(side="right", padx=(8, 0))

        self._update_btn = ctk.CTkButton(
            btn_frame,
            text="Update Now",
            width=120,
            command=self._on_update_now,
        )
        self._update_btn.pack(side="right")

    # ------------------------------------------------------------------ #
    # Event handlers                                                       #
    # ------------------------------------------------------------------ #

    def _on_later(self) -> None:
        self.destroy()

    def _on_skip(self) -> None:
        """Persist this version as skipped so the dialog is suppressed on future startups."""
        self._config.set("skip_version", self._release.version)
        self._config.save_settings()
        logger.info(f"Update {self._release.version} skipped by user")
        self.destroy()

    def _on_update_now(self) -> None:
        self._update_btn.configure(state="disabled", text="Downloading…")
        self._later_btn.configure(state="disabled")
        self._skip_btn.configure(state="disabled")
        self._progress_bar.grid()
        self._safe_set_status("Downloading installer…")

        self._download_thread = threading.Thread(
            target=self._download_worker, daemon=True
        )
        self._download_thread.start()

    # ------------------------------------------------------------------ #
    # Download / install flow                                              #
    # ------------------------------------------------------------------ #

    def _download_worker(self) -> None:
        path = self._checker.download(
            self._release,
            progress_callback=self._on_progress,
        )
        if not self.winfo_exists():
            return
        if path:
            self.after(0, self._on_download_complete, path)
        else:
            self.after(0, self._on_download_failed)

    def _on_progress(self, downloaded: int, total: int) -> None:
        if not self.winfo_exists():
            return
        ratio = downloaded / total if total else 0
        mb_done = downloaded / (1024 * 1024)
        mb_total = total / (1024 * 1024)

        def _update():
            if self.winfo_exists():
                self._progress_bar.set(ratio)
                self._safe_set_status(
                    f"Downloading… {mb_done:.1f} / {mb_total:.1f} MB"
                )

        self.after(0, _update)

    def _on_download_complete(self, path: Path) -> None:
        if not self.winfo_exists():
            return
        self._installer_path = path
        self._progress_bar.set(1)
        self._safe_set_status("Download complete. Launching installer…")

        self.after(
            600,
            lambda: self._checker.install_and_quit(
                self._installer_path,
                quit_callback=self._quit_callback,
            ),
        )

    def _on_download_failed(self) -> None:
        if not self.winfo_exists():
            return
        self._safe_set_status("Download failed. Please try again later.")
        self._update_btn.configure(state="normal", text="Retry")
        self._later_btn.configure(state="normal")
        self._skip_btn.configure(state="normal")
        self._progress_bar.set(0)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _safe_set_status(self, text: str) -> None:
        """Update status label only if dialog still exists."""
        if self.winfo_exists():
            self._status_label.configure(text=text)

    def _centre_on_parent(self) -> None:
        if not self.winfo_exists():
            return
        parent = self.master
        px = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

    @staticmethod
    def _current_version() -> str:
        from ..utils.updater import APP_VERSION
        return APP_VERSION
