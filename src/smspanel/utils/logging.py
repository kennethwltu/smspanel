"""Standardized logging utilities."""

import logging
import uuid
from typing import Any, Optional

from flask import Flask, Request


# Request ID context variable
_request_id_context: Optional[str] = None


def get_request_id() -> str:
    """Get current request ID or return N/A if not set."""
    global _request_id_context
    return _request_id_context or "N/A"


def set_request_id(request_id: str) -> None:
    """Set request ID for context."""
    global _request_id_context
    _request_id_context = request_id


def clear_request_id() -> None:
    """Clear request ID context (useful for test cleanup)."""
    global _request_id_context
    _request_id_context = None


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


def setup_app_logging(app: Flask) -> None:
    """Configure application-wide logging.

    Args:
        app: Flask application instance.
    """
    log_level = app.config.get("LOG_LEVEL", logging.INFO)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s"

    # Create request ID filter
    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            record.request_id = get_request_id()
            return True

    # Configure handler with formatter
    handler = logging.StreamHandler()
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    # Get root logger and configure
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Configure app-specific logger
    app_logger = logging.getLogger("smspanel")
    app_logger.setLevel(log_level)


def log_error(
    error: Exception,
    context: Optional[dict[str, Any]] = None,
    level: int = logging.ERROR,
    exc_info: bool = True,
) -> None:
    """Log an error with standardized format.

    Args:
        error: The exception to log.
        context: Optional context dictionary with additional details.
        level: Logging level (default: ERROR).
        exc_info: Include traceback (default: True).
    """
    logger = logging.getLogger("smspanel")

    extra = {"request_id": get_request_id()}

    if exc_info:
        logger.log(level, f"Error: {type(error).__name__}: {error}", extra=extra, exc_info=True)
    else:
        logger.log(level, f"Error: {type(error).__name__}: {error}", extra=extra)


def log_request(request: Request, status_code: int, duration_ms: float) -> None:
    """Log an HTTP request with standardized format.

    Args:
        request: Flask request object.
        status_code: HTTP status code of response.
        duration_ms: Request duration in milliseconds.
    """
    logger = logging.getLogger("smspanel")

    extra = {
        "request_id": get_request_id(),
        "method": request.method,
        "path": request.path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "ip": request.remote_addr,
    }

    if status_code >= 400:
        logger.warning(
            f"Request failed: {request.method} {request.path} -> {status_code}", extra=extra
        )
    else:
        logger.info(f"Request: {request.method} {request.path} -> {status_code}", extra=extra)
