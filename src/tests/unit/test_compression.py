"""
Unit tests for CompressionEngine.
"""

import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from squash.core.compression import (
    ERROR_CANCELLED,
    ERROR_GHOSTSCRIPT,
    ERROR_OUTPUT_IS_INPUT,
    ERROR_TIMEOUT,
    ERROR_UNEXPECTED,
    CompressionEngine,
    CompressionResult,
)
from squash.core.ghostscript import GhostscriptError
from squash.core.presets import PresetManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_output(input_path, output_path, params, **kwargs):
    """Default fake Ghostscript behaviour: create a small output file."""
    output_path.write_bytes(b"%PDF-1.4 fake compressed")


def _make_engine(tmp_path: Path) -> CompressionEngine:
    """Return a CompressionEngine with a mocked GhostscriptWrapper."""
    engine = CompressionEngine.__new__(CompressionEngine)
    engine.gs = MagicMock()
    engine.gs.validate_pdf.return_value = True
    engine.gs.compress.side_effect = _write_output
    engine.preset_manager = PresetManager()
    return engine


# ---------------------------------------------------------------------------
# CompressionResult helpers
# ---------------------------------------------------------------------------


class TestCompressionResultFormatSizes:
    def test_with_compressed_size(self):
        result = CompressionResult(
            success=True,
            input_path="a.pdf",
            output_path="a_compressed.pdf",
            original_size=2 * 1024 * 1024,
            compressed_size=1 * 1024 * 1024,
            reduction_percent=50.0,
            duration=1.0,
            preset_used="medium",
            timestamp=datetime.now(),
        )
        assert result.format_sizes() == "2.0 MB → 1.0 MB"

    def test_without_compressed_size(self):
        result = CompressionResult(
            success=False,
            input_path="a.pdf",
            output_path=None,
            original_size=2 * 1024 * 1024,
            compressed_size=None,
            reduction_percent=None,
            duration=0.0,
            preset_used="medium",
            timestamp=datetime.now(),
        )
        assert result.format_sizes() == "2.0 MB"

    def test_zero_compressed_size_not_treated_as_none(self):
        """compressed_size=0 should not fall through to the no-size branch."""
        result = CompressionResult(
            success=True,
            input_path="a.pdf",
            output_path="a_compressed.pdf",
            original_size=1024 * 1024,
            compressed_size=0,
            reduction_percent=100.0,
            duration=1.0,
            preset_used="medium",
            timestamp=datetime.now(),
        )
        assert "→" in result.format_sizes()

    def test_cancelled_property(self):
        result = CompressionResult(
            success=False,
            input_path="a.pdf",
            output_path=None,
            original_size=1,
            compressed_size=None,
            reduction_percent=None,
            duration=0.0,
            preset_used="medium",
            timestamp=datetime.now(),
            error_code=ERROR_CANCELLED,
        )
        assert result.cancelled is True


# ---------------------------------------------------------------------------
# CompressionEngine.compress()
# ---------------------------------------------------------------------------


class TestCompressionEngineCompress:
    def test_file_not_found_returns_error(self, tmp_path):
        engine = _make_engine(tmp_path)
        result = engine.compress(tmp_path / "nonexistent.pdf")

        assert result.success is False
        assert result.error_code == "E001"
        assert result.original_size == 0

    def test_invalid_pdf_returns_error(self, tmp_path):
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"not a pdf")

        engine = _make_engine(tmp_path)
        engine.gs.validate_pdf.return_value = False

        result = engine.compress(bad_pdf)
        assert result.success is False
        assert result.error_code == "E002"
        assert result.original_size == bad_pdf.stat().st_size

    def test_invalid_preset_returns_error(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf, preset="nonexistent_preset")

        assert result.success is False
        assert result.error_code == "E003"
        engine.gs.compress.assert_not_called()

    def test_successful_compression(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        pdf.write_bytes(b"%PDF-1.4 " + b"x" * 10_000)

        engine = _make_engine(tmp_path)

        def _compress_smaller(input_path, output_path, params, **kwargs):
            output_path.write_bytes(b"%PDF-1.4 " + b"x" * 5_000)

        engine.gs.compress.side_effect = _compress_smaller

        result = engine.compress(pdf, preset="medium")

        assert result.success is True
        assert result.compressed_size is not None
        assert result.compressed_size < result.original_size
        assert result.reduction_percent > 0
        assert result.size_increased is False

    def _engine_with_larger_output(self, tmp_path):
        pdf = tmp_path / "already_optimised.pdf"
        pdf.write_bytes(b"%PDF-1.4 small")
        engine = _make_engine(tmp_path)

        def _compress_larger(input_path, output_path, params, **kwargs):
            output_path.write_bytes(b"%PDF-1.4 " + b"x" * 100_000)

        engine.gs.compress.side_effect = _compress_larger
        return pdf, engine

    def test_larger_output_is_discarded_and_original_kept_by_default(self, tmp_path):
        pdf, engine = self._engine_with_larger_output(tmp_path)

        result = engine.compress(pdf, preset="medium")

        assert result.success is True
        assert result.size_increased is True
        assert result.output_discarded is True
        assert result.output_path is None
        assert result.compressed_size == result.original_size
        assert result.reduction_percent == 0.0
        assert "original was kept" in (result.note or "")
        assert not (tmp_path / "already_optimised_compressed.pdf").exists()
        assert pdf.read_bytes() == b"%PDF-1.4 small"

    def test_keep_larger_preserves_output(self, tmp_path):
        pdf, engine = self._engine_with_larger_output(tmp_path)

        result = engine.compress(pdf, preset="medium", keep_larger=True)

        assert result.success is True
        assert result.size_increased is True
        assert result.output_discarded is False
        assert result.reduction_percent < 0
        assert Path(result.output_path).exists()

    def test_output_path_auto_generated(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data" + b"x" * 1_000)

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf)

        assert result.output_path is not None
        assert "doc_compressed" in result.output_path

    def test_output_path_collision_generates_unique_name(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data" + b"x" * 1_000)
        (tmp_path / "doc_compressed.pdf").write_bytes(b"existing")

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf)

        assert result.output_path is not None
        assert result.output_path != str(tmp_path / "doc_compressed.pdf")

    def test_output_equal_to_input_is_refused(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data" + b"x" * 1_000)

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf, output_path=pdf)

        assert result.success is False
        assert result.error_code == ERROR_OUTPUT_IS_INPUT
        engine.gs.compress.assert_not_called()
        assert pdf.read_bytes().startswith(b"%PDF-1.4 test data")  # untouched

    def test_ghostscript_error_maps_to_e004_with_message(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        engine = _make_engine(tmp_path)
        engine.gs.compress.side_effect = GhostscriptError("password", "Locked PDF", "")

        result = engine.compress(pdf)
        assert result.success is False
        assert result.error_code == ERROR_GHOSTSCRIPT
        assert result.error_message == "Locked PDF"

    def test_cancelled_maps_to_e006(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        engine = _make_engine(tmp_path)
        engine.gs.compress.side_effect = GhostscriptError("cancelled", "Cancelled", "")

        result = engine.compress(pdf)
        assert result.error_code == ERROR_CANCELLED
        assert result.cancelled is True

    def test_timeout_maps_to_e007(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        engine = _make_engine(tmp_path)
        engine.gs.compress.side_effect = GhostscriptError("timeout", "Too slow", "")

        result = engine.compress(pdf)
        assert result.error_code == ERROR_TIMEOUT

    def test_unexpected_exception_maps_to_e005(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        engine = _make_engine(tmp_path)
        engine.gs.compress.side_effect = RuntimeError("kaboom")

        result = engine.compress(pdf)
        assert result.success is False
        assert result.error_code == ERROR_UNEXPECTED
        assert "kaboom" in result.error_message

    def test_custom_output_path_respected(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data" + b"x" * 5_000)
        out = tmp_path / "my_output.pdf"

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf, output_path=out)

        assert result.output_path == str(out)

    def test_timeout_progress_and_cancel_are_forwarded(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data" + b"x" * 1_000)

        engine = _make_engine(tmp_path)
        cancel = threading.Event()
        callback = MagicMock()

        engine.compress(pdf, timeout=77, progress_callback=callback, cancel_event=cancel)

        kwargs = engine.gs.compress.call_args.kwargs
        assert kwargs["timeout"] == 77
        assert kwargs["progress_callback"] is callback
        assert kwargs["cancel_event"] is cancel

    def test_preset_parameters_are_used(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data" + b"x" * 1_000)

        engine = _make_engine(tmp_path)
        engine.compress(pdf, preset="small")

        params = engine.gs.compress.call_args.args[2]
        assert params["PDFSETTINGS"] == "/screen"
        assert params["AutoRotatePages"] == "/None"
