"""Core compression engine and processing logic."""

from .compression import CompressionEngine, CompressionResult
from .presets import PresetManager, Preset
from .batch import BatchProcessor, BatchResult

__all__ = [
    "CompressionEngine",
    "CompressionResult",
    "PresetManager",
    "Preset",
    "BatchProcessor",
    "BatchResult",
]
