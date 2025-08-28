import logging

from .config import LOG_DIR, LOG_FILE


def get_logger(name: str) -> logging.Logger:
    """Return logger preferring file output, with safe fallback.

    Attempts to log to ``LOG_FILE``; if file I/O is not permitted (e.g. sandboxed
    test runner), falls back to a plain ``StreamHandler`` to stderr. Ensures we
    never crash tests due to logging setup.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        # LOG_DIR is created by config on import; handle permission errors here
        handler = logging.FileHandler(LOG_FILE)
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except Exception:  # pragma: no cover - permission or path errors
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger
