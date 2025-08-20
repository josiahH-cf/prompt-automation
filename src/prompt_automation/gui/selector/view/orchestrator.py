from __future__ import annotations

"""High level view orchestration for the selector GUI."""

from typing import List, Optional

from .preview import open_preview
from .overrides import manage_overrides
from .exclusions import edit_exclusions


class SelectorView:
    """Orchestrates selector subcomponents and business logic."""

    def __init__(self, service):
        self.service = service
        self.non_recursive = False
        self.multi_selected: List[dict] = []

    # --- Search ---------------------------------------------------------
    def toggle_recursive(self) -> None:
        """Toggle between recursive and non-recursive search modes."""
        self.non_recursive = not self.non_recursive

    def search(self, query: str):
        """Delegate search to the service respecting recursive toggle."""
        recursive = not self.non_recursive
        return self.service.template_search_service.search(query, recursive=recursive)

    # --- Multi-select ---------------------------------------------------
    def select_multi(self, template: dict) -> None:
        """Add or remove a template from the multi-selection list."""
        if template in self.multi_selected:
            self.multi_selected.remove(template)
        else:
            self.multi_selected.append(template)

    def finish_multi(self) -> Optional[dict]:
        """Combine selected templates into a synthetic multi template."""
        combined = self.service.multi_select_service.merge_templates(self.multi_selected)
        self.multi_selected = []
        return combined

    # --- Dialog wrappers ------------------------------------------------
    def open_preview(self, parent, entry) -> None:
        open_preview(parent, entry)

    def manage_overrides(self, root) -> None:
        manage_overrides(root, self.service.overrides_service)

    def edit_exclusions(self, root) -> None:
        edit_exclusions(root, self.service.exclusions_service)

    # --- GUI open placeholder -------------------------------------------
    def open(self, embedded: bool = False, parent=None):  # pragma: no cover - GUI heavy
        """Placeholder for full GUI open method."""
        return None
