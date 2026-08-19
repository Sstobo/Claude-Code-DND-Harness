#!/usr/bin/env python3
"""
Centralized logging configuration for GM modules.
Provides consistent logging across all Python modules.
"""

import logging
import sys
import os
from typing import Optional


def setup_logging(level: Optional[int] = None, name: str = 'dm') -> logging.Logger:
    """Configure logging for GM modules.

    Args:
        level: Logging level. Defaults to INFO, or reads from DM_LOG_LEVEL env var.
        name: Logger name. Defaults to 'dm'.

    Returns:
        Configured logger instance.
    """
    # Get level from environment if not specified
    if level is None:
        env_level = os.environ.get('DM_LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, env_level, logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '[%(levelname)s] %(name)s: %(message)s'
    )

    # Create handler for stderr
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        module_name: Name of the module (e.g., 'npc_manager', 'session_manager')

    Returns:
        Logger instance for the module.
    """
    return logging.getLogger(f'dm.{module_name}')


# Initialize root logger on import
_root_logger = setup_logging()
