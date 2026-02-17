"""
Structured Logging Configuration
结构化日志配置

Provides JSON-formatted structured logging for better log aggregation and analysis.
提供JSON格式的结构化日志，便于日志聚合和分析。
"""

import logging
import sys
try:
    # python-json-logger >= 3.x
    from pythonjsonlogger.json import JsonFormatter
except Exception:  # Backward compatibility for older versions
    from pythonjsonlogger import jsonlogger as _jsonlogger
    JsonFormatter = _jsonlogger.JsonFormatter

try:
    import structlog
except Exception:  # Optional in some local/dev test setups
    structlog = None


def configure_logging(log_level: str = "INFO", json_logs: bool = True):
    """
    Configure structured logging for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
    """

    # Set logging level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )

    if json_logs:
        # Configure JSON logging
        logHandler = logging.StreamHandler()
        formatter = JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        logHandler.setFormatter(formatter)

        # Apply to root logger
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(logHandler)

    if structlog is None:
        logging.getLogger(__name__).warning(
            "structlog not installed; falling back to stdlib logging only"
        )
        return

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__):
    """
    Get a structured logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    if structlog is None:
        return logging.getLogger(name)
    return structlog.get_logger(name)
