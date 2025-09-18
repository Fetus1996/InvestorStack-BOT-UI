import logging
import sys
from datetime import datetime
import json

class JSONFormatter(logging.Formatter):
    """JSON log formatter."""

    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'message': record.getMessage(),
        }
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)
        return json.dumps(log_obj)


def setup_logger(name: str = "grid_bot", level: int = logging.INFO) -> logging.Logger:
    """Set up logger with JSON formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logger()