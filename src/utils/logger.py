"""
Structured Logger Module

Configures structlog for JSON-formatted structured logging with correlation IDs.
All components must use this logger for consistent multi-agent tracing.

Example Usage:
    from src.utils.logger import get_logger

    # Get logger with context
    logger = get_logger(
        correlation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        phase="professor_filter",
        component="professor_filter_agent"
    )

    # Log with context automatically included
    logger.info("Starting professor filtering", total_professors=100)
    logger.warning("Low confidence match", professor_name="Dr. Smith", confidence=68.5)
    logger.error("LLM call failed", error="Timeout after 30s")

Log Levels:
    - DEBUG: Detailed execution flow, LLM prompts/responses (verbose)
    - INFO: Phase progress, batch completion, checkpoints saved
    - WARNING: Missing data, skipped items, low-confidence matches
    - ERROR: Exceptions, failed retries, resource access failures
    - CRITICAL: Unrecoverable failures requiring user intervention
"""

import logging
import sys
import uuid
from pathlib import Path
from typing import Optional
import structlog
from structlog.types import BindableLogger, EventDict, WrappedLogger


def mask_credentials(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Processor to mask sensitive credentials in log output.

    Args:
        logger: Logger instance
        method_name: Logging method name
        event_dict: Event dictionary to process

    Returns:
        Event dictionary with masked credentials

    Masks:
        - password, api_key, token, secret, credential, auth fields
        - Replaces values with "***MASKED***"
        - Uses word boundary matching to avoid false positives
    """
    sensitive_fields = {"password", "api_key", "token", "secret", "credential", "auth"}

    for key in list(event_dict.keys()):
        key_lower = key.lower()
        # Check for exact match or word boundary match (separated by underscore/hyphen)
        for sensitive in sensitive_fields:
            if (
                key_lower == sensitive
                or key_lower.endswith(f"_{sensitive}")
                or key_lower.endswith(f"-{sensitive}")
                or key_lower.startswith(f"{sensitive}_")
                or key_lower.startswith(f"{sensitive}-")
            ):
                event_dict[key] = "***MASKED***"
                break

    return event_dict


def configure_logging(
    log_file: str = "logs/lab-finder.log", log_level: str = "INFO"
) -> None:
    """
    Configure structlog with JSON output and file logging.

    Args:
        log_file: Path to log file (default: "logs/lab-finder.log")
        log_level: Logging level (default: "INFO")

    Log Format (JSON):
        {
            "timestamp": "2024-10-06T10:30:45Z",
            "level": "INFO",
            "correlation_id": "a1b2c3d4-...",
            "phase": "professor_filter",
            "component": "professor_filter_agent",
            "message": "Starting professor filtering",
            "total_professors": 100
        }
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    # Configure structlog processors
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            mask_credentials,  # Mask sensitive data
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(
    correlation_id: Optional[str] = None,
    phase: Optional[str] = None,
    component: Optional[str] = None,
) -> BindableLogger:
    """
    Get structured logger with bound context.

    Args:
        correlation_id: Correlation ID for request tracing (generates UUID if not provided)
        phase: Pipeline phase (e.g., "professor_filter", "lab_intelligence")
        component: Component name (e.g., "professor_filter_agent", "checkpoint_manager")

    Returns:
        BoundLogger with correlation_id, phase, and component bound to context

    Example:
        logger = get_logger(
            correlation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            phase="professor_filter",
            component="professor_filter_agent"
        )
        logger.info("Processing batch", batch_id=3, total_items=20)

        # Output (JSON):
        # {
        #   "timestamp": "2024-10-06T10:30:45Z",
        #   "level": "info",
        #   "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        #   "phase": "professor_filter",
        #   "component": "professor_filter_agent",
        #   "message": "Processing batch",
        #   "batch_id": 3,
        #   "total_items": 20
        # }
    """
    # Generate correlation ID if not provided
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    # Get base logger
    logger = structlog.get_logger()

    # Bind context
    if correlation_id:
        logger = logger.bind(correlation_id=correlation_id)
    if phase:
        logger = logger.bind(phase=phase)
    if component:
        logger = logger.bind(component=component)

    return logger


# Initialize logging on module import with default settings
configure_logging()
