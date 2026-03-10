"""
Core PDF compression engine.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime
import time
import logging

from .ghostscript import GhostscriptWrapper
from .presets import PresetManager
from ..utils.filesystem import FileSystemHelper

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """Result of a PDF compression operation."""

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

    def get_size_reduction_mb(self) -> Optional[float]:
        """Get size reduction in megabytes."""
        if self.compressed_size is not None:
            return (self.original_size - self.compressed_size) / (1024 * 1024)
        return None

    def format_sizes(self) -> str:
        """Format original and compressed sizes for display."""
        orig_mb = self.original_size / (1024 * 1024)
        if self.compressed_size is not None:
            comp_mb = self.compressed_size / (1024 * 1024)
            return f"{orig_mb:.1f} MB → {comp_mb:.1f} MB"
        return f"{orig_mb:.1f} MB"


class CompressionEngine:
    """
    Core PDF compression engine using Ghostscript.
    """

    def __init__(self, ghostscript_path: Optional[Path] = None):
        """
        Initialize compression engine.

        Args:
            ghostscript_path: Custom Ghostscript executable path.
                            If None, uses bundled version or system install.
        """
        self.gs = GhostscriptWrapper(ghostscript_path)
        self.preset_manager = PresetManager()
        logger.info("CompressionEngine initialized")

    def compress(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        preset: str = "medium",
        timeout: int = 300,
    ) -> CompressionResult:
        """
        Compress a PDF file.

        Args:
            input_path: Path to input PDF file
            output_path: Path for output file. If None, generates automatically.
            preset: Quality preset name (small/medium/high)
            timeout: Maximum compression time in seconds

        Returns:
            CompressionResult with operation details
        """
        start_time = time.time()
        timestamp = datetime.now()

        # Validate input
        if not input_path.exists():
            return CompressionResult(
                success=False,
                input_path=str(input_path),
                output_path=None,
                original_size=0,
                compressed_size=None,
                reduction_percent=None,
                duration=0,
                preset_used=preset,
                timestamp=timestamp,
                error_code="E001",
                error_message=f"Input file not found: {input_path}",
            )

        # Validate PDF
        if not self.gs.validate_pdf(input_path):
            return CompressionResult(
                success=False,
                input_path=str(input_path),
                output_path=None,
                original_size=input_path.stat().st_size,
                compressed_size=None,
                reduction_percent=None,
                duration=time.time() - start_time,
                preset_used=preset,
                timestamp=timestamp,
                error_code="E002",
                error_message="Invalid PDF file or corrupted structure",
            )

        # Get original file size
        original_size = input_path.stat().st_size

        # Generate output path if not provided
        if output_path is None:
            candidate = input_path.parent / f"{input_path.stem}_compressed.pdf"
            output_path = FileSystemHelper.get_unique_filename(candidate)

        # Get preset parameters
        try:
            preset_obj = self.preset_manager.get_preset(preset)
            gs_params = preset_obj.to_ghostscript_params()
        except KeyError as e:
            return CompressionResult(
                success=False,
                input_path=str(input_path),
                output_path=None,
                original_size=original_size,
                compressed_size=None,
                reduction_percent=None,
                duration=time.time() - start_time,
                preset_used=preset,
                timestamp=timestamp,
                error_code="E003",
                error_message=f"Invalid preset: {e}",
            )

        # Compress PDF
        try:
            success = self.gs.compress(input_path, output_path, gs_params, timeout)

            if not success:
                return CompressionResult(
                    success=False,
                    input_path=str(input_path),
                    output_path=str(output_path),
                    original_size=original_size,
                    compressed_size=None,
                    reduction_percent=None,
                    duration=time.time() - start_time,
                    preset_used=preset,
                    timestamp=timestamp,
                    error_code="E004",
                    error_message="Ghostscript compression failed",
                )

            # Get compressed file size
            compressed_size = output_path.stat().st_size
            reduction_percent = ((original_size - compressed_size) / original_size) * 100
            size_increased = compressed_size > original_size

            if size_increased:
                logger.warning(
                    f"Output larger than input for {input_path.name}: "
                    f"{original_size / (1024 * 1024):.1f} MB → "
                    f"{compressed_size / (1024 * 1024):.1f} MB "
                    f"(PDF may already be optimised)"
                )
            else:
                logger.info(
                    f"Compressed {input_path.name}: "
                    f"{original_size / (1024 * 1024):.1f} MB → "
                    f"{compressed_size / (1024 * 1024):.1f} MB "
                    f"({reduction_percent:.1f}% reduction)"
                )

            return CompressionResult(
                success=True,
                input_path=str(input_path),
                output_path=str(output_path),
                original_size=original_size,
                compressed_size=compressed_size,
                reduction_percent=reduction_percent,
                duration=time.time() - start_time,
                preset_used=preset,
                timestamp=timestamp,
                size_increased=size_increased,
            )

        except Exception as e:
            logger.error(f"Compression error for {input_path}: {e}")
            return CompressionResult(
                success=False,
                input_path=str(input_path),
                output_path=str(output_path) if output_path else None,
                original_size=original_size,
                compressed_size=None,
                reduction_percent=None,
                duration=time.time() - start_time,
                preset_used=preset,
                timestamp=timestamp,
                error_code="E005",
                error_message=f"Unexpected error: {str(e)}",
            )

    def validate_pdf(self, path: Path) -> bool:
        """
        Check if file is a valid PDF.

        Args:
            path: Path to file

        Returns:
            True if valid PDF, False otherwise
        """
        return self.gs.validate_pdf(path)
