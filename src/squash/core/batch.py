"""
Batch processing for multiple PDF files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional
import logging
import time

from .compression import CompressionEngine, CompressionResult

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of batch PDF compression."""

    total_files: int
    successful: int
    failed: int
    total_size_before: int  # bytes
    total_size_after: int  # bytes
    total_reduction_percent: float
    duration: float  # seconds
    file_results: List[CompressionResult]

    def get_summary(self) -> str:
        """Get human-readable summary."""
        before_mb = self.total_size_before / (1024 * 1024)
        after_mb = self.total_size_after / (1024 * 1024)
        saved_mb = (self.total_size_before - self.total_size_after) / (1024 * 1024)

        return (
            f"Processed {self.total_files} files:\n"
            f"✓ Successful: {self.successful}\n"
            f"✗ Failed: {self.failed}\n"
            f"Size: {before_mb:.1f} MB → {after_mb:.1f} MB\n"
            f"Saved: {saved_mb:.1f} MB ({self.total_reduction_percent:.1f}%)\n"
            f"Duration: {self.duration:.1f}s"
        )


class MetricsCalculator:
    """Calculates real-time compression metrics for progress tracking."""

    def __init__(self, total_bytes: int):
        """Initialize metrics tracker.

        Args:
            total_bytes: Total bytes to process in batch
        """
        self.total_bytes = total_bytes
        self.start_time = time.time()
        self.bytes_processed = 0

    def update(self, bytes_completed: int) -> Dict[str, float]:
        """Update metrics with newly processed bytes.

        Args:
            bytes_completed: Bytes processed in latest file

        Returns:
            Dictionary with speed_mbps and eta_seconds
        """
        self.bytes_processed += bytes_completed
        elapsed_time = time.time() - self.start_time

        # Calculate speed (MB/s)
        if elapsed_time > 0:
            bytes_per_second = self.bytes_processed / elapsed_time
            speed_mbps = bytes_per_second / (1024 * 1024)
        else:
            speed_mbps = 0.0

        # Calculate ETA
        bytes_remaining = self.total_bytes - self.bytes_processed
        if speed_mbps > 0:
            eta_seconds = bytes_remaining / (speed_mbps * 1024 * 1024)
        else:
            eta_seconds = 0.0

        return {
            "speed_mbps": max(0.0, speed_mbps),
            "eta_seconds": max(0.0, eta_seconds),
        }


class BatchProcessor:
    """Handles batch processing of multiple PDF files."""

    def __init__(self, engine: Optional[CompressionEngine] = None):
        """
        Initialize batch processor.

        Args:
            engine: CompressionEngine instance. If None, creates new one.
        """
        self.engine = engine or CompressionEngine()
        logger.info("BatchProcessor initialized")

    def process_batch(
        self,
        input_paths: List[Path],
        preset: str = "medium",
        recursive: bool = False,
        progress_callback: Optional[
            Callable[[int, int, str, float, float, Dict[str, float]], None]
        ] = None,
    ) -> BatchResult:
        """
        Process multiple PDFs with enhanced progress tracking.

        Args:
            input_paths: List of file/folder paths
            preset: Quality preset name
            recursive: Process folders recursively
            progress_callback: Optional callback with signature:
                callback(current, total, filename, file_progress,
                         overall_progress, metrics)

        Returns:
            BatchResult with operation details
        """
        start_time = time.time()

        # Collect all PDF files
        pdf_files = self._collect_pdf_files(input_paths, recursive)
        total_files = len(pdf_files)

        logger.info(f"Processing {total_files} PDF files with preset '{preset}'")

        # Calculate total bytes for metrics
        total_bytes = sum(f.stat().st_size for f in pdf_files if f.exists())
        metrics_tracker = MetricsCalculator(total_bytes)

        # Process each file
        results: List[CompressionResult] = []
        successful = 0
        failed = 0
        total_size_before = 0
        total_size_after = 0

        for idx, pdf_path in enumerate(pdf_files, 1):
            # Progress callback with metrics (start of file)
            overall_progress = (idx - 1) / total_files if total_files > 0 else 0
            if progress_callback:
                metrics = metrics_tracker.update(0)
                progress_callback(
                    idx,
                    total_files,
                    pdf_path.name,
                    0.0,  # file_progress
                    overall_progress,
                    metrics,
                )

            # Compress file
            result = self.engine.compress(pdf_path, preset=preset)
            results.append(result)

            # Update metrics with processed bytes
            bytes_compressed = result.original_size
            metrics = metrics_tracker.update(bytes_compressed)

            # Update statistics
            total_size_before += result.original_size

            if result.success:
                successful += 1
                if result.compressed_size:
                    total_size_after += result.compressed_size
            else:
                failed += 1
                total_size_after += result.original_size  # No compression
                logger.warning(
                    f"Failed to compress {pdf_path.name}: {result.error_message}"
                )

            # Progress callback (end of file)
            overall_progress = idx / total_files if total_files > 0 else 1.0
            if progress_callback:
                progress_callback(
                    idx,
                    total_files,
                    pdf_path.name,
                    1.0,  # file_progress (complete)
                    overall_progress,
                    metrics,
                )

        # Calculate total reduction
        if total_size_before > 0:
            total_reduction_percent = (
                (total_size_before - total_size_after) / total_size_before
            ) * 100
        else:
            total_reduction_percent = 0.0

        duration = time.time() - start_time

        batch_result = BatchResult(
            total_files=total_files,
            successful=successful,
            failed=failed,
            total_size_before=total_size_before,
            total_size_after=total_size_after,
            total_reduction_percent=total_reduction_percent,
            duration=duration,
            file_results=results,
        )

        logger.info(f"Batch complete: {successful} success, {failed} failed")
        return batch_result

    def _collect_pdf_files(
        self, input_paths: List[Path], recursive: bool
    ) -> List[Path]:
        """
        Collect all PDF files from input paths.

        Args:
            input_paths: List of file/folder paths
            recursive: Search folders recursively

        Returns:
            List of PDF file paths
        """
        pdf_files: List[Path] = []

        for path in input_paths:
            if path.is_file():
                if path.suffix.lower() == ".pdf":
                    pdf_files.append(path)
                else:
                    logger.warning(f"Skipping non-PDF file: {path}")

            elif path.is_dir():
                pattern = "**/*.pdf" if recursive else "*.pdf"
                folder_pdfs = list(path.glob(pattern))
                pdf_files.extend(folder_pdfs)
                logger.debug(f"Found {len(folder_pdfs)} PDFs in {path}")

            else:
                logger.warning(f"Path not found: {path}")

        return sorted(pdf_files)
