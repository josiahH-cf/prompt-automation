import logging

from .config import LOG_DIR, LOG_FILE


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
