"""Centralized logging configuration for Milestone 2.

Every module obtains its logger via :func:`get_logger` instead of calling
``logging.basicConfig`` independently. This guarantees a single, consistent
log format and a single rotating file handler across the whole milestone,
which matters for audit readiness (Farida's compliance audit in Milestone 4
depends on complete, consistent logs).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(logs_dir: Path, file_name: str, level: str = "INFO",
                       max_bytes: int = 5_242_880, backup_count: int = 3) -> None:
    """Configure the root logger once with a console and rotating file handler.

    Safe to call multiple times; only the first call takes effect, which
    lets every module call it defensively at import time without producing
    duplicate log lines.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / file_name

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Modules obtain a logger at import time via get_logger(), which may have
    # already attached a basicConfig() fallback handler to the root logger
    # before this explicit setup ran. Clear those first so handlers are never
    # duplicated (which otherwise doubles every console log line).
    root_logger.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring logging with defaults if needed.

    If :func:`configure_logging` has not yet been called explicitly (e.g. in
    a notebook or ad-hoc script), this falls back to a console-only logger so
    modules never fail purely due to missing logging setup.
    """
    if not _CONFIGURED:
        logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)
    return logging.getLogger(name)
