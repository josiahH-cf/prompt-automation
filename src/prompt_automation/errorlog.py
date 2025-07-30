import logging
from pathlib import Path

LOG_DIR = Path.home() / ".prompt-automation" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "error.log"


def get_logger(name: str) -> logging.Logger:
    """Return logger writing to ``error.log``."""
    logger = logging.getLogger(name)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(LOG_FILE) for h in logger.handlers):
        handler = logging.FileHandler(LOG_FILE)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
