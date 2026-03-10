"""
History management for Squash PDF Compressor.

This module provides SQLite-based history tracking for compression operations.
Stores the last 50 compression operations with full metadata.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.compression import CompressionResult
from .filesystem import FileSystemHelper

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """Represents a single compression history record.

    Attributes:
        id: Unique identifier (None for new entries)
        input_path: Path to input PDF file
        output_path: Path to compressed output file
        preset_name: Compression preset used (small/medium/high)
        original_size: Original file size in bytes
        compressed_size: Compressed file size in bytes
        compression_ratio: Percentage reduction (e.g., 45.5)
        duration: Compression time in seconds
        timestamp: When compression occurred
        success: Whether compression succeeded
        error_message: Error message if failed (None if successful)
    """

    id: Optional[int]
    input_path: str
    output_path: str
    preset_name: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    duration: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


class HistoryManager:
    """Manages compression history using SQLite database.

    Stores the last 50 compression operations with automatic cleanup.
    Database location: %APPDATA%/Squash/history/history.db

    Thread-safe: Creates new connection for each operation.
    """

    MAX_ENTRIES = 50

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize HistoryManager.

        Args:
            db_path: Path to SQLite database. If None, uses default AppData location.

        Raises:
            sqlite3.Error: If database cannot be initialized
        """
        if db_path is None:
            app_data = FileSystemHelper.get_app_data_dir()
            history_dir = app_data / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            db_path = history_dir / "history.db"

        self.db_path = db_path
        logger.info(f"Initializing HistoryManager with database: {self.db_path}")

        try:
            self._init_database()
            logger.info("HistoryManager initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize history database: {e}")
            raise

    def _init_database(self) -> None:
        """Create database schema if it doesn't exist.

        Creates the history table with indexes for efficient queries.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create history table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        input_path TEXT NOT NULL,
                        output_path TEXT NOT NULL,
                        preset_name TEXT NOT NULL,
                        original_size INTEGER NOT NULL,
                        compressed_size INTEGER NOT NULL,
                        compression_ratio REAL NOT NULL,
                        duration REAL NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT 1,
                        error_message TEXT
                    )
                    """
                )

                # Create indexes for performance
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON history(timestamp DESC)
                    """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_success
                    ON history(success)
                    """
                )

                conn.commit()
                logger.debug("Database schema created/verified")

        except sqlite3.Error as e:
            logger.error(f"Failed to create database schema: {e}")
            raise

    def add_entry(self, result: CompressionResult) -> bool:
        """Add a single compression result to history.

        Automatically enforces MAX_ENTRIES limit by deleting oldest entries.

        Args:
            result: CompressionResult from compression operation

        Returns:
            True if entry added successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert new entry
                cursor.execute(
                    """
                    INSERT INTO history (
                        input_path, output_path, preset_name,
                        original_size, compressed_size, compression_ratio,
                        duration, timestamp, success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.input_path,
                        result.output_path or "",
                        result.preset_used,
                        result.original_size,
                        result.compressed_size or 0,
                        result.reduction_percent or 0.0,
                        result.duration,
                        result.timestamp,
                        result.success,
                        result.error_message,
                    ),
                )

                # Enforce MAX_ENTRIES limit
                cursor.execute(
                    """
                    DELETE FROM history
                    WHERE id IN (
                        SELECT id FROM history
                        ORDER BY timestamp DESC
                        LIMIT -1 OFFSET ?
                    )
                    """,
                    (self.MAX_ENTRIES,),
                )

                conn.commit()
                logger.debug(f"Added history entry for: {result.input_path}")
                return True

        except sqlite3.Error as e:
            logger.error(f"Failed to add history entry: {e}")
            return False

    def add_entries(self, results: List[CompressionResult]) -> int:
        """Add multiple compression results to history in a single transaction.

        Args:
            results: List of CompressionResult objects

        Returns:
            Number of entries successfully added
        """
        if not results:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                rows = [
                    (
                        r.input_path,
                        r.output_path or "",
                        r.preset_used,
                        r.original_size,
                        r.compressed_size or 0,
                        r.reduction_percent or 0.0,
                        r.duration,
                        r.timestamp,
                        r.success,
                        r.error_message,
                    )
                    for r in results
                ]

                cursor.executemany(
                    """
                    INSERT INTO history (
                        input_path, output_path, preset_name,
                        original_size, compressed_size, compression_ratio,
                        duration, timestamp, success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )

                # Enforce MAX_ENTRIES limit once after all inserts
                cursor.execute(
                    """
                    DELETE FROM history
                    WHERE id IN (
                        SELECT id FROM history
                        ORDER BY timestamp DESC
                        LIMIT -1 OFFSET ?
                    )
                    """,
                    (self.MAX_ENTRIES,),
                )

                conn.commit()
                added_count = len(rows)
                logger.info(f"Added {added_count}/{len(results)} entries to history")
                return added_count

        except sqlite3.Error as e:
            logger.error(f"Failed to add history entries: {e}")
            return 0

    def get_recent(self, limit: int = 50) -> List[HistoryEntry]:
        """Get recent compression history.

        Args:
            limit: Maximum number of entries to return (default: 50)

        Returns:
            List of HistoryEntry objects, newest first
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM history
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

                entries = []
                for row in cursor.fetchall():
                    entries.append(
                        HistoryEntry(
                            id=row["id"],
                            input_path=row["input_path"],
                            output_path=row["output_path"],
                            preset_name=row["preset_name"],
                            original_size=row["original_size"],
                            compressed_size=row["compressed_size"],
                            compression_ratio=row["compression_ratio"],
                            duration=row["duration"],
                            timestamp=datetime.fromisoformat(row["timestamp"]),
                            success=bool(row["success"]),
                            error_message=row["error_message"],
                        )
                    )

                logger.debug(f"Retrieved {len(entries)} history entries")
                return entries

        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve history: {e}")
            return []

    def search(self, query: str) -> List[HistoryEntry]:
        """Search history by filename.

        Args:
            query: Search term (case-insensitive, searches input_path)

        Returns:
            List of matching HistoryEntry objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM history
                    WHERE input_path LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", self.MAX_ENTRIES),
                )

                entries = []
                for row in cursor.fetchall():
                    entries.append(
                        HistoryEntry(
                            id=row["id"],
                            input_path=row["input_path"],
                            output_path=row["output_path"],
                            preset_name=row["preset_name"],
                            original_size=row["original_size"],
                            compressed_size=row["compressed_size"],
                            compression_ratio=row["compression_ratio"],
                            duration=row["duration"],
                            timestamp=datetime.fromisoformat(row["timestamp"]),
                            success=bool(row["success"]),
                            error_message=row["error_message"],
                        )
                    )

                logger.debug(f"Search '{query}' found {len(entries)} entries")
                return entries

        except sqlite3.Error as e:
            logger.error(f"Failed to search history: {e}")
            return []

    def clear_history(self) -> bool:
        """Delete all history entries.

        Returns:
            True if history cleared successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM history")
                conn.commit()

                logger.info("History cleared successfully")
                return True

        except sqlite3.Error as e:
            logger.error(f"Failed to clear history: {e}")
            return False

    def cleanup_old(self, days: int = 30) -> int:
        """Delete history entries older than specified days.

        Args:
            days: Age threshold in days (default: 30)

        Returns:
            Number of entries deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    DELETE FROM history
                    WHERE timestamp < ?
                    """,
                    (cutoff_date,),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Deleted {deleted_count} entries older than {days} days")
                return deleted_count

        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup old entries: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from history.

        Returns:
            Dictionary with statistics:
                - total_files: Total files compressed
                - total_original_size: Sum of original sizes (bytes)
                - total_compressed_size: Sum of compressed sizes (bytes)
                - bytes_saved: Total bytes saved
                - average_ratio: Average compression ratio
                - success_rate: Percentage of successful compressions
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get aggregated statistics
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_files,
                        SUM(original_size) as total_original,
                        SUM(compressed_size) as total_compressed,
                        AVG(compression_ratio) as avg_ratio,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                    FROM history
                    """
                )

                row = cursor.fetchone()

                total_files = row[0] or 0
                total_original = row[1] or 0
                total_compressed = row[2] or 0
                avg_ratio = row[3] or 0.0
                successful = row[4] or 0

                bytes_saved = total_original - total_compressed
                success_rate = (successful / total_files * 100) if total_files > 0 else 0

                stats = {
                    "total_files": total_files,
                    "total_original_size": total_original,
                    "total_compressed_size": total_compressed,
                    "bytes_saved": bytes_saved,
                    "average_ratio": avg_ratio,
                    "success_rate": success_rate,
                }

                logger.debug(f"Calculated statistics: {stats}")
                return stats

        except sqlite3.Error as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {
                "total_files": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "bytes_saved": 0,
                "average_ratio": 0.0,
                "success_rate": 0.0,
            }

    def get_preset_statistics(self) -> Dict[str, Dict[str, float]]:
        """Calculate statistics grouped by preset.

        Returns:
            Dictionary mapping preset name to statistics:
            {
                "small": {
                    "avg_ratio": 65.2,
                    "count": 15,
                    "total_saved_mb": 45.3,
                    "avg_original_mb": 3.5,
                    "avg_compressed_mb": 1.2
                },
                ...
            }
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        preset_name,
                        AVG(compression_ratio) as avg_ratio,
                        COUNT(*) as count,
                        SUM(original_size - compressed_size) / (1024.0 * 1024.0) as total_saved_mb,
                        AVG(original_size) / (1024.0 * 1024.0) as avg_original_mb,
                        AVG(compressed_size) / (1024.0 * 1024.0) as avg_compressed_mb
                    FROM history
                    WHERE success = 1
                    GROUP BY preset_name
                    ORDER BY avg_ratio DESC
                    """
                )

                results = {}
                for row in cursor.fetchall():
                    results[row[0]] = {
                        "avg_ratio": round(row[1], 1),
                        "count": row[2],
                        "total_saved_mb": round(row[3], 1),
                        "avg_original_mb": round(row[4], 2),
                        "avg_compressed_mb": round(row[5], 2),
                    }

                logger.debug(f"Calculated preset statistics for {len(results)} presets")
                return results

        except sqlite3.Error as e:
            logger.error(f"Failed to get preset statistics: {e}")
            return {}

    def get_trend_data(self, days: int = 30) -> List[Tuple[datetime, float]]:
        """Get compression ratio trend for last N days.

        Args:
            days: Number of days to retrieve (default 30)

        Returns:
            List of (timestamp, compression_ratio) tuples sorted by time
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT timestamp, compression_ratio
                    FROM history
                    WHERE success = 1
                      AND timestamp >= ?
                    ORDER BY timestamp ASC
                    """,
                    (cutoff_date.isoformat(),),
                )

                results = []
                for row in cursor.fetchall():
                    timestamp = datetime.fromisoformat(row[0])
                    ratio = row[1]
                    results.append((timestamp, ratio))

                logger.debug(f"Retrieved trend data: {len(results)} points over {days} days")
                return results

        except sqlite3.Error as e:
            logger.error(f"Failed to get trend data: {e}")
            return []
