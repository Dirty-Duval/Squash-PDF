"""
Unit tests for history management.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from squash.core.compression import CompressionResult
from squash.utils.history import HistoryEntry, HistoryManager


def create_mock_result(
    filename: str,
    original: int = 1000000,
    compressed: int = 500000,
    preset: str = "medium",
    success: bool = True
) -> CompressionResult:
    """Create a mock CompressionResult for testing.

    Args:
        filename: Input filename
        original: Original file size in bytes
        compressed: Compressed file size in bytes
        preset: Preset name
        success: Whether compression succeeded

    Returns:
        CompressionResult object
    """
    reduction = ((original - compressed) / original) * 100 if original > 0 else 0.0

    return CompressionResult(
        success=success,
        input_path=filename,
        output_path=f"compressed_{filename}" if success else None,
        original_size=original,
        compressed_size=compressed if success else None,
        reduction_percent=reduction if success else None,
        duration=1.0,
        preset_used=preset,
        timestamp=datetime.now(),
        error_code=None if success else "ERROR",
        error_message=None if success else "Test error"
    )


class TestHistoryManager:
    """Test cases for HistoryManager."""

    def test_initialization(self, tmp_path):
        """Test HistoryManager creates database successfully."""
        db_path = tmp_path / "test_history.db"
        manager = HistoryManager(db_path)

        assert db_path.exists()
        assert manager.db_path == db_path

    def test_database_schema_creation(self, tmp_path):
        """Test database schema is created correctly."""
        db_path = tmp_path / "test.db"
        manager = HistoryManager(db_path)

        # Verify table exists by querying it
        entries = manager.get_recent()
        assert entries == []

    def test_add_single_entry(self, tmp_path):
        """Test adding a single history entry."""
        manager = HistoryManager(tmp_path / "test.db")
        result = create_mock_result("test.pdf", 1000000, 500000)

        success = manager.add_entry(result)
        assert success is True

        entries = manager.get_recent(limit=10)
        assert len(entries) == 1
        assert entries[0].preset_name == "medium"
        assert entries[0].compression_ratio == 50.0
        assert entries[0].original_size == 1000000
        assert entries[0].compressed_size == 500000

    def test_add_multiple_entries(self, tmp_path):
        """Test adding multiple history entries."""
        manager = HistoryManager(tmp_path / "test.db")

        results = [
            create_mock_result("file1.pdf", 1000000, 500000),
            create_mock_result("file2.pdf", 2000000, 1000000),
            create_mock_result("file3.pdf", 500000, 250000),
        ]

        added = manager.add_entries(results)
        assert added == 3

        entries = manager.get_recent()
        assert len(entries) == 3

    def test_enforce_50_entry_limit(self, tmp_path):
        """Test automatic cleanup of old entries when limit exceeded."""
        manager = HistoryManager(tmp_path / "test.db")

        # Add 60 entries
        for i in range(60):
            result = create_mock_result(f"file{i}.pdf")
            manager.add_entry(result)

        # Should only keep last 50
        entries = manager.get_recent(limit=100)
        assert len(entries) == 50

        # Verify newest entries are kept (file50-file59)
        newest_entry = entries[0]
        assert "file59" in newest_entry.input_path

    def test_get_recent_with_limit(self, tmp_path):
        """Test retrieving recent entries with custom limit."""
        manager = HistoryManager(tmp_path / "test.db")

        # Add 20 entries
        for i in range(20):
            result = create_mock_result(f"file{i}.pdf")
            manager.add_entry(result)

        # Get only 10
        entries = manager.get_recent(limit=10)
        assert len(entries) == 10

        # Verify newest first (file19-file10)
        assert "file19" in entries[0].input_path

    def test_search_by_filename(self, tmp_path):
        """Test searching history by filename."""
        manager = HistoryManager(tmp_path / "test.db")

        manager.add_entry(create_mock_result("document.pdf"))
        manager.add_entry(create_mock_result("image.pdf"))
        manager.add_entry(create_mock_result("another_document.pdf"))

        # Search for "document"
        results = manager.search("document")
        assert len(results) == 2
        assert all("document" in r.input_path for r in results)

        # Search for "image"
        results = manager.search("image")
        assert len(results) == 1
        assert "image" in results[0].input_path

    def test_search_case_insensitive(self, tmp_path):
        """Test search is case-insensitive."""
        manager = HistoryManager(tmp_path / "test.db")

        manager.add_entry(create_mock_result("Document.PDF"))

        results = manager.search("document")
        assert len(results) == 1

        results = manager.search("DOCUMENT")
        assert len(results) == 1

    def test_clear_history(self, tmp_path):
        """Test clearing all history entries."""
        manager = HistoryManager(tmp_path / "test.db")

        # Add entries
        manager.add_entry(create_mock_result("file1.pdf"))
        manager.add_entry(create_mock_result("file2.pdf"))

        # Verify entries exist
        entries = manager.get_recent()
        assert len(entries) == 2

        # Clear history
        success = manager.clear_history()
        assert success is True

        # Verify empty
        entries = manager.get_recent()
        assert len(entries) == 0

    def test_cleanup_old_entries(self, tmp_path):
        """Test cleanup of entries older than threshold."""
        manager = HistoryManager(tmp_path / "test.db")

        # Add entry with old timestamp
        old_result = create_mock_result("old.pdf")
        old_result.timestamp = datetime.now() - timedelta(days=35)
        manager.add_entry(old_result)

        # Add recent entry
        recent_result = create_mock_result("recent.pdf")
        manager.add_entry(recent_result)

        # Cleanup entries older than 30 days
        deleted = manager.cleanup_old(days=30)
        assert deleted == 1

        # Verify only recent entry remains
        entries = manager.get_recent()
        assert len(entries) == 1
        assert "recent" in entries[0].input_path

    def test_get_statistics(self, tmp_path):
        """Test statistics calculation."""
        manager = HistoryManager(tmp_path / "test.db")

        # Add 3 entries with known sizes
        manager.add_entry(create_mock_result("f1.pdf", 1000000, 500000))  # 50% reduction
        manager.add_entry(create_mock_result("f2.pdf", 2000000, 1000000))  # 50% reduction
        manager.add_entry(create_mock_result("f3.pdf", 1000000, 600000))  # 40% reduction

        stats = manager.get_statistics()

        assert stats["total_files"] == 3
        assert stats["total_original_size"] == 4000000
        assert stats["total_compressed_size"] == 2100000
        assert stats["bytes_saved"] == 1900000
        assert 46.0 < stats["average_ratio"] < 47.0  # Average of 50, 50, 40
        assert stats["success_rate"] == 100.0

    def test_statistics_with_failures(self, tmp_path):
        """Test statistics include failed compressions."""
        manager = HistoryManager(tmp_path / "test.db")

        # Add successful and failed entries
        manager.add_entry(create_mock_result("success.pdf", 1000000, 500000, success=True))
        manager.add_entry(create_mock_result("failed.pdf", 1000000, 0, success=False))

        stats = manager.get_statistics()

        assert stats["total_files"] == 2
        assert stats["success_rate"] == 50.0

    def test_empty_database_statistics(self, tmp_path):
        """Test statistics on empty database."""
        manager = HistoryManager(tmp_path / "test.db")

        stats = manager.get_statistics()

        assert stats["total_files"] == 0
        assert stats["bytes_saved"] == 0
        assert stats["average_ratio"] == 0.0
        assert stats["success_rate"] == 0.0

    def test_history_entry_dataclass(self):
        """Test HistoryEntry dataclass creation."""
        entry = HistoryEntry(
            id=1,
            input_path="test.pdf",
            output_path="compressed_test.pdf",
            preset_name="medium",
            original_size=1000000,
            compressed_size=500000,
            compression_ratio=50.0,
            duration=2.5,
            timestamp=datetime.now(),
            success=True,
            error_message=None
        )

        assert entry.id == 1
        assert entry.input_path == "test.pdf"
        assert entry.preset_name == "medium"
        assert entry.compression_ratio == 50.0
        assert entry.success is True

    def test_concurrent_access(self, tmp_path):
        """Test thread-safe database access."""
        manager = HistoryManager(tmp_path / "test.db")

        # Simulate concurrent writes
        import threading

        def add_entries():
            for i in range(10):
                result = create_mock_result(f"file_{threading.current_thread().name}_{i}.pdf")
                manager.add_entry(result)

        threads = [threading.Thread(target=add_entries) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have 30 entries total
        entries = manager.get_recent(limit=50)
        assert len(entries) == 30
