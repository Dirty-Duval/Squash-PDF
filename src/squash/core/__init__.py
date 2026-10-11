"""Core compression engine and processing logic."""

from .compression import CompressionEngine, CompressionResult
from .ghostscript import GhostscriptError, GhostscriptWrapper, detect_ghostscript
from .presets import Preset, PresetManager
from .batch import BatchProcessor, BatchProgress, BatchResult, resolve_output_path

__all__ = [
    "CompressionEngine",
    "CompressionResult",
    "GhostscriptError",
    "GhostscriptWrapper",
    "detect_ghostscript",
    "PresetManager",
    "Preset",
    "BatchProcessor",
    "BatchProgress",
    "BatchResult",
    "resolve_output_path",
]
