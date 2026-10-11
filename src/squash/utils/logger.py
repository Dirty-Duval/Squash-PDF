"""
Logging configuration and utilities.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

APP_LOGGER_NAME = "squash"

_CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"


def _coerce_level(level: Union[int, str]) -> int:
    """Accept an int or a level name and return the numeric level (INFO on error)."""
    if isinstance(level, int):
        return level
    resolved = logging.getLevelName(str(level).upper())
    return resolved if isinstance(resolved, int) else logging.INFO


def setup_logger(
    name: str = APP_LOGGER_NAME,
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """Configure the application logger.

    Safe to call more than once: existing handlers are replaced rather than
    duplicated. In a windowed (PyInstaller ``console=False``) build there is
    no stdout, so the console handler is skipped.

    Args:
        name: Logger name. Module loggers use ``logging.getLogger(__name__)``
            and inherit from this one via the ``squash.`` prefix.
        level: Logging level (int or name such as ``"DEBUG"``).
        log_file: Optional rotating log file path.

    Returns:
        The configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(_coerce_level(level))

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    if sys.stdout is not None:
        try:  # console code pages (cp1252) cannot encode arrows; never crash on them
            sys.stdout.reconfigure(errors="replace")
        except Exception:
            pass
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(_CONSOLE_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(console_handler)

    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        logger.addHandler(file_handler)

    return logger


def set_log_level(level: Union[int, str], name: str = APP_LOGGER_NAME) -> None:
    """Change the application log level at runtime (used by the Settings dialog)."""
    logging.getLogger(name).setLevel(_coerce_level(level))


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance (thin wrapper kept for backwards compatibility)."""
    return logging.getLogger(name)
