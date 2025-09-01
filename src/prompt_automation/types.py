from __future__ import annotations

from typing import NotRequired, TypedDict, List, Dict, Any


class Placeholder(TypedDict, total=False):
    """Placeholder entry in a template."""

    name: str
    label: NotRequired[str]
    default: NotRequired[str]
    multiline: NotRequired[bool]
    format: NotRequired[str]
    # Extended types and display options
    type: NotRequired[str]  # e.g. 'file', 'reminder', 'link'
    url: NotRequired[str]
    href: NotRequired[str]
    link_text: NotRequired[str]


class Template(TypedDict, total=False):
    """Prompt template structure."""

    id: int
    title: str
    style: str
    template: List[str]
    placeholders: List[Placeholder]
    role: NotRequired[str]
    schema: NotRequired[int]
    metadata: NotRequired[Dict[str, Any]]


__all__ = ["Template", "Placeholder"]
