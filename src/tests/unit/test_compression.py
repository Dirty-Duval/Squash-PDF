"""
Unit tests for CompressionEngine.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from squash.core.compression import CompressionEngine, CompressionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(tmp_path: Path) -> CompressionEngine:
    """Return a CompressionEngine with a mocked GhostscriptWrapper."""
    engine = CompressionEngine.__new__(CompressionEngine)
    engine.gs = MagicMock()
    engine.gs.validate_pdf.return_value = True

    # Default compress behaviour: creates the output file
    def _fake_compress(input_path, output_path, params, timeout):
        output_path.write_bytes(b"%PDF-1.4 fake compressed")
        return True

    engine.gs.compress.side_effect = _fake_compress

    from squash.core.presets import PresetManager
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

    def test_invalid_preset_returns_error(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf, preset="nonexistent_preset")

        assert result.success is False
        assert result.error_code == "E003"

    def test_successful_compression(self, tmp_path):
        # Write a "large" input PDF so compressed output is smaller
        pdf = tmp_path / "input.pdf"
        pdf.write_bytes(b"%PDF-1.4 " + b"x" * 10_000)

        engine = _make_engine(tmp_path)

        def _compress_smaller(input_path, output_path, params, timeout):
            output_path.write_bytes(b"%PDF-1.4 " + b"x" * 5_000)
            return True

        engine.gs.compress.side_effect = _compress_smaller

        result = engine.compress(pdf, preset="medium")

        assert result.success is True
        assert result.compressed_size is not None
        assert result.compressed_size < result.original_size
        assert result.reduction_percent > 0
        assert result.size_increased is False

    def test_output_larger_than_input_sets_flag(self, tmp_path):
        pdf = tmp_path / "already_optimised.pdf"
        pdf.write_bytes(b"%PDF-1.4 small")

        engine = _make_engine(tmp_path)

        def _compress_larger(input_path, output_path, params, timeout):
            # Simulate GS producing a bigger file
            output_path.write_bytes(b"%PDF-1.4 " + b"x" * 100_000)
            return True

        engine.gs.compress.side_effect = _compress_larger

        result = engine.compress(pdf, preset="medium")

        assert result.success is True
        assert result.size_increased is True
        assert result.reduction_percent < 0

    def test_output_path_auto_generated(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data")

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf)

        assert result.output_path is not None
        assert "doc_compressed" in result.output_path

    def test_output_path_collision_generates_unique_name(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data")
        # Pre-create the default output path to trigger collision avoidance
        (tmp_path / "doc_compressed.pdf").write_bytes(b"existing")

        engine = _make_engine(tmp_path)
        result = engine.compress(pdf)

        assert result.output_path is not None
        # Should be doc_compressed_1.pdf, not doc_compressed.pdf
        assert result.output_path != str(tmp_path / "doc_compressed.pdf")

    def test_ghostscript_failure_returns_error(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        engine = _make_engine(tmp_path)
        engine.gs.compress.side_effect = subprocess.CalledProcessError(1, "gs")

        result = engine.compress(pdf)
        assert result.success is False
        assert result.error_code == "E005"

    def test_custom_output_path_respected(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        pdf.write_bytes(b"%PDF-1.4 test data" + b"x" * 5_000)
        out = tmp_path / "my_output.pdf"

        engine = _make_engine(tmp_path)

        def _compress(input_path, output_path, params, timeout):
            output_path.write_bytes(b"%PDF-1.4 compressed")
            return True

        engine.gs.compress.side_effect = _compress
        result = engine.compress(pdf, output_path=out)

        assert result.output_path == str(out)
