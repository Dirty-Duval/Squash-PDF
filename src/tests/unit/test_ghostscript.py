"""
Unit tests for the Ghostscript wrapper helpers (no Ghostscript binary required).
"""

from pathlib import Path

import pytest

from squash.core.ghostscript import (
    GhostscriptError,
    GhostscriptWrapper,
    classify_error,
    escape_output_path,
    parse_progress_line,
)


class TestParseProgressLine:
    def test_total_pages(self):
        assert parse_progress_line("Processing pages 1 through 12.\n") == ("total", 12)

    def test_page_marker(self):
        assert parse_progress_line("Page 7") == ("page", 7)

    def test_page_marker_with_trailing_whitespace(self):
        assert parse_progress_line("Page 3   \r\n") == ("page", 3)

    def test_unrelated_lines_ignored(self):
        assert parse_progress_line("GPL Ghostscript 10.06.0 (2025-09-09)") is None
        assert parse_progress_line("Loading font Helvetica from %rom%Resource/Font") is None
        assert parse_progress_line("") is None

    def test_page_word_inside_other_text_ignored(self):
        # Only a bare "Page N" line is a progress marker
        assert parse_progress_line("Pages are Page 2 wide") is None


class TestClassifyError:
    def test_password_protected(self):
        output = "GPL Ghostscript 10.06.0:\n   **** This file requires a password for access."
        code, message, _ = classify_error(output, 0)
        assert code == "password"
        assert "password" in message.lower()

    def test_corrupt_file(self):
        output = (
            "Error: /stackunderflow in --not--\nGPL Ghostscript: Unrecoverable error, exit code 1"
        )
        code, message, detail = classify_error(output, 1)
        assert code == "corrupt"
        assert "damaged" in message.lower()
        assert "error" in detail.lower()

    def test_permission_error(self):
        code, _, _ = classify_error("Error: /invalidfileaccess in --file--", 1)
        assert code == "permission"

    def test_disk_error(self):
        code, _, _ = classify_error("Error: /ioerror in --showpage--", 1)
        assert code == "disk"

    def test_unknown_error_includes_exit_code_and_detail(self):
        code, message, detail = classify_error("Something odd happened\nLast line here", 3)
        assert code == "unknown"
        assert "exit code 3" in message
        assert detail == "Last line here"

    def test_unknown_error_without_output(self):
        code, message, detail = classify_error("", None)
        assert code == "unknown"
        assert "unknown status" in message
        assert detail == ""


class TestEscapeOutputPath:
    def test_percent_is_doubled(self):
        assert escape_output_path(Path("C:/out/100%.pdf")).endswith("100%%.pdf")

    def test_plain_path_unchanged(self):
        assert escape_output_path(Path("C:/out/report.pdf")) == str(Path("C:/out/report.pdf"))


class TestGhostscriptWrapperInit:
    def test_explicit_existing_path_is_used(self, tmp_path):
        fake_gs = tmp_path / "gswin64c.exe"
        fake_gs.write_bytes(b"MZ")
        wrapper = GhostscriptWrapper(fake_gs)
        assert wrapper.gs_path == fake_gs

    def test_missing_explicit_path_falls_back_to_detection(self, tmp_path, monkeypatch):
        fake_gs = tmp_path / "detected.exe"
        fake_gs.write_bytes(b"MZ")
        monkeypatch.setattr("squash.core.ghostscript.detect_ghostscript", lambda: fake_gs)
        wrapper = GhostscriptWrapper(tmp_path / "does_not_exist.exe")
        assert wrapper.gs_path == fake_gs

    def test_no_ghostscript_anywhere_raises(self, monkeypatch):
        monkeypatch.setattr("squash.core.ghostscript.detect_ghostscript", lambda: None)
        with pytest.raises(RuntimeError):
            GhostscriptWrapper(None)


class TestBuildCommand:
    @pytest.fixture
    def wrapper(self, tmp_path):
        fake_gs = tmp_path / "gs.exe"
        fake_gs.write_bytes(b"MZ")
        return GhostscriptWrapper(fake_gs)

    def test_basic_structure(self, wrapper, tmp_path):
        cmd = wrapper.build_command(
            tmp_path / "in.pdf",
            tmp_path / "out.pdf",
            {"PDFSETTINGS": "/ebook", "ColorImageResolution": 150},
        )
        assert cmd[0] == str(wrapper.gs_path)
        assert "-sDEVICE=pdfwrite" in cmd
        assert "-dBATCH" in cmd and "-dNOPAUSE" in cmd
        assert "-dQUIET" not in cmd  # progress output must stay enabled
        assert "-dPDFSETTINGS=/ebook" in cmd
        assert "-dCompatibilityLevel=1.5" in cmd
        assert "-dColorImageResolution=150" in cmd
        assert cmd[-2] == f"-sOutputFile={tmp_path / 'out.pdf'}"
        assert cmd[-1] == str(tmp_path / "in.pdf")

    def test_boolean_parameters(self, wrapper, tmp_path):
        cmd = wrapper.build_command(
            tmp_path / "in.pdf", tmp_path / "out.pdf", {"Down": True, "Up": False}
        )
        assert "-dDown" in cmd
        assert "-dUp=false" in cmd

    def test_pdfsettings_precedes_overrides(self, wrapper, tmp_path):
        cmd = wrapper.build_command(
            tmp_path / "in.pdf",
            tmp_path / "out.pdf",
            {"PDFSETTINGS": "/screen", "AutoRotatePages": "/None"},
        )
        assert cmd.index("-dPDFSETTINGS=/screen") < cmd.index("-dAutoRotatePages=/None")

    def test_compatibility_level_override(self, wrapper, tmp_path):
        cmd = wrapper.build_command(
            tmp_path / "in.pdf", tmp_path / "out.pdf", {"CompatibilityLevel": "1.7"}
        )
        assert "-dCompatibilityLevel=1.7" in cmd
        assert "-dCompatibilityLevel=1.5" not in cmd


class TestValidatePdf:
    def test_header_at_start(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4\n...")
        assert GhostscriptWrapper.validate_pdf(pdf) is True

    def test_header_after_junk_within_first_kilobyte(self, tmp_path):
        pdf = tmp_path / "b.pdf"
        pdf.write_bytes(b"\x00" * 200 + b"%PDF-1.7\n")
        assert GhostscriptWrapper.validate_pdf(pdf) is True

    def test_not_a_pdf(self, tmp_path):
        bad = tmp_path / "c.pdf"
        bad.write_bytes(b"hello world")
        assert GhostscriptWrapper.validate_pdf(bad) is False

    def test_missing_file(self, tmp_path):
        assert GhostscriptWrapper.validate_pdf(tmp_path / "missing.pdf") is False


class TestGhostscriptErrorObject:
    def test_attributes(self):
        err = GhostscriptError("password", "Locked", "detail text")
        assert err.code == "password"
        assert err.message == "Locked"
        assert err.detail == "detail text"
        assert str(err) == "Locked"
