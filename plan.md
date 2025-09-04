# Hierarchical Template Folder Structure — Plan

This plan follows phased delivery with tests-first, minimal API surface changes, and a feature flag for safe rollout.

## Scope Summary
- Add a physical on-disk hierarchy scanner with caching and safe CRUD operations.
- Provide a CLI tree listing behind `--tree` flag; keep existing flat `--list` intact.
- Expose a feature flag to enable hierarchical behavior in UI without breaking existing flows.
- Ensure security (no traversal/symlink escape), observability (structured logs, counters), and tests.

## Affected Modules
- New: `prompt_automation/services/hierarchy.py` (scanner + cache + view model helpers)
- New: `prompt_automation/services/hierarchy_fs.py` (filesystem CRUD ops)
- New: `prompt_automation/features.py` (feature flags; reads env and settings.json)
- Updated: `prompt_automation/cli/controller.py` (CLI flags `--tree`, `--flat` handling for `--list`)
- Docs: README, CHANGELOG

## Acceptance Criteria Mapping
- Rendering hierarchy: `TemplateHierarchyScanner.scan()` returns nested structure reflecting `PROMPTS_DIR`.
- CRUD: `TemplateFSService` supports create/rename/move/delete for folders and templates; persists to FS; validates names.
- Drag & drop: covered via `move_*` ops; integration point exposed for GUI to call.
- Backward compatibility: Flat list preserved (`services/template_search.py` untouched); CLI `--list` behavior unchanged unless `--tree` provided; feature flag default off.
- Performance: Single-pass `os.scandir` walk; caching with TTL; tests mock timing to assert budgets.
- Caching: TTL-based cache with explicit invalidation on CRUD; optional manual `invalidate()`.
- Security: Normalize & assert root prefix on all ops; reject `..` and symlinks.
- Observability: Structured INFO logs for scan + CRUD with fields: `event`, `path`, `duration_ms`, `template_count`, `folder_count`.
- Error handling: Typed exceptions with error codes (e.g., `E_NAME_EXISTS`); meaningful messages.
- Testing: Unit + integration tests under `tests/services/` for listing, CRUD, drag/move, cache invalidation, security, flat mode fallback, performance (mock), logging presence.
- Docs + Rollback: README/CHANGELOG; feature flag `hierarchical_templates` disables view when false.

## Risks & Mitigations
- FS race conditions: Revalidate existence before mutating; raise typed errors.
- Large directories: Use `os.scandir` and avoid O(N^2) rescans by caching; provide TTL.
- Symlink escapes: Do not follow symlinks; reject symlinked dirs/files.
- Cross-platform name rules: Enforce conservative regex `^[A-Za-z0-9._-]+$` for folders and stem for files.

## Rollback
- Flip feature flag off → UI uses legacy flat listing. CLI remains unchanged unless `--tree` used.

## Milestones
1. Tests for scanner + security + cache invalidation.
2. Implement `features.py` and `hierarchy.py` (scanner/cache).
3. Implement `hierarchy_fs.py` (CRUD + invalidation + logging).
4. CLI flags wiring (`--tree`, `--flat`) for `--list` command.
5. Additional tests (CRUD, drag/move, logging, performance mock, flat fallback).
6. Docs + CHANGELOG + review checklist.

