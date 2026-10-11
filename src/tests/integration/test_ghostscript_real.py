"""
Integration tests that drive the real Ghostscript binary.

Skipped automatically when Ghostscript is not available (CI without the
bundled copy). The sample PDF is generated on the fly with Ghostscript
itself, so no binary fixtures are checked in.
"""

import subprocess
import threading
from pathlib import Path

import pytest

from squash.core.batch import BatchProcessor
from squash.core.compression import (
    ERROR_CANCELLED,
    ERROR_GHOSTSCRIPT,
    CompressionEngine,
)
from squash.core.ghostscript import GhostscriptError, GhostscriptWrapper, detect_ghostscript

GS_PATH = detect_ghostscript()
pytestmark = pytest.mark.skipif(GS_PATH is None, reason="Ghostscript not available")

_SAMPLE_PS = b"""%!PS
/Helvetica findfont 24 scalefont setfont
1 1 4 { pop 72 700 moveto (Hello Squash) show showpage } for
"""


def _run_gs(*args: str) -> None:
    subprocess.run([str(GS_PATH), "-q", "-dBATCH", "-dNOPAUSE", *args], check=True, timeout=60)


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    ps = tmp_path / "sample.ps"
    ps.write_bytes(_SAMPLE_PS)
    pdf = tmp_path / "sample.pdf"
    _run_gs("-sDEVICE=pdfwrite", f"-sOutputFile={pdf}", str(ps))
    assert pdf.exists()
    return pdf


@pytest.fixture
def locked_pdf(tmp_path) -> Path:
    ps = tmp_path / "locked.ps"
    ps.write_bytes(_SAMPLE_PS)
    pdf = tmp_path / "locked.pdf"
    _run_gs(
        "-sDEVICE=pdfwrite",
        "-sOwnerPassword=secret",
        "-sUserPassword=secret",
        f"-sOutputFile={pdf}",
        str(ps),
    )
    return pdf


class TestWrapperWithRealGhostscript:
    def test_compress_reports_page_progress(self, sample_pdf, tmp_path):
        wrapper = GhostscriptWrapper(GS_PATH)
        out = tmp_path / "out.pdf"
        pages = []

        wrapper.compress(
            sample_pdf,
            out,
            {"PDFSETTINGS": "/ebook", "AutoRotatePages": "/None"},
            progress_callback=lambda page, total: pages.append((page, total)),
        )

        assert out.exists() and out.stat().st_size > 0
        assert not list(tmp_path.glob("*.part"))
        assert [p for p, _ in pages] == [1, 2, 3, 4]
        assert all(total == 4 for _, total in pages)

    def test_password_protected_input_is_reported(self, locked_pdf, tmp_path):
        wrapper = GhostscriptWrapper(GS_PATH)
        out = tmp_path / "out.pdf"
        with pytest.raises(GhostscriptError) as excinfo:
            wrapper.compress(locked_pdf, out, {"PDFSETTINGS": "/ebook"})
        assert excinfo.value.code == "password"
        assert not out.exists()

    def test_garbage_input_is_reported_as_corrupt(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"%PDF-1.4\nthis is not really a pdf\n")
        wrapper = GhostscriptWrapper(GS_PATH)
        with pytest.raises(GhostscriptError) as excinfo:
            wrapper.compress(bad, tmp_path / "out.pdf", {"PDFSETTINGS": "/ebook"})
        assert excinfo.value.code in {"corrupt", "unknown"}
        assert not (tmp_path / "out.pdf").exists()

    def test_cancel_event_already_set_aborts_quickly(self, sample_pdf, tmp_path):
        wrapper = GhostscriptWrapper(GS_PATH)
        cancel = threading.Event()
        cancel.set()
        with pytest.raises(GhostscriptError) as excinfo:
            wrapper.compress(sample_pdf, tmp_path / "out.pdf", {}, cancel_event=cancel)
        assert excinfo.value.code == "cancelled"
        assert not (tmp_path / "out.pdf").exists()

    def test_percent_in_output_name(self, sample_pdf, tmp_path):
        wrapper = GhostscriptWrapper(GS_PATH)
        out = tmp_path / "100% done.pdf"
        wrapper.compress(sample_pdf, out, {"PDFSETTINGS": "/ebook"})
        assert out.exists()


class TestEngineAndBatchWithRealGhostscript:
    def test_engine_end_to_end(self, sample_pdf):
        engine = CompressionEngine(GS_PATH)
        result = engine.compress(sample_pdf, preset="small", keep_larger=True)
        assert result.success, result.error_message
        assert Path(result.output_path).exists()
        assert result.compressed_size is not None

    def test_engine_maps_locked_pdf_to_e004(self, locked_pdf):
        engine = CompressionEngine(GS_PATH)
        result = engine.compress(locked_pdf, preset="medium")
        assert result.success is False
        assert result.error_code == ERROR_GHOSTSCRIPT
        assert "password" in (result.error_message or "").lower()

    def test_engine_cancelled_maps_to_e006(self, sample_pdf):
        engine = CompressionEngine(GS_PATH)
        cancel = threading.Event()
        cancel.set()
        result = engine.compress(sample_pdf, cancel_event=cancel)
        assert result.error_code == ERROR_CANCELLED
        assert result.cancelled

    def test_batch_into_custom_folder(self, sample_pdf, tmp_path):
        processor = BatchProcessor(CompressionEngine(GS_PATH))
        out_dir = tmp_path / "squashed"
        result = processor.process_batch(
            [sample_pdf],
            preset="medium",
            output_dir=out_dir,
            naming_pattern="{filename}-sm.pdf",
            keep_larger=True,
        )
        assert result.successful == 1
        assert (out_dir / "sample-sm.pdf").exists()

    def test_all_builtin_presets_run(self, sample_pdf):
        engine = CompressionEngine(GS_PATH)
        for name in engine.preset_manager.get_preset_names():
            result = engine.compress(sample_pdf, preset=name)
            assert result.success, f"{name}: {result.error_message}"
