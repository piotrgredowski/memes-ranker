"""Logging configuration for memes-ranker application.

This module provides centralized logging setup using structlog with file rotation.
"""

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable
import structlog
from fastapi import Request


def setup_logging(
    logs_dir: str = "logs",
    json_log_file: str = "app_json.log",
    text_log_file: str = "app.log",
    frontend_json_log: str = "frontend_json.log",
    frontend_text_log: str = "frontend.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure structlog with dual file outputs and console output.

    Args:
        logs_dir: Directory to store log files
        json_log_file: Name of the JSON structured log file
        text_log_file: Name of the human-readable log file
        frontend_json_log: Name of the frontend JSON log file
        frontend_text_log: Name of the frontend text log file
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        console_level: Logging level for console output
        file_level: Logging level for file output
    """
    # Create logs directory
    logs_path = Path(logs_dir)
    logs_path.mkdir(exist_ok=True)

    # Configure JSON file logging with rotation
    json_file_handler = RotatingFileHandler(
        logs_path / json_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    json_file_handler.setLevel(file_level)

    # Configure human-readable file logging with rotation
    text_file_handler = RotatingFileHandler(
        logs_path / text_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    text_file_handler.setLevel(file_level)

    # Configure console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)

    # Create formatters
    json_formatter = logging.Formatter("%(message)s")  # Raw message for JSON logs
    text_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Set formatters
    json_file_handler.setFormatter(json_formatter)
    text_file_handler.setFormatter(text_formatter)
    console_handler.setFormatter(console_formatter)

    # Configure structlog for JSON output
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging with both handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(min(console_level, file_level))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Add our handlers
    root_logger.addHandler(json_file_handler)
    root_logger.addHandler(text_file_handler)
    root_logger.addHandler(console_handler)

    # Silence noisy third-party loggers
    _silence_noisy_loggers()

    # Setup exception logging for uncaught exceptions
    _setup_exception_logging()


def _silence_noisy_loggers() -> None:
    """Silence overly verbose third-party loggers."""
    noisy_loggers = [
        "aiosqlite",
        "sqlite3",
        "urllib3.connectionpool",
        "httpx",
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _setup_exception_logging() -> None:
    """Setup logging for uncaught exceptions."""

    def handle_exception(exc_type, exc_value, exc_traceback):
        """Log uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log KeyboardInterrupt (Ctrl+C)
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Use the root logger to ensure it goes through all handlers
        root_logger = logging.getLogger()
        root_logger.error(
            "Uncaught exception occurred",
            exc_info=(exc_type, exc_value, exc_traceback),
            extra={
                "exception_type": exc_type.__name__,
                "exception_message": str(exc_value),
            },
        )

        # Also try with structlog for structured output
        try:
            logger = get_logger("uncaught_exceptions")
            logger.error(
                "Uncaught exception",
                exception_type=exc_type.__name__,
                exception_message=str(exc_value),
                traceback="".join(
                    __import__("traceback").format_exception(
                        exc_type, exc_value, exc_traceback
                    )
                ),
            )
        except Exception:
            # Fallback if structlog fails
            pass

    # Set the custom exception handler
    sys.excepthook = handle_exception


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Logger name, defaults to caller's module name

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


async def log_exceptions_middleware(request: Request, call_next: Callable):
    """Middleware to log all exceptions including Jinja template errors."""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger = get_logger("middleware_exceptions")

        # Log the exception with full context
        logger.error(
            "Exception in request processing",
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            traceback=traceback.format_exc(),
            request_method=request.method,
            request_url=str(request.url),
            request_headers=dict(request.headers),
        )

        # Re-raise the exception so FastAPI can handle it normally
        raise exc


def setup_fastapi_error_logging(app):
    """Add error logging middleware to FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.middleware("http")(log_exceptions_middleware)


def setup_frontend_logging(
    logs_dir: str = "logs",
    frontend_json_log: str = "frontend_json.log",
    frontend_text_log: str = "frontend.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    file_level: int = logging.INFO,
) -> tuple[logging.Logger, logging.Logger]:
    """Setup dedicated frontend logging handlers.

    Args:
        logs_dir: Directory to store log files
        frontend_json_log: Name of the frontend JSON log file
        frontend_text_log: Name of the frontend text log file
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        file_level: Logging level for file output

    Returns:
        Tuple of (json_logger, text_logger)
    """
    # Create logs directory
    logs_path = Path(logs_dir)
    logs_path.mkdir(exist_ok=True)

    # Frontend JSON logger
    frontend_json_logger = logging.getLogger("frontend_json")
    frontend_json_logger.setLevel(file_level)
    frontend_json_logger.handlers.clear()

    json_handler = RotatingFileHandler(
        logs_path / frontend_json_log,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    json_handler.setLevel(file_level)
    json_handler.setFormatter(logging.Formatter("%(message)s"))
    frontend_json_logger.addHandler(json_handler)

    # Frontend text logger
    frontend_text_logger = logging.getLogger("frontend_text")
    frontend_text_logger.setLevel(file_level)
    frontend_text_logger.handlers.clear()

    text_handler = RotatingFileHandler(
        logs_path / frontend_text_log,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    text_handler.setLevel(file_level)
    text_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    frontend_text_logger.addHandler(text_handler)

    return frontend_json_logger, frontend_text_logger


def get_frontend_loggers() -> tuple[logging.Logger, logging.Logger]:
    """Get frontend loggers.

    Returns:
        Tuple of (json_logger, text_logger)
    """
    return logging.getLogger("frontend_json"), logging.getLogger("frontend_text")
