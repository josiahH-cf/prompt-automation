"""Central configuration paths for prompt-automation."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

# Environment variable names
ENV_PROMPTS = "PROMPT_AUTOMATION_PROMPTS"
ENV_DB = "PROMPT_AUTOMATION_DB"
ENV_LOG_DIR = "PROMPT_AUTOMATION_LOG_DIR"
ENV_HOME = "PROMPT_AUTOMATION_HOME"


def _candidate_prompt_paths() -> List[Path]:
    """Return potential locations for packaged or user prompts."""
    return [
        # Development structure (3 levels up from this file)
        Path(__file__).resolve().parent.parent.parent / "prompts" / "styles",
        # Packaged installation - data files location
        Path(__file__).resolve().parent / "prompts" / "styles",
        # Alternative package location (in site-packages)
        Path(__file__).resolve().parent.parent / "prompts" / "styles",
        # pipx virtual environment location
        Path(__file__).resolve().parent.parent.parent / "Lib" / "prompts" / "styles",
        # User locations
        Path.home() / ".prompt-automation" / "prompts" / "styles",
        Path.home() / ".local" / "share" / "prompt-automation" / "prompts" / "styles",
        # System-wide locations
        Path("/usr/local/share/prompt-automation/prompts/styles"),
        Path("C:/ProgramData/prompt-automation/prompts/styles"),
    ]


PROMPTS_SEARCH_PATHS = _candidate_prompt_paths()


def _find_prompts_dir() -> Path:
    env_path = os.environ.get(ENV_PROMPTS)
    if env_path:
        env_prompts = Path(env_path).expanduser()
        if env_prompts.exists():
            return env_prompts
    for location in PROMPTS_SEARCH_PATHS:
        if location.exists() and location.is_dir():
            return location
    return PROMPTS_SEARCH_PATHS[0]


PROMPTS_DIR = _find_prompts_dir()

DEFAULT_HOME = Path.home() / ".prompt-automation"
HOME_DIR = Path(os.environ.get(ENV_HOME, DEFAULT_HOME))
HOME_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = Path(os.environ.get(ENV_LOG_DIR, HOME_DIR / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "error.log"

DB_PATH = Path(os.environ.get(ENV_DB, HOME_DIR / "usage.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
