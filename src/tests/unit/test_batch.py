"""
Unit tests for batch processing (engine is mocked; no Ghostscript required).
"""

import threading
from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from squash.core.batch import (
    DEFAULT_NAMING_PATTERN,
    BatchProcessor,
    BatchProgress,
    resolve_output_path,
)
from squash.core.compression import ERROR_CANCELLED, CompressionResult

# ---------------------------------------------------------------------------
# resolve_output_path
# ---------------------------------------------------------------------------


class TestResolveOutputPath:
    def test_default_same_folder(self, tmp_path):
        src = tmp_path / "report.pdf"
        src.write_bytes(b"%PDF")
        assert resolve_output_path(src) == tmp_path / "report_compressed.pdf"

    def test_custom_output_dir(self, tmp_path):
        src = tmp_path / "in" / "report.pdf"
        src.parent.mkdir()
        src.write_bytes(b"%PDF")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        assert resolve_output_path(src, out_dir) == out_dir / "report_compressed.pdf"

    def test_custom_pattern(self, tmp_path):
        src = tmp_path / "report.pdf"
        result = resolve_output_path(src, None, "small_{filename}.pdf")
        assert result == tmp_path / "small_report.pdf"

    def test_pattern_without_pdf_extension_gets_one(self, tmp_path):
        result = resolve_output_path(tmp_path / "report.pdf", None, "{filename}-min")
        assert result.name == "report-min.pdf"

    def test_pattern_missing_placeholder_falls_back(self, tmp_path):
        result = resolve_output_path(tmp_path / "report.pdf", None, "compressed.pdf")
        assert result.name == DEFAULT_NAMING_PATTERN.format(filename="report")

    def test_malformed_pattern_falls_back(self, tmp_path):
        result = resolve_output_path(tmp_path / "report.pdf", None, "{filename}_{oops}.pdf")
        assert result.name == "report_compressed.pdf"

    def test_invalid_characters_sanitised(self, tmp_path):
        result = resolve_output_path(tmp_path / "report.pdf", None, "{filename}:v2?.pdf")
        assert result.name == "report_v2_.pdf"

    def test_never_overwrites_existing_file(self, tmp_path):
        src = tmp_path / "report.pdf"
        src.write_bytes(b"%PDF")
        # Pattern that would resolve to the input itself
        result = resolve_output_path(src, None, "{filename}.pdf")
        assert result != src
        assert result == tmp_path / "report_1.pdf"


# ---------------------------------------------------------------------------
# BatchProcessor
# ---------------------------------------------------------------------------


def _result(path: Path, output: Path, success: bool = True, code=None) -> CompressionResult:
    size = path.stat().st_size
    return CompressionResult(
        success=success,
        input_path=str(path),
        output_path=str(output) if success else None,
        original_size=size,
        compressed_size=size // 2 if success else None,
        reduction_percent=50.0 if success else None,
        duration=0.01,
        preset_used="medium",
        timestamp=datetime.now(),
        error_code=code,
        error_message=None if success else "boom",
    )


def _make_processor(behaviour=None) -> BatchProcessor:
    engine = MagicMock()

    def _compress(
        input_path,
        output_path=None,
        preset="medium",
        timeout=300,
        progress_callback=None,
        cancel_event=None,
        keep_larger=False,
    ):
        if behaviour:
            custom = behaviour(input_path, output_path, progress_callback, cancel_event)
            if custom is not None:
                return custom
        output_path.write_bytes(b"%PDF compressed")
        return _result(input_path, output_path)

    engine.compress.side_effect = _compress
    return BatchProcessor(engine)


@pytest.fixture
def pdfs(tmp_path) -> List[Path]:
    files = []
    for name, size in (("c.pdf", 3000), ("a.pdf", 1000), ("b.pdf", 2000)):
        p = tmp_path / name
        p.write_bytes(b"%PDF-1.4 " + b"x" * size)
        files.append(p)
    return files


class TestCollectPdfFiles:
    def test_preserves_user_order_and_dedupes(self, pdfs):
        processor = _make_processor()
        collected = processor.collect_pdf_files(pdfs + [pdfs[0]])
        assert collected == pdfs  # same order as given, duplicate dropped

    def test_folder_contents_sorted(self, tmp_path, pdfs):
        processor = _make_processor()
        collected = processor.collect_pdf_files([tmp_path])
        assert [p.name for p in collected] == ["a.pdf", "b.pdf", "c.pdf"]

    def test_non_pdf_and_missing_paths_skipped(self, tmp_path, pdfs):
        (tmp_path / "notes.txt").write_text("x")
        processor = _make_processor()
        collected = processor.collect_pdf_files([tmp_path / "notes.txt", tmp_path / "nope.pdf"])
        assert collected == []


class TestProcessBatch:
    def test_successful_batch_totals(self, pdfs):
        processor = _make_processor()
        result = processor.process_batch(pdfs, preset="medium")

        assert result.total_files == 3
        assert result.successful == 3
        assert result.failed == 0
        assert result.cancelled is False
        assert result.total_size_before == sum(p.stat().st_size for p in pdfs)
        assert result.total_size_after == sum(p.stat().st_size // 2 for p in pdfs)
        assert result.total_reduction_percent == pytest.approx(50.0, abs=0.1)

    def test_output_dir_and_pattern_are_passed_to_engine(self, pdfs, tmp_path):
        processor = _make_processor()
        out_dir = tmp_path / "compressed"
        processor.process_batch(pdfs, output_dir=out_dir, naming_pattern="{filename}_s.pdf")

        assert out_dir.is_dir()
        destinations = [
            call.kwargs["output_path"] for call in processor.engine.compress.call_args_list
        ]
        assert destinations == [out_dir / f"{p.stem}_s.pdf" for p in pdfs]

    def test_timeout_and_keep_larger_are_forwarded(self, pdfs):
        processor = _make_processor()
        processor.process_batch(pdfs, timeout=42, keep_larger=True)
        for call in processor.engine.compress.call_args_list:
            assert call.kwargs["timeout"] == 42
            assert call.kwargs["keep_larger"] is True

    def test_progress_callback_receives_paths_in_order(self, pdfs):
        processor = _make_processor()
        seen: List[BatchProgress] = []
        processor.process_batch(pdfs, progress_callback=seen.append)

        assert [p.path for p in seen if p.detail == "starting"] == pdfs
        assert seen[-1].overall_progress == pytest.approx(1.0)
        assert all(0.0 <= p.overall_progress <= 1.0 for p in seen)
        assert all(p.total == 3 for p in seen)

    def test_page_progress_is_byte_weighted(self, pdfs):
        def behaviour(input_path, output_path, progress_callback, cancel_event):
            if progress_callback:
                progress_callback(1, 2)  # half way through this file
            return None

        processor = _make_processor(behaviour)
        seen: List[BatchProgress] = []
        processor.process_batch(pdfs[:1], progress_callback=seen.append)

        page_update = next(p for p in seen if p.detail == "page 1 of 2")
        assert page_update.file_progress == pytest.approx(0.5)
        assert page_update.overall_progress == pytest.approx(0.5)

    def test_failed_file_counts_as_unsaved(self, pdfs):
        def behaviour(input_path, output_path, progress_callback, cancel_event):
            if input_path.name == "a.pdf":
                return _result(input_path, output_path, success=False, code="E004")
            return None

        processor = _make_processor(behaviour)
        result = processor.process_batch(pdfs)

        assert result.successful == 2
        assert result.failed == 1
        # Failed file contributes its full size to "after" (nothing saved)
        a_size = next(p for p in pdfs if p.name == "a.pdf").stat().st_size
        assert result.total_size_after == a_size + sum(
            p.stat().st_size // 2 for p in pdfs if p.name != "a.pdf"
        )

    def test_cancel_before_start_processes_nothing(self, pdfs):
        processor = _make_processor()
        cancel = threading.Event()
        cancel.set()
        result = processor.process_batch(pdfs, cancel_event=cancel)

        assert result.cancelled is True
        assert result.processed == 0
        assert result.skipped == 3
        processor.engine.compress.assert_not_called()

    def test_cancel_mid_batch_stops_remaining_files(self, pdfs):
        cancel = threading.Event()

        def behaviour(input_path, output_path, progress_callback, cancel_event):
            if input_path == pdfs[1]:
                cancel.set()
                return _result(input_path, output_path, success=False, code=ERROR_CANCELLED)
            return None

        processor = _make_processor(behaviour)
        result = processor.process_batch(pdfs, cancel_event=cancel)

        assert result.cancelled is True
        assert result.processed == 2  # first succeeded, second was cancelled
        assert result.successful == 1
        assert result.failed == 0  # a cancelled file is not a failure
        assert result.skipped == 1

    def test_empty_batch(self):
        processor = _make_processor()
        result = processor.process_batch([])
        assert result.total_files == 0
        assert result.total_reduction_percent == 0.0
        assert "Processed 0 of 0" in result.get_summary()
