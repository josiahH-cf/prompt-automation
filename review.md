# Post-Implementation Review

Checklist against core principles and acceptance criteria.

- Modularity/Cohesion: Scanner (`services/hierarchy.py`) and FS ops (`services/hierarchy_fs.py`) separated; feature flags in `features.py`.
- Test-Driven: New tests cover listing, CRUD, security, cache invalidation, flat fallback, and logging.
- Minimal Surface Change: Existing flat APIs untouched; CLI adds opt-in flags.
- Deterministic Ordering: Folders alphabetical, templates by numeric prefix then name.
- Performance: Single-pass `os.scandir`; TTL cache; test injects time function for budget checks.
- Dependency Minimization: Standard library only.
- Observability: Structured INFO logs emitted for scans and CRUD.
- Security: Path normalization, traversal rejection, symlink dirs skipped; name regex enforced.
- File/function sizes: Files and functions kept under limits.

Follow-ups (optional):
- Consider OS-agnostic FS event watching (optional dep) for instant cache invalidation.
- Expose hierarchy adapter to GUI tree widget (drag/drop integration endpoint is `move_*`).

