"""Data model helpers for template browsing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
from ...menus import PROMPTS_DIR
from ...renderer import validate_template, load_template

@dataclass
class TemplateEntry:
    path: Path
    data: Dict[str, Any]

@dataclass
class ListingItem:
    type: str  # 'dir' | 'template' | 'up' | 'empty'
    path: Optional[Path] = None
    template: Optional[TemplateEntry] = None
    display: str = ""

class BrowserState:
    def __init__(self, root: Path):
        self.root = root
        self.current = root
        self.items: List[ListingItem] = []
        # Pre-built recursive index (list of ListingItem w/ template attached)
        self._indexed: List[ListingItem] = []
        self._indexed_built: bool = False

    def build(self) -> None:
        self.items.clear()
        # First collect dirs and templates
        for child in sorted([p for p in self.current.iterdir() if p.is_dir()]):
            if child.name.lower() == "settings":
                continue
            self.items.append(ListingItem(type="dir", path=child, display=child.name+"/"))
        for child in sorted([p for p in self.current.iterdir() if p.is_file() and p.suffix.lower()==".json"]):
            if child.name.lower()=="settings.json":
                continue
            try:
                data = load_template(child)
                if not validate_template(data):
                    continue
                self.items.append(ListingItem(type="template", path=child, template=TemplateEntry(child, data), display=child.name))
            except Exception:
                continue
        # Append navigation 'up' control at the bottom (requested UX)
        if self.current != self.root:
            self.items.append(ListingItem(type="up", display="[..]"))
        if not self.items:
            self.items.append(ListingItem(type="empty", display="<empty>"))

    def enter(self, item: ListingItem) -> Optional[TemplateEntry]:
        if item.type == 'up':
            self.current = self.current.parent if self.current != self.root else self.root
            self.build(); return None
        if item.type == 'dir' and item.path:
            self.current = item.path; self.build(); return None
        if item.type == 'template' and item.template:
            return item.template
        return None

    def breadcrumb(self) -> str:
        if self.current == self.root:
            return str(self.root)
        return f"{self.root.name}/{self.current.relative_to(self.root)}"

    def filter(self, query: str) -> List[ListingItem]:
        if not query:
            return self.items
        q = query.lower()
        return [it for it in self.items if it.display.lower().find(q) != -1 or (it.template and str(it.path).lower().find(q) != -1)]

    # --- Recursive content-aware search ---------------------------------
    def _ensure_index(self) -> None:
        if self._indexed_built:
            return
        # Traverse all templates once; build ListingItems with searchable blobs
        indexed: List[ListingItem] = []
        for path in sorted(self.root.rglob("*.json")):
            if path.name.lower() == "settings.json":
                continue
            try:
                data = load_template(path)
                if not validate_template(data):
                    continue
                entry = TemplateEntry(path, data)
                # display uses relative path for clarity
                rel = path.relative_to(self.root)
                indexed.append(ListingItem(
                    type="template",
                    path=path,
                    template=entry,
                    display=str(rel),
                ))
            except Exception:
                continue
        self._indexed = indexed
        self._indexed_built = True

    def search(self, query: str) -> List[ListingItem]:
        """Recursive search across all templates (path, title, placeholders, body).

        Implements simple AND token matching: all whitespace-separated tokens
        must appear (case-insensitive) somewhere in the aggregated text blob.
        """
        q = query.strip()
        if not q:
            return []
        self._ensure_index()
        tokens = [t.lower() for t in q.split() if t.strip()]
        if not tokens:
            return []
        results: List[ListingItem] = []
        for item in self._indexed:
            data = item.template.data if item.template else {}
            # Build blob lazily; keep it lightweight
            body_lines = data.get("template", []) if isinstance(data.get("template"), list) else []
            placeholders = data.get("placeholders", []) if isinstance(data.get("placeholders"), list) else []
            ph_names = [p.get("name", "") for p in placeholders if isinstance(p, dict)]
            title = data.get("title", "")
            blob_parts = [item.display.lower(), title.lower(), "\n".join(body_lines).lower(), " ".join(ph_names).lower()]
            blob = " \n".join(blob_parts)
            if all(tok in blob for tok in tokens):
                results.append(item)
        return results


def create_browser_state() -> BrowserState:
    return BrowserState(PROMPTS_DIR)

__all__ = ["TemplateEntry", "ListingItem", "BrowserState", "create_browser_state"]
