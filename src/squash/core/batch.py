"""
Batch processing for multiple PDF files.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..utils.filesystem import FileSystemHelper
from .compression import CompressionEngine, CompressionResult

logger = logging.getLogger(__name__)

DEFAULT_NAMING_PATTERN = "{filename}_compressed.pdf"
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MB = 1024 * 1024


@dataclass
class BatchProgress:
    """Snapshot of batch progress passed to the progress callback.

    Attributes:
        index: 1-based index of the file currently being processed.
        total: Total number of files in the batch.
        path: The file currently being processed.
        file_progress: Progress of the current file (0.0-1.0).
        overall_progress: Byte-weighted progress of the whole batch (0.0-1.0).
        speed_mbps: Average throughput so far in MB/s.
        eta_seconds: Estimated remaining seconds (0 if unknown).
        detail: Short human-readable status, e.g. ``"page 3 of 12"``.
    """

    index: int
    total: int
    path: Path
    file_progress: float
    overall_progress: float
    speed_mbps: float
    eta_seconds: float
    detail: str = ""


ProgressCallback = Callable[[BatchProgress], None]
ResultCallback = Callable[[CompressionResult], None]


@dataclass
class BatchResult:
    """Result of batch PDF compression."""

    total_files: int
    successful: int
    failed: int
    total_size_before: int  # bytes (processed files only)
    total_size_after: int  # bytes (processed files only)
    total_reduction_percent: float
    duration: float  # seconds
    file_results: List[CompressionResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def processed(self) -> int:
        """Number of files that were actually attempted."""
        return len(self.file_results)

    @property
    def skipped(self) -> int:
        """Files never attempted because the batch was cancelled."""
        return max(0, self.total_files - self.processed)

    def get_summary(self) -> str:
        """Get human-readable summary."""
        saved = self.total_size_before - self.total_size_after
        lines = [
            f"Processed {self.processed} of {self.total_files} files:",
            f"Successful: {self.successful}",
            f"Failed: {self.failed}",
        ]
        if self.cancelled:
            lines.append(f"Cancelled (skipped {self.skipped})")
        lines += [
            f"Size: {FileSystemHelper.format_size(self.total_size_before)} → "
            f"{FileSystemHelper.format_size(self.total_size_after)}",
            f"Saved: {FileSystemHelper.format_size(saved)} ({self.total_reduction_percent:.1f}%)",
            f"Duration: {self.duration:.1f}s",
        ]
        return "\n".join(lines)


def resolve_output_path(
    input_path: Path,
    output_dir: Optional[Path] = None,
    naming_pattern: str = DEFAULT_NAMING_PATTERN,
) -> Path:
    """Compute where a compressed file should be written.

    Args:
        input_path: Source PDF.
        output_dir: Destination folder, or None to use the source folder.
        naming_pattern: Pattern containing ``{filename}`` (the source stem).
            Falls back to the default pattern if the placeholder is missing or
            the pattern is malformed.

    Returns:
        A path that does not yet exist (a numeric suffix is appended on
        collision), so the original file is never overwritten.
    """
    pattern = naming_pattern if "{filename}" in (naming_pattern or "") else DEFAULT_NAMING_PATTERN
    try:
        name = pattern.format(filename=input_path.stem)
    except (KeyError, IndexError, ValueError):
        name = DEFAULT_NAMING_PATTERN.format(filename=input_path.stem)

    name = _INVALID_FILENAME_CHARS.sub("_", name).strip().rstrip(".")
    if not name:
        name = DEFAULT_NAMING_PATTERN.format(filename=input_path.stem)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"

    directory = Path(output_dir) if output_dir else input_path.parent
    return FileSystemHelper.get_unique_filename(directory / name)


class BatchProcessor:
    """Compresses many PDFs sequentially with progress and cancellation."""

    def __init__(self, engine: Optional[CompressionEngine] = None):
        """
        Args:
            engine: CompressionEngine to use. Created on demand if None.
        """
        self.engine = engine or CompressionEngine()
        logger.info("BatchProcessor initialized")

    def collect_pdf_files(self, input_paths: List[Path], recursive: bool = False) -> List[Path]:
        """Expand files and folders into a de-duplicated, order-preserving PDF list.

        Args:
            input_paths: Files and/or folders.
            recursive: Descend into sub-folders.

        Returns:
            List of PDF paths in the order they were given (folder contents sorted).
        """
        seen: Dict[Path, None] = {}
        for path in input_paths:
            path = Path(path)
            if path.is_file():
                if path.suffix.lower() == ".pdf":
                    seen.setdefault(path, None)
                else:
                    logger.warning(f"Skipping non-PDF file: {path}")
            elif path.is_dir():
                pattern = "**/*.pdf" if recursive else "*.pdf"
                found = sorted(p for p in path.glob(pattern) if p.is_file())
                for p in found:
                    seen.setdefault(p, None)
                logger.debug(f"Found {len(found)} PDFs in {path}")
            else:
                logger.warning(f"Path not found: {path}")
        return list(seen)

    # Backwards-compatible alias
    _collect_pdf_files = collect_pdf_files

    def process_batch(
        self,
        input_paths: List[Path],
        preset: str = "medium",
        recursive: bool = False,
        output_dir: Optional[Path] = None,
        naming_pattern: str = DEFAULT_NAMING_PATTERN,
        timeout: int = 300,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
        result_callback: Optional[ResultCallback] = None,
        keep_larger: bool = False,
    ) -> BatchResult:
        """Compress every PDF in ``input_paths``.

        Args:
            input_paths: Files and/or folders.
            preset: Preset name.
            recursive: Search folders recursively.
            output_dir: Destination folder (created if missing). None = same folder.
            naming_pattern: Output naming pattern with ``{filename}``.
            timeout: Per-file Ghostscript timeout in seconds.
            progress_callback: Receives :class:`BatchProgress` snapshots.
            cancel_event: When set, stops after the current page and marks the
                batch cancelled.
            result_callback: Called with each file's :class:`CompressionResult`
                as soon as that file finishes (success, failure or cancellation).
            keep_larger: Keep outputs that are larger than their originals
                (default: delete them and keep the original).

        Returns:
            BatchResult. Per-file problems are reported inside it, not raised.

        Raises:
            OSError: If ``output_dir`` is given but cannot be created.
        """
        start = time.perf_counter()
        pdf_files = self.collect_pdf_files(input_paths, recursive)
        total_files = len(pdf_files)
        logger.info(f"Processing {total_files} PDF files with preset '{preset}'")

        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        sizes: Dict[Path, int] = {}
        for pdf in pdf_files:
            try:
                sizes[pdf] = pdf.stat().st_size
            except OSError:
                sizes[pdf] = 0
        total_bytes = sum(sizes.values())
        bytes_done = 0

        def _emit(index: int, path: Path, file_progress: float, detail: str) -> None:
            if progress_callback is None:
                return
            done = bytes_done + sizes.get(path, 0) * file_progress
            elapsed = time.perf_counter() - start
            speed = (done / _MB) / elapsed if elapsed > 0 else 0.0
            remaining = max(0.0, total_bytes - done)
            eta = remaining / (speed * _MB) if speed > 0 else 0.0
            if total_bytes > 0:
                overall = min(1.0, done / total_bytes)
            else:
                overall = (index - 1 + file_progress) / total_files if total_files else 1.0
            try:
                progress_callback(
                    BatchProgress(
                        index, total_files, path, file_progress, overall, speed, eta, detail
                    )
                )
            except Exception:  # UI must not break the batch
                logger.exception("Batch progress callback raised")

        results: List[CompressionResult] = []
        successful = failed = 0
        size_before = size_after = 0
        cancelled = False

        for index, pdf_path in enumerate(pdf_files, 1):
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break

            _emit(index, pdf_path, 0.0, "starting")
            destination = resolve_output_path(pdf_path, output_dir, naming_pattern)

            def _on_page(
                page: int, total_pages: int, _index: int = index, _path: Path = pdf_path
            ) -> None:
                fraction = min(1.0, page / total_pages) if total_pages > 0 else 0.0
                detail = f"page {page} of {total_pages}" if total_pages else f"page {page}"
                _emit(_index, _path, fraction, detail)

            result = self.engine.compress(
                pdf_path,
                output_path=destination,
                preset=preset,
                timeout=timeout,
                progress_callback=_on_page,
                cancel_event=cancel_event,
                keep_larger=keep_larger,
            )
            results.append(result)
            if result_callback is not None:
                try:
                    result_callback(result)
                except Exception:  # UI must not break the batch
                    logger.exception("Batch result callback raised")

            if result.cancelled:
                cancelled = True
                break

            bytes_done += sizes.get(pdf_path, 0)
            size_before += result.original_size
            if result.success and result.compressed_size is not None:
                successful += 1
                size_after += result.compressed_size
            else:
                failed += 1
                size_after += result.original_size  # nothing saved for this file
                logger.warning(f"Failed to compress {pdf_path.name}: {result.error_message}")

            _emit(index, pdf_path, 1.0, "done")

        reduction = ((size_before - size_after) / size_before * 100) if size_before > 0 else 0.0
        batch_result = BatchResult(
            total_files=total_files,
            successful=successful,
            failed=failed,
            total_size_before=size_before,
            total_size_after=size_after,
            total_reduction_percent=reduction,
            duration=time.perf_counter() - start,
            file_results=results,
            cancelled=cancelled,
        )
        logger.info(
            f"Batch complete: {successful} success, {failed} failed"
            + (", cancelled" if cancelled else "")
        )
        return batch_result
