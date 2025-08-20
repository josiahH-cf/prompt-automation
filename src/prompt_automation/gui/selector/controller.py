"""High level orchestration between selector view and services."""
from __future__ import annotations

from typing import Optional
from types import SimpleNamespace

from . import view
from ...services import (
    template_search as template_search_service,
    multi_select as multi_select_service,
    overrides as overrides_service,
    exclusions as exclusions_service,
)
from ...config import PROMPTS_DIR


# Bundle the individual services for injection into the view layer.  The
# ``open_template_selector`` shim only relies on ``PROMPTS_DIR`` and
# ``load_template_by_relative`` but we expose the full set so that
# ``SelectorView`` can access them when instantiated directly (e.g. tests).
service = SimpleNamespace(
    template_search_service=template_search_service,
    multi_select_service=multi_select_service,
    overrides_service=overrides_service,
    exclusions_service=exclusions_service,
    PROMPTS_DIR=PROMPTS_DIR,
    load_template_by_relative=template_search_service.load_template_by_relative,
)


def open_template_selector() -> Optional[dict]:
    """Open the template selector GUI and return chosen template data."""
    return view.open_template_selector(service)


__all__ = [
    "open_template_selector",
    "service",
]

