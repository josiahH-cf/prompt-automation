from __future__ import annotations

"""Module entry point to allow `python -m prompt_automation`.

This provides an alternate launcher path on systems where the console
script shim is unavailable or misconfigured (e.g., PATH issues).
"""

from .cli.cli import main


if __name__ == "__main__":  # pragma: no cover - module entry convenience
    main()

