"""
Pytest configuration and shared fixtures.
"""

import pytest
from pathlib import Path


@pytest.fixture
def sample_pdf_path():
    """
    Fixture for sample PDF file path.

    Note: Actual PDF files need to be added to tests/fixtures/sample_pdfs/
    """
    return Path(__file__).parent / "fixtures" / "sample_pdfs" / "sample.pdf"


@pytest.fixture
def mock_ghostscript_path(monkeypatch):
    """Mock Ghostscript path for testing without Ghostscript installed."""

    def mock_which(name):
        return "/usr/bin/gs" if name == "gs" else None

    monkeypatch.setattr("shutil.which", mock_which)
