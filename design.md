# Hierarchical Templates — Design

## Overview
Introduce a filesystem-backed hierarchical template browser while preserving the existing flat listing APIs. The design separates scanning/caching from mutation operations and from presentation, enabling reuse in CLI and GUI.

## Components
- TemplateHierarchyScanner
  - Input: `root: Path` (PROMPTS_DIR)
  - Responsibilities:
    - Single-pass directory traversal (`os.scandir`) building an in-memory tree.
    - Sorting: folders alphabetical, then templates by numeric prefix (if any) else lexical.
    - Security: do not follow symlinks; skip or reject symlink dirs.
    - Caching: TTL-based with composite mtime signature; explicit `invalidate()`.
    - Observability: logs structured events (`hierarchy.scan.*`).
  - Output: `HierarchyNode` dataclass-like dicts with fields: `type`, `name`, `relpath`, and `children` (for folders).

- TemplateFSService
  - Input: `root: Path`, optional `on_change` callback (to invalidate scanner cache).
  - Responsibilities:
    - CRUD operations for folders and templates with validation.
    - Path normalization and sandboxing under `root` (reject `..`, non-matching prefix, symlinks).
    - Name validation using `^[A-Za-z0-9._-]+$` for folder names; `.json` enforced for templates; stems validated.
    - Observability: INFO logs with `event`, `path`, `ok/error`, counters (`hierarchy.crud.*`).
  - Errors: dedicated exceptions with error codes (e.g., `E_NAME_EXISTS`, `E_INVALID_NAME`, `E_UNSAFE_PATH`).

- Feature Flag
  - `features.is_hierarchy_enabled()` reads from env `PROMPT_AUTOMATION_HIERARCHICAL_TEMPLATES` or `Settings/settings.json` key `hierarchical_templates` (default false).
  - GUI/CLI can inspect and choose tree vs flat behavior.

## Public Interfaces (docsignatures)

```python
class TemplateHierarchyScanner:
    def __init__(self, root: Path, cache_ttl: int = 5, time_fn: Callable[[], float] | None = None): ...
    def scan(self) -> dict:  # returns { 'type': 'folder', 'name': '', 'relpath': '', 'children': [...] }
    def invalidate(self) -> None: ...
    def list_flat(self) -> list[Path]: ...  # convenience, respects root and skips settings.json

class TemplateFSService:
    def create_folder(self, rel: str) -> Path: ...
    def rename_folder(self, rel: str, new_name: str) -> Path: ...
    def move_folder(self, src_rel: str, dst_parent_rel: str) -> Path: ...
    def delete_folder(self, rel: str, recursive: bool = False) -> None: ...
    def create_template(self, rel: str, payload: dict | None = None) -> Path: ...
    def rename_template(self, rel: str, new_name: str) -> Path: ...
    def move_template(self, src_rel: str, dst_rel: str) -> Path: ...
    def duplicate_template(self, src_rel: str, dst_rel: str | None = None) -> Path: ...
    def delete_template(self, rel: str) -> None: ...
```

## Ordering Rules
- Folders: `sorted(name.lower())` ascending.
- Templates: first by numeric prefix (int from leading digits in filename), ascending; then lexicographic on filename.

## Performance
- Scans use `os.scandir` breadth-first, collecting metadata in one pass.
- Cache TTL defaults to 5 seconds; invalidation called on CRUD to avoid waiting TTL.
- `time_fn` injectable for tests to mock elapsed time and log `duration_ms` deterministically.

## Observability
- Use `errorlog.get_logger` to emit structured lines like:
  `{"event": "hierarchy.scan.success", "duration_ms": 42, "template_count": 120, "folder_count": 18}`
- Similar events for CRUD: `hierarchy.crud.success`/`error` including `op` and `path`.

## Security
- Normalize paths with `Path.resolve()`; assert `resolved_path.is_relative_to(root)` (polyfill for older Python).
- Reject `..` segments and symlinks.
- Explicit regex validation for names; deny if invalid.

## GUI Integration (Adapter)
- Not implementing UI widgets here. Provide the `scan()` tree model suitable for a tree view.
- Drag/drop maps to `move_template`/`move_folder` operations.

## Rollback
- If flag disabled, GUI continues using existing flat list. CLI defaults unchanged; `--tree` is opt-in.

