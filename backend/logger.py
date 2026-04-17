#!/usr/bin/env python3
"""
Structured logging for RO-ED AI Agent.
Wraps Python logging with JSON format for production monitoring.
"""

import logging
import json
import sys
from datetime import datetime

# Configure root logger
logger = logging.getLogger("ro-ed")
logger.setLevel(logging.INFO)

# Console handler with structured format
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "time": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        return json.dumps(log_entry)


# Use simple format in development, structured in production
import os
if os.environ.get("LOG_FORMAT") == "json":
    handler.setFormatter(StructuredFormatter())
else:
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
        datefmt="%H:%M:%S"
    ))

logger.addHandler(handler)


def log_step(step: int, name: str, status: str, detail: str = "", **kwargs):
    """Log a pipeline step event."""
    msg = f"Step {step}: {name} [{status}]"
    if detail:
        msg += f" — {detail}"
    if kwargs:
        msg += f" | {kwargs}"
    logger.info(msg)


def log_fix(rule_id: str, field: str, old_value, new_value):
    """Log a fixer rule application."""
    logger.info(f"Fix [{rule_id}] {field}: {old_value} → {new_value}")


def log_error(message: str, **kwargs):
    """Log an error."""
    logger.error(f"{message} | {kwargs}" if kwargs else message)


def log_cost(step: str, cost: float, model: str = ""):
    """Log API cost."""
    logger.info(f"Cost: ${cost:.4f} ({step}) model={model}")
