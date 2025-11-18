"""
Logging utilities for ingestion pipeline.
Outputs to both stdout and rotating log file.
"""

import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "ingestion", log_dir: Path = None) -> logging.Logger:
    """
    Set up a logger that outputs to both stdout and a rotating log file.
    
    Args:
        name: Logger name
        log_dir: Directory for log files (defaults to /app/logs or ./logs)
    
    Returns:
        Configured logger instance
    """
    # Determine log directory
    if log_dir is None:
        log_dir = Path(os.getenv('LOG_DIR', '/app/logs'))
        # Fallback to local logs/ if /app/logs doesn't exist
        if not log_dir.exists():
            log_dir = Path('logs')
    
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Format for log messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating, max 10MB per file, keep 5 backups)
    log_file = log_dir / f"{name}.log"
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

