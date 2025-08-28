"""Template shortcut & renumber utilities.

Stores a mapping of shortcut keys -> relative template path in
``PROMPTS_DIR/Settings/template-shortcuts.json``. Provides logic to
renumber templates so a chosen shortcut digit becomes the on-disk ID
and filename prefix (e.g. key '1' -> id 1 -> ``01_title.json``).
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Dict, Tuple, List, Callable, Optional

from .errorlog import get_logger

from .config import PROMPTS_DIR, HOME_DIR

SETTINGS_DIR = PROMPTS_DIR / "Settings"
SHORTCUT_FILE = SETTINGS_DIR / "template-shortcuts.json"
LOCAL_SHORTCUT_FILE = HOME_DIR / "template-shortcuts.json"
_log = get_logger(__name__)


def load_shortcuts() -> Dict[str, str]:
    """Return merged shortcut mapping with local overrides taking precedence.

    Layering (highest to lowest):
      - ``LOCAL_SHORTCUT_FILE`` (machine-local, not under VCS)
      - ``SHORTCUT_FILE`` (repo defaults)
    """
    base: Dict[str, str] = {}
    try:
        if SHORTCUT_FILE.exists():
            data = json.loads(SHORTCUT_FILE.read_text())
            if isinstance(data, dict):
                base = {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    try:
        if LOCAL_SHORTCUT_FILE.exists():
            data_l = json.loads(LOCAL_SHORTCUT_FILE.read_text())
            if isinstance(data_l, dict):
                # Local values override repo defaults
                base.update({str(k): str(v) for k, v in data_l.items()})
    except Exception:
        pass
    return base


def save_shortcuts(mapping: Dict[str, str]) -> None:
    """Persist mapping to the local machine layer.

    Writes to ``LOCAL_SHORTCUT_FILE`` to avoid churn in version-controlled repos.
    """
    try:
        LOCAL_SHORTCUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOCAL_SHORTCUT_FILE.with_suffix('.tmp')
        tmp.write_text(json.dumps(mapping, indent=2), encoding='utf-8')
        tmp.replace(LOCAL_SHORTCUT_FILE)
    except Exception as e:
        _log.error("failed to save local shortcuts: %s", e)


def build_shortcut_options(base: Path | None = None) -> List[Dict[str, str]]:
    """Return structured options for mapping digits to templates.

    Each entry contains: ``id`` (str), ``title`` (str), ``rel`` (relative path),
    and a human-friendly ``label`` combining those fields. Intended for UI use
    but testable in headless environments.
    """
    from .renderer import load_template

    base = base or PROMPTS_DIR
    out: List[Dict[str, str]] = []
    for p in sorted(base.rglob('*.json')):
        # Skip settings control files or known non-template metadata lists
        if p.name.lower() == 'settings.json':
            continue
        try:
            data = load_template(p)
        except Exception:  # pragma: no cover - defensive
            continue
        # Some JSON files (e.g. Settings/starred.json) are lists of relative paths
        # rather than template objects; ignore anything that is not a dict.
        if not isinstance(data, dict):
            continue
        template_id = data.get('id')
        if not isinstance(template_id, int):
            continue
        if 'template' not in data:  # minimal schema gate
            continue
        try:
            rel = str(p.relative_to(base))
        except Exception:
            rel = p.name
        title = str(data.get('title') or p.stem)
        tid = str(template_id)
        label = f"[{tid}] {title} — {rel}"
        out.append({'id': tid, 'title': title, 'rel': rel, 'label': label})
    return out


def update_shortcut_digit(
    mapping: Dict[str, str],
    digit: str,
    rel: str,
    *,
    confirm_cb: Optional[Callable[[str, str, str], bool]] = None,
) -> Dict[str, str]:
    """Set ``digit`` -> ``rel`` mapping with optional overwrite confirmation.

    Parameters
    ----------
    mapping: current shortcut mapping (will be shallow-copied)
    digit: key to set (e.g. '1'..'9' or '0')
    rel: relative template path to assign
    confirm_cb: optional callback ``(digit, old_rel, new_rel) -> bool``.
        Called when overwriting an existing mapping. If absent or returns True,
        the overwrite proceeds; otherwise the existing mapping is kept.
    """
    new = dict(mapping)
    old = new.get(str(digit))
    if old and old != rel:
        if confirm_cb and not confirm_cb(str(digit), old, rel):
            _log.info("shortcut overwrite declined: %s stays %s", digit, old)
            return new
        _log.info("shortcut overwrite: %s %s -> %s", digit, old, rel)
    else:
        _log.info("shortcut set: %s -> %s", digit, rel)
    new[str(digit)] = rel
    return new


def _load_template_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_template_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')


def renumber_templates(shortcuts: Dict[str, str], base: Path | None = None) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Renumber templates so any numeric shortcut key ("1".."98") becomes that ID.

    Returns (updated_mapping, applied_ids) where applied_ids maps relative path -> new id.
    Non-numeric shortcut keys are ignored for renumbering.
    """
    base = base or PROMPTS_DIR
    applied: Dict[str, int] = {}
    # Build map current id -> path for conflict resolution
    id_to_path: Dict[int, Path] = {}
    all_templates: Dict[str, Path] = {}
    for p in base.rglob('*.json'):
        try:
            data = _load_template_json(p)
            if 'template' in data and isinstance(data.get('id'), int):
                id_to_path[data['id']] = p
                all_templates[str(p.relative_to(base))] = p
        except Exception:
            continue
    # Desired assignments (new_id -> path)
    desired: Dict[int, Path] = {}
    for key, rel in shortcuts.items():
        if not key.isdigit():
            continue
        num = int(key)
        if not (1 <= num <= 98):
            continue
        p = all_templates.get(rel)
        if p:
            desired[num] = p
    # Resolve collisions: if desired id occupied by different template, move occupant to next free id
    def next_free(start: int = 1) -> int:
        for i in range(start, 99):
            if i not in desired and i not in id_to_path:
                return i
        raise ValueError('No free IDs available')
    for target_id, path in list(desired.items()):
        existing_holder = id_to_path.get(target_id)
        if existing_holder and existing_holder.resolve() != path.resolve():
            new_id_for_existing = next_free()
            # Update existing holder later
            id_to_path[new_id_for_existing] = existing_holder
            data = _load_template_json(existing_holder)
            data['id'] = new_id_for_existing
            _write_template_json(existing_holder, data)
            new_name = existing_holder.with_name(f"{new_id_for_existing:02d}_{existing_holder.stem.split('_',1)[-1]}.json")
            if new_name != existing_holder:
                existing_holder.rename(new_name)
                # update maps
                rel_old = str(existing_holder.relative_to(base))
                rel_new = str(new_name.relative_to(base))
                for k, v in shortcuts.items():
                    if v == rel_old:
                        shortcuts[k] = rel_new
                all_templates[rel_new] = new_name
                all_templates.pop(rel_old, None)
            id_to_path.pop(target_id, None)
        # Now path will claim target_id below.
    # Apply desired ids
    for target_id, path in desired.items():
        data = _load_template_json(path)
        if data.get('id') == target_id:
            applied[str(path.relative_to(base))] = target_id
            continue
        data['id'] = target_id
        _write_template_json(path, data)
        # rename file prefix
        suffix_part = path.stem.split('_', 1)[-1]
        new_name = path.with_name(f"{target_id:02d}_{suffix_part}.json")
        if new_name != path:
            path.rename(new_name)
            rel_old = str(path.relative_to(base))
            rel_new = str(new_name.relative_to(base))
            # Update shortcut mapping value
            for k, v in shortcuts.items():
                if v == rel_old:
                    shortcuts[k] = rel_new
            applied[rel_new] = target_id
        else:
            applied[str(path.relative_to(base))] = target_id
    save_shortcuts(shortcuts)
    return shortcuts, applied


__all__ = [
    'load_shortcuts',
    'save_shortcuts',
    'renumber_templates',
    'SHORTCUT_FILE',
]
