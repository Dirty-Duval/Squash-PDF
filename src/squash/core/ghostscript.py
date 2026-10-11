"""
Ghostscript wrapper for PDF compression.

Runs the Ghostscript ``pdfwrite`` device as a subprocess and turns its
console output into structured progress and error information:

* ``Processing pages 1 through N.`` and ``Page N`` lines drive a per-file
  progress callback.
* Known failure texts (password-protected input, damaged files, permission
  and disk errors) are mapped to short, user-readable messages.
* Output is written to a temporary ``.part`` file next to the destination and
  only moved into place once Ghostscript finishes successfully, so a failed or
  cancelled run never leaves a half-written PDF behind.
"""

from __future__ import annotations

import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Signature: callback(current_page, total_pages). total_pages may be 0 if unknown.
ProgressCallback = Callable[[int, int], None]

_PAGES_TOTAL_RE = re.compile(r"Processing pages \d+ through (\d+)\.")
_PAGE_RE = re.compile(r"^Page (\d+)\s*$")

# Ghostscript exits with status 0 for some fatal conditions (notably encrypted
# input), so the output text has to be inspected as well as the return code.
_FATAL_TEXT_MARKERS = ("requires a password", "unrecoverable error", "couldn't initialise file")

# Order matters: the first matching pattern wins.
_ERROR_PATTERNS: Tuple[Tuple[Tuple[str, ...], str, str], ...] = (
    (
        ("requires a password",),
        "password",
        "This PDF is password-protected. Remove the password and try again.",
    ),
    (
        ("/invalidfileaccess", "permission denied"),
        "permission",
        "Squash does not have permission to read the input or write the output file.",
    ),
    (
        ("/ioerror", "no space left"),
        "disk",
        "A disk error occurred while writing the output. Check free space and that the "
        "folder is writable.",
    ),
    (
        (
            "couldn't initialise file",
            "no pdf header",
            "not a pdf",
            "syntaxerror",
            "stackunderflow",
            "unrecoverable error",
            "undefined in",
            "rangecheck",
            "typecheck",
            "xref",
            "file is damaged",
        ),
        "corrupt",
        "The file could not be read. It may be damaged or not a valid PDF.",
    ),
)


class GhostscriptError(Exception):
    """Raised when a Ghostscript run fails, is cancelled, or times out.

    Attributes:
        code: Short machine-readable category (``password``, ``corrupt``,
            ``permission``, ``disk``, ``timeout``, ``cancelled``, ``no_output``,
            ``launch``, ``unknown``).
        message: User-readable explanation suitable for a dialog.
        detail: Raw Ghostscript output excerpt for the log.
    """

    def __init__(self, code: str, message: str, detail: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def parse_progress_line(line: str) -> Optional[Tuple[str, int]]:
    """Interpret one line of Ghostscript console output.

    Args:
        line: A single output line (trailing newline optional).

    Returns:
        ``("total", n)`` for the page-count announcement, ``("page", n)`` for a
        page-start marker, or None for anything else.
    """
    text = line.strip()
    match = _PAGES_TOTAL_RE.search(text)
    if match:
        return "total", int(match.group(1))
    match = _PAGE_RE.match(text)
    if match:
        return "page", int(match.group(1))
    return None


def classify_error(output: str, returncode: Optional[int]) -> Tuple[str, str, str]:
    """Map Ghostscript output to an error category and user message.

    Args:
        output: Combined stdout/stderr text from the Ghostscript run.
        returncode: Process exit status (None if it was killed).

    Returns:
        Tuple of (code, user_message, detail_for_log).
    """
    lowered = output.lower()
    detail_lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    error_lines = [ln for ln in detail_lines if "error" in ln.lower()]
    detail = (error_lines or detail_lines or [""])[-1][:300]

    for markers, code, message in _ERROR_PATTERNS:
        if any(marker in lowered for marker in markers):
            return code, message, detail

    status = "an unknown status" if returncode is None else f"exit code {returncode}"
    message = f"Ghostscript could not process this file ({status})."
    if detail:
        message += f" Details: {detail}"
    return "unknown", message, detail


def escape_output_path(path: Path) -> str:
    """Escape a path for ``-sOutputFile``.

    Ghostscript treats ``%`` in the output filename as a printf-style format
    directive (for per-page output), so a literal percent sign must be doubled.
    """
    return str(path).replace("%", "%%")


def detect_ghostscript() -> Optional[Path]:
    """Locate a Ghostscript executable.

    Search order:
        1. Bundled copy shipped with the frozen application (``_internal/ghostscript``).
        2. Bundled copy in the source tree (``<repo>/ghostscript/bin``).
        3. Anything on the system PATH (``gswin64c``, ``gswin32c``, ``gs``).

    Returns:
        Path to the executable, or None if nothing was found.
    """
    candidates: List[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / "_internal" / "ghostscript" / "bin" / "gswin64c.exe")
        candidates.append(exe_dir / "ghostscript" / "bin" / "gswin64c.exe")
    else:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        candidates.append(repo_root / "ghostscript" / "bin" / "gswin64c.exe")

    for candidate in candidates:
        if candidate.exists():
            logger.info(f"Using bundled Ghostscript: {candidate}")
            return candidate

    for name in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(name)
        if found:
            logger.info(f"Using system Ghostscript: {found}")
            return Path(found)

    return None


class GhostscriptWrapper:
    """Thin, well-behaved wrapper around the Ghostscript executable."""

    # PDF 1.5 (Acrobat 6, 2003) enables object streams, which shave a few percent
    # off most files; every reader in use today supports it.
    DEFAULT_COMPATIBILITY_LEVEL = "1.5"

    def __init__(self, gs_path: Optional[Path] = None):
        """Initialize the wrapper.

        Args:
            gs_path: Explicit executable path (for example from user settings).
                If it does not exist, auto-detection is used instead.

        Raises:
            RuntimeError: If no Ghostscript executable could be found.
        """
        resolved: Optional[Path] = None
        if gs_path is not None:
            gs_path = Path(gs_path)
            if gs_path.is_file():
                resolved = gs_path
            else:
                logger.warning(
                    "Configured Ghostscript path does not exist, falling back to "
                    f"auto-detect: {gs_path}"
                )
        if resolved is None:
            resolved = detect_ghostscript()
        if resolved is None:
            raise RuntimeError(
                "Ghostscript not found. Please reinstall Squash or point Settings at a "
                "Ghostscript executable."
            )
        self.gs_path: Path = resolved
        logger.info(f"Using Ghostscript: {self.gs_path}")

    # ------------------------------------------------------------------ #
    # Command construction                                                 #
    # ------------------------------------------------------------------ #

    def build_command(
        self, input_path: Path, output_path: Path, params: Dict[str, Any]
    ) -> List[str]:
        """Build the Ghostscript argument list.

        Args:
            input_path: Source PDF.
            output_path: Destination path (may be a temporary file).
            params: Ghostscript ``-d`` parameters. Booleans become ``-dKey`` /
                ``-dKey=false``; everything else becomes ``-dKey=value``.

        Returns:
            Argument list suitable for ``subprocess``.
        """
        compat = params.get("CompatibilityLevel", self.DEFAULT_COMPATIBILITY_LEVEL)
        cmd = [
            str(self.gs_path),
            "-sDEVICE=pdfwrite",
            f"-dCompatibilityLevel={compat}",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
        ]
        for key, value in params.items():
            if key == "CompatibilityLevel":
                continue
            if isinstance(value, bool):
                cmd.append(f"-d{key}" if value else f"-d{key}=false")
            else:
                cmd.append(f"-d{key}={value}")
        cmd.append(f"-sOutputFile={escape_output_path(output_path)}")
        cmd.append(str(input_path))
        return cmd

    # ------------------------------------------------------------------ #
    # Execution                                                            #
    # ------------------------------------------------------------------ #

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        params: Dict[str, Any],
        timeout: int = 300,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> None:
        """Compress ``input_path`` into ``output_path``.

        Args:
            input_path: Source PDF.
            output_path: Final destination. Written atomically on success.
            params: Ghostscript parameters (see :meth:`build_command`).
            timeout: Maximum wall-clock seconds before the run is killed.
            progress_callback: Optional ``callback(page, total_pages)``.
            cancel_event: Optional event; when set, Ghostscript is killed.

        Raises:
            GhostscriptError: On failure, timeout or cancellation. The partial
                output file is removed before raising.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Short temporary name: Ghostscript cannot open paths longer than 260
        # characters on Windows, and long user file names plus a suffix get there.
        temp_output = output_path.with_name(f".squash-{uuid.uuid4().hex[:8]}.part")
        cmd = self.build_command(input_path, temp_output, params)
        logger.debug("Running Ghostscript: %s", subprocess.list2cmdline(cmd))

        popen_kwargs: Dict[str, Any] = {}
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_kwargs["startupinfo"] = startupinfo
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        lines: List[str] = []
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                **popen_kwargs,
            )
        except OSError as exc:
            self._remove_quietly(temp_output)
            raise GhostscriptError(
                "launch",
                f"Could not start Ghostscript ({self.gs_path.name}): {exc}",
                str(exc),
            ) from exc

        try:
            returncode = self._pump_output(proc, lines, timeout, progress_callback, cancel_event)
        except GhostscriptError:
            self._remove_quietly(temp_output)
            raise

        output_text = "\n".join(lines)
        lowered = output_text.lower()
        fatal_text = any(marker in lowered for marker in _FATAL_TEXT_MARKERS)
        produced = temp_output.exists() and temp_output.stat().st_size > 0

        if returncode != 0 or fatal_text or not produced:
            self._remove_quietly(temp_output)
            if returncode == 0 and not fatal_text and not produced:
                code, message, detail = (
                    "no_output",
                    "Ghostscript finished but produced no output file.",
                    "",
                )
            else:
                code, message, detail = classify_error(output_text, returncode)
            logger.error(f"Ghostscript failed for {input_path.name} [{code}]: {detail or message}")
            raise GhostscriptError(code, message, detail)

        if not self.validate_pdf(temp_output):
            self._remove_quietly(temp_output)
            raise GhostscriptError("corrupt", "Ghostscript produced an unreadable output file.", "")

        os.replace(temp_output, output_path)
        logger.info(f"Compressed {input_path} -> {output_path}")

    def _pump_output(
        self,
        proc: subprocess.Popen,
        lines: List[str],
        timeout: int,
        progress_callback: Optional[ProgressCallback],
        cancel_event: Optional[threading.Event],
    ) -> int:
        """Read process output while watching for timeout and cancellation.

        Returns:
            The process exit code.

        Raises:
            GhostscriptError: ``timeout`` or ``cancelled``.
        """
        line_queue: "queue.Queue[Optional[str]]" = queue.Queue()

        def _reader() -> None:
            try:
                assert proc.stdout is not None
                for raw in proc.stdout:
                    line_queue.put(raw)
            finally:
                line_queue.put(None)

        threading.Thread(target=_reader, name="gs-reader", daemon=True).start()

        deadline = time.monotonic() + max(1, timeout)
        total_pages = 0
        finished = False

        while not finished:
            try:
                item = line_queue.get(timeout=0.1)
            except queue.Empty:
                item = ""
            else:
                if item is None:
                    finished = True
                    continue
                line = item.rstrip("\r\n")
                lines.append(line)
                parsed = parse_progress_line(line)
                if parsed and progress_callback:
                    kind, value = parsed
                    if kind == "total":
                        total_pages = value
                    else:
                        try:
                            progress_callback(value, total_pages)
                        except Exception:  # UI callbacks must never kill the run
                            logger.exception("Progress callback raised")

            if cancel_event is not None and cancel_event.is_set():
                self._kill(proc)
                logger.info("Ghostscript run cancelled by user")
                raise GhostscriptError("cancelled", "Compression was cancelled.", "")

            if time.monotonic() > deadline:
                self._kill(proc)
                logger.error(f"Ghostscript timed out after {timeout}s")
                raise GhostscriptError(
                    "timeout",
                    f"Compression took longer than {timeout} seconds and was stopped. "
                    "You can raise the limit in Settings.",
                    "",
                )

        try:
            return proc.wait(timeout=max(1.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            self._kill(proc)
            raise GhostscriptError(
                "timeout",
                f"Compression took longer than {timeout} seconds and was stopped.",
                "",
            )

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:  # best effort
            pass

    @staticmethod
    def _remove_quietly(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:  # best effort cleanup
            logger.debug(f"Could not remove temp file {path}: {exc}")

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_pdf(path: Path) -> bool:
        """Cheap structural check: does the file start like a PDF?

        The PDF specification allows up to 1024 bytes of junk before the
        ``%PDF`` header, so the first kilobyte is searched rather than only
        the first four bytes.
        """
        try:
            path = Path(path)
            if not path.is_file():
                return False
            with open(path, "rb") as fh:
                return b"%PDF" in fh.read(1024)
        except OSError as exc:
            logger.error(f"Error validating PDF {path}: {exc}")
            return False

    def get_version(self) -> Optional[str]:
        """Return the Ghostscript version string, or None if it cannot be read."""
        try:
            kwargs: Dict[str, Any] = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                [str(self.gs_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                **kwargs,
            )
            return result.stdout.strip() or None
        except Exception as exc:
            logger.error(f"Error getting Ghostscript version: {exc}")
            return None
