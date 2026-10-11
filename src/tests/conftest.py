"""
Pytest configuration and shared fixtures.
"""

from pathlib import Path

import pytest

from squash.utils.filesystem import FileSystemHelper


@pytest.fixture(autouse=True)
def isolated_app_data(tmp_path, monkeypatch):
    """Redirect %APPDATA%/Squash to a temp folder for every test.

    PresetManager, HistoryManager and ConfigManager all derive their storage
    location from FileSystemHelper.get_app_data_dir(); without this fixture the
    test-suite would read and write the developer's real custom presets.
    """
    app_dir = tmp_path / "appdata" / "Squash"
    app_dir.mkdir(parents=True)
    monkeypatch.setattr(FileSystemHelper, "get_app_data_dir", staticmethod(lambda: app_dir))
    return app_dir


@pytest.fixture
def sample_pdf_path():
    """Path where an optional real sample PDF fixture may live."""
    return Path(__file__).parent / "fixtures" / "sample_pdfs" / "sample.pdf"
