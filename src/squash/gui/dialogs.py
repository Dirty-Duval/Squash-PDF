"""
Shared, theme-consistent dialogs for Squash.

Every dialog in the application goes through this module so that errors,
confirmations and notices look the same everywhere and behave the same way
(centered on their parent, modal, Escape/Return bound, grab restored to the
parent dialog when they close).
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

import customtkinter as ctk

from ._icon import apply_icon

logger = logging.getLogger(__name__)

# (light, dark) colours per dialog kind; brand orange for info to match the theme.
_KIND_STYLE = {
    "info": ("ℹ", ("#C86B00", "#E07B10")),
    "success": ("✓", ("#43A047", "#50C878")),
    "warning": ("⚠", ("#E08A00", "#FFA500")),
    "error": ("✕", ("#C62828", "#E74C3C")),
    "question": ("?", ("#C86B00", "#E07B10")),
}


def center_on_parent(window: ctk.CTkToplevel, parent=None) -> None:
    """Position ``window`` over the centre of ``parent`` (or the screen).

    Works before the window has been mapped by falling back to its requested
    size. Never places the window off-screen.
    """
    window.update_idletasks()
    parent = parent if parent is not None else window.master

    width = window.winfo_width()
    height = window.winfo_height()
    if width <= 1 or height <= 1:
        width, height = window.winfo_reqwidth(), window.winfo_reqheight()

    try:
        if parent is not None and parent.winfo_exists() and parent.winfo_viewable():
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
        else:
            raise RuntimeError("parent not viewable")
    except Exception:
        px, py = 0, 0
        pw, ph = window.winfo_screenwidth(), window.winfo_screenheight()

    x = max(0, px + (pw - width) // 2)
    y = max(0, py + (ph - height) // 2)
    window.geometry(f"+{x}+{y}")


def fit_to_content(
    window,
    min_width: int = 0,
    min_height: int = 0,
    parent=None,
    margin: int = 60,
    grow_only: bool = False,
) -> tuple[int, int]:
    """Resize ``window`` so every widget is visible without scrolling.

    The requested size of the widget tree is measured after layout, clamped to
    the screen (leaving ``margin`` pixels for taskbar and decorations), and
    applied. With ``grow_only`` the window is never made smaller than it is.

    Args:
        window: A CTk or CTkToplevel window whose children are already gridded/packed.
        min_width: Lower bound for the width.
        min_height: Lower bound for the height.
        parent: If given, the window is re-centred over this parent afterwards.
        margin: Screen pixels to keep free in each dimension.
        grow_only: Only enlarge, never shrink.

    Returns:
        The (width, height) that was applied.
    """
    window.update_idletasks()
    req_w = max(window.winfo_reqwidth(), min_width)
    req_h = max(window.winfo_reqheight(), min_height)
    if grow_only:
        req_w = max(req_w, window.winfo_width())
        req_h = max(req_h, window.winfo_height())
    max_w = max(320, window.winfo_screenwidth() - margin)
    max_h = max(240, window.winfo_screenheight() - margin)
    width, height = min(req_w, max_w), min(req_h, max_h)
    window.geometry(f"{width}x{height}")
    if parent is not None:
        center_on_parent(window, parent)
    return width, height


class MessageDialog(ctk.CTkToplevel):
    """Modal message box with themed styling.

    Example:
        >>> choice = MessageDialog(parent, "Delete?", "Really delete?", "question",
        ...                        buttons=("Cancel", "Delete"), danger_index=1).show()
        >>> if choice == "Delete": ...
    """

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        kind: str = "info",
        buttons: Sequence[str] = ("OK",),
        default_index: int = -1,
        cancel_index: Optional[int] = None,
        danger_index: Optional[int] = None,
        width: int = 440,
    ):
        """
        Args:
            parent: Owning window.
            title: Window title.
            message: Body text (wrapped automatically).
            kind: ``info`` / ``success`` / ``warning`` / ``error`` / ``question``.
            buttons: Button captions, left to right.
            default_index: Button triggered by Return (negative counts from the end).
            cancel_index: Button triggered by Escape / closing the window. Defaults to
                the first button when there are several, otherwise the only button.
            danger_index: Button drawn in red (destructive action).
            width: Dialog width in pixels.
        """
        super().__init__(parent)
        self.result: Optional[str] = None
        self._buttons = list(buttons) or ["OK"]
        self._default = self._buttons[default_index]
        if cancel_index is None:
            cancel_index = 0 if len(self._buttons) > 1 else 0
        self._cancel = self._buttons[cancel_index]
        self._previous_grab = None

        self.title(title)
        self.resizable(False, False)
        # A transient of a withdrawn window is itself withdrawn on Windows, so only
        # attach to the parent when it is actually on screen (startup errors are
        # shown before the main window is mapped).
        try:
            if parent is not None and parent.winfo_viewable():
                self.transient(parent)
        except Exception:
            pass
        self.attributes("-topmost", True)
        self.after(200, lambda: self.winfo_exists() and self.attributes("-topmost", False))
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose(self._cancel))

        icon, colour = _KIND_STYLE.get(kind, _KIND_STYLE["info"])

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            body,
            text=icon,
            width=44,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=colour,
        ).grid(row=0, column=0, padx=(0, 14), sticky="n")

        ctk.CTkLabel(
            body,
            text=message,
            wraplength=width - 110,
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=1, sticky="w")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.grid(row=1, column=0, padx=20, pady=(6, 18), sticky="e")

        for index, caption in reversed(list(enumerate(self._buttons))):
            is_primary = caption == self._default
            is_danger = danger_index is not None and index == danger_index
            kwargs = {}
            if is_danger:
                kwargs = {"fg_color": ("#C62828", "#B71C1C"), "hover_color": ("#B71C1C", "#8E1414")}
            elif not is_primary:
                kwargs = {
                    "fg_color": "transparent",
                    "border_width": 1,
                    "text_color": ("#1A1208", "#F0E8DC"),
                }
            button = ctk.CTkButton(
                button_row,
                text=caption,
                width=max(90, 10 * len(caption) + 30),
                command=lambda c=caption: self._choose(c),
                **kwargs,
            )
            button.pack(side="right", padx=(8, 0))
            if is_primary:
                self._primary_button = button

        self.bind("<Return>", lambda _e: self._choose(self._default))
        self.bind("<Escape>", lambda _e: self._choose(self._cancel))

        apply_icon(self)
        self.update_idletasks()
        center_on_parent(self, parent)

    def _choose(self, value: str) -> None:
        if self.result is not None:
            return
        self.result = value
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def show(self) -> Optional[str]:
        """Display modally and return the caption of the chosen button."""
        try:
            self._previous_grab = self.grab_current()
        except Exception:
            self._previous_grab = None
        try:
            self.grab_set()
        except Exception as exc:  # window may have been destroyed by caller already
            logger.debug(f"grab_set failed: {exc}")
        self.focus_force()
        try:
            self._primary_button.focus_set()
        except Exception:
            pass
        self.wait_window(self)

        # Return the modal grab to the dialog that had it (e.g. Settings).
        previous = self._previous_grab
        if previous is not None:
            try:
                if previous.winfo_exists():
                    previous.grab_set()
            except Exception:
                pass
        return self.result


def show_info(parent, title: str, message: str) -> None:
    """Show an informational message and wait for OK."""
    MessageDialog(parent, title, message, "info").show()


def show_success(parent, title: str, message: str) -> None:
    """Show a success message and wait for OK."""
    MessageDialog(parent, title, message, "success").show()


def show_warning(parent, title: str, message: str) -> None:
    """Show a warning message and wait for OK."""
    MessageDialog(parent, title, message, "warning").show()


def show_error(parent, title: str, message: str) -> None:
    """Show an error message and wait for OK."""
    MessageDialog(parent, title, message, "error").show()


def ask_yes_no(
    parent,
    title: str,
    message: str,
    yes_text: str = "Yes",
    no_text: str = "No",
    danger: bool = False,
) -> bool:
    """Ask a yes/no question.

    Args:
        danger: Draw the affirmative button in red and make "No" the default,
            for destructive actions such as deleting or clearing.

    Returns:
        True if the affirmative button was chosen.
    """
    dialog = MessageDialog(
        parent,
        title,
        message,
        "question" if not danger else "warning",
        buttons=(no_text, yes_text),
        default_index=0 if danger else 1,
        cancel_index=0,
        danger_index=1 if danger else None,
    )
    return dialog.show() == yes_text
