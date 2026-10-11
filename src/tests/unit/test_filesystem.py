"""
Unit tests for filesystem helpers.
"""

from squash.utils.filesystem import FileSystemHelper


class TestFormatSize:
    def test_bytes(self):
        assert FileSystemHelper.format_size(0) == "0 B"
        assert FileSystemHelper.format_size(512) == "512 B"

    def test_kilobytes(self):
        assert FileSystemHelper.format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert FileSystemHelper.format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert FileSystemHelper.format_size(3 * 1024**3) == "3.0 GB"

    def test_negative(self):
        assert FileSystemHelper.format_size(-2 * 1024 * 1024) == "-2.0 MB"

    def test_precision(self):
        assert FileSystemHelper.format_size(1536, precision=2) == "1.50 KB"


class TestUniqueFilename:
    def test_free_path_returned_unchanged(self, tmp_path):
        target = tmp_path / "a.pdf"
        assert FileSystemHelper.get_unique_filename(target) == target

    def test_suffix_increments(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"x")
        (tmp_path / "a_1.pdf").write_bytes(b"x")
        assert FileSystemHelper.get_unique_filename(tmp_path / "a.pdf") == tmp_path / "a_2.pdf"


class TestWritableDirectory:
    def test_existing_directory(self, tmp_path):
        assert FileSystemHelper.is_writable_directory(tmp_path) is True

    def test_missing_directory(self, tmp_path):
        assert FileSystemHelper.is_writable_directory(tmp_path / "nope") is False

    def test_file_is_not_a_directory(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x")
        assert FileSystemHelper.is_writable_directory(f) is False
