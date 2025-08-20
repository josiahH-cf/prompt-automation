"""Frame builders for the single-window GUI."""

from .collect import build as build_collect_frame
from .review import build as build_review_frame
from .select import build as build_select_frame

__all__ = [
    "build_collect_frame",
    "build_review_frame",
    "build_select_frame",
]
