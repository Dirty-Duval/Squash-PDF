"""
Core PDF compression engine.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils.filesystem import FileSystemHelper
from .ghostscript import GhostscriptError, GhostscriptWrapper, ProgressCallback
from .presets import PresetManager

logger = logging.getLogger(__name__)

# Error codes surfaced in CompressionResult.error_code
ERROR_INPUT_NOT_FOUND = "E001"
ERROR_INVALID_PDF = "E002"
ERROR_INVALID_PRESET = "E003"
ERROR_GHOSTSCRIPT = "E004"
ERROR_UNEXPECTED = "E005"
ERROR_CANCELLED = "E006"
ERROR_TIMEOUT = "E007"
ERROR_OUTPUT_IS_INPUT = "E008"

_GS_CODE_MAP = {
    "cancelled": ERROR_CANCELLED,
    "timeout": ERROR_TIMEOUT,
}


@dataclass
class CompressionResult:
    """Result of a single PDF compression operation."""

    success: bool
    input_path: str
    output_path: Optional[str]
    original_size: int  # bytes
    compressed_size: Optional[int]
    reduction_percent: Optional[float]
    duration: float  # seconds
    preset_used: str
    timestamp: datetime
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    size_increased: bool = False  # True when output is larger than input
    output_discarded: bool = False  # larger output deleted, original kept
    note: Optional[str] = None  # extra human-readable detail for the UI

    @property
    def cancelled(self) -> bool:
        """True when the operation was stopped by the user."""
        return self.error_code == ERROR_CANCELLED

    def get_size_reduction_mb(self) -> Optional[float]:
        """Get size reduction in megabytes (negative if the file grew)."""
        if self.compressed_size is not None:
            return (self.original_size - self.compressed_size) / (1024 * 1024)
        return None

    def format_sizes(self) -> str:
        """Format original and compressed sizes for display."""
        original = FileSystemHelper.format_size(self.original_size)
        if self.compressed_size is not None:
            return f"{original} → {FileSystemHelper.format_size(self.compressed_size)}"
        return original


class CompressionEngine:
    """Compresses single PDF files via Ghostscript using named presets."""

    def __init__(
        self,
        ghostscript_path: Optional[Path] = None,
        preset_manager: Optional[PresetManager] = None,
    ):
        """Initialize the engine.

        Args:
            ghostscript_path: Custom Ghostscript executable. If None (or the
                path is invalid) the bundled/system copy is auto-detected.
            preset_manager: Shared PresetManager. A new one is created if omitted.

        Raises:
            RuntimeError: If Ghostscript cannot be found.
        """
        self.gs = GhostscriptWrapper(ghostscript_path)
        self.preset_manager = preset_manager or PresetManager()
        logger.info("CompressionEngine initialized")

    def compress(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        preset: str = "medium",
        timeout: int = 300,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
        keep_larger: bool = False,
    ) -> CompressionResult:
        """Compress one PDF.

        Args:
            input_path: Source PDF.
            output_path: Destination. If None, ``<name>_compressed.pdf`` next to
                the input (made unique if it already exists).
            preset: Preset name (built-in or custom).
            timeout: Maximum seconds for the Ghostscript run.
            progress_callback: Optional ``callback(page, total_pages)``.
            cancel_event: Optional event that aborts the run when set.
            keep_larger: Keep the output even if it is larger than the input.
                By default a larger output is deleted, the result is still a
                success with ``output_discarded=True`` and the original is kept.

        Returns:
            CompressionResult describing success or the failure reason. This
            method does not raise for per-file problems.
        """
        start = time.perf_counter()
        timestamp = datetime.now()
        input_path = Path(input_path)

        def _failure(
            code: str, message: str, original_size: int = 0, output: Optional[Path] = None
        ) -> CompressionResult:
            return CompressionResult(
                success=False,
                input_path=str(input_path),
                output_path=str(output) if output else None,
                original_size=original_size,
                compressed_size=None,
                reduction_percent=None,
                duration=time.perf_counter() - start,
                preset_used=preset,
                timestamp=timestamp,
                error_code=code,
                error_message=message,
            )

        if not input_path.is_file():
            return _failure(ERROR_INPUT_NOT_FOUND, f"Input file not found: {input_path}")

        original_size = input_path.stat().st_size

        if not self.gs.validate_pdf(input_path):
            return _failure(
                ERROR_INVALID_PDF, "Invalid PDF file or corrupted structure", original_size
            )

        if output_path is None:
            candidate = input_path.parent / f"{input_path.stem}_compressed.pdf"
            output_path = FileSystemHelper.get_unique_filename(candidate)
        output_path = Path(output_path)

        try:
            if output_path.exists() and output_path.resolve() == input_path.resolve():
                return _failure(
                    ERROR_OUTPUT_IS_INPUT,
                    "Output path is the same as the input file; refusing to overwrite "
                    "the original.",
                    original_size,
                )
        except OSError:
            pass

        try:
            gs_params = self.preset_manager.get_preset(preset).to_ghostscript_params()
        except KeyError as exc:
            return _failure(ERROR_INVALID_PRESET, f"Invalid preset: {exc}", original_size)

        try:
            self.gs.compress(
                input_path,
                output_path,
                gs_params,
                timeout=timeout,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
        except GhostscriptError as exc:
            code = _GS_CODE_MAP.get(exc.code, ERROR_GHOSTSCRIPT)
            if code == ERROR_CANCELLED:
                logger.info(f"Compression cancelled: {input_path.name}")
            else:
                logger.error(f"Compression failed for {input_path.name}: {exc.message}")
            return _failure(code, exc.message, original_size)
        except Exception as exc:  # defensive: never let one file kill a batch
            logger.exception(f"Unexpected compression error for {input_path}")
            return _failure(ERROR_UNEXPECTED, f"Unexpected error: {exc}", original_size)

        try:
            compressed_size = output_path.stat().st_size
        except OSError as exc:
            return _failure(
                ERROR_UNEXPECTED, f"Output file missing after compression: {exc}", original_size
            )

        reduction_percent = (
            ((original_size - compressed_size) / original_size) * 100 if original_size else 0.0
        )
        size_increased = compressed_size > original_size

        sizes = (
            f"{FileSystemHelper.format_size(original_size)} → "
            f"{FileSystemHelper.format_size(compressed_size)}"
        )
        if size_increased and not keep_larger:
            # Ghostscript re-encodes everything; a PDF that already uses tighter
            # encodings (JBIG2 scans, optimised JPEGs, object streams) comes out
            # bigger. Nobody wants a "_compressed" file that is larger, so keep
            # the original and say so.
            grew_by = compressed_size - original_size
            try:
                output_path.unlink()
            except OSError as exc:
                logger.warning(f"Could not remove larger output {output_path}: {exc}")
            logger.info(
                f"Already optimised, original kept for {input_path.name}: output would have "
                f"been {sizes} (+{-reduction_percent:.0f}%)"
            )
            return CompressionResult(
                success=True,
                input_path=str(input_path),
                output_path=None,
                original_size=original_size,
                compressed_size=original_size,
                reduction_percent=0.0,
                duration=time.perf_counter() - start,
                preset_used=preset,
                timestamp=timestamp,
                size_increased=True,
                output_discarded=True,
                note=(
                    "Already optimised. Compressing would have made it "
                    f"{FileSystemHelper.format_size(grew_by)} larger "
                    f"({FileSystemHelper.format_size(compressed_size)}), so the original was kept."
                ),
            )

        if size_increased:
            logger.warning(
                f"Output larger than input for {input_path.name}: {sizes} "
                "(PDF may already be optimised; kept because keep_larger=True)"
            )
        else:
            logger.info(
                f"Compressed {input_path.name}: {sizes} ({reduction_percent:.1f}% reduction)"
            )

        return CompressionResult(
            success=True,
            input_path=str(input_path),
            output_path=str(output_path),
            original_size=original_size,
            compressed_size=compressed_size,
            reduction_percent=reduction_percent,
            duration=time.perf_counter() - start,
            preset_used=preset,
            timestamp=timestamp,
            size_increased=size_increased,
        )

    def validate_pdf(self, path: Path) -> bool:
        """Check whether ``path`` looks like a PDF."""
        return self.gs.validate_pdf(path)
