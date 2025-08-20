from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Sequence, Set

from ...config import PROMPTS_DIR


def apply_post_render(
    rendered: str,
    tmpl: Dict[str, Any],
    placeholders: Sequence[Dict[str, Any]],
    vars: Dict[str, Any],
    exclude_globals: Set[str],
) -> str:
    """Post-process rendered text.

    Handles remove-if-empty phrases, trim blanks, reminders, and think deeply.
    """

    try:
        for ph in placeholders:
            name = ph.get("name")
            if not name:
                continue
            val = vars.get(name)
            if val is not None and str(val).strip():
                continue
            phrases = ph.get("remove_if_empty") or ph.get("remove_if_empty_phrases")
            if not phrases:
                continue
            if isinstance(phrases, str):
                phrases = [phrases]
            for phrase in phrases:
                if not isinstance(phrase, str) or not phrase.strip():
                    continue
                pattern = re.compile(
                    rf"(\s|^){re.escape(phrase.strip())}(?=\s*[.,;:!?])",
                    re.IGNORECASE,
                )
                rendered = pattern.sub(
                    lambda m: m.group(1) if m.group(1).isspace() else "",
                    rendered,
                )
                pattern2 = re.compile(
                    rf"(\s|^){re.escape(phrase.strip())}\s+",
                    re.IGNORECASE,
                )
                rendered = pattern2.sub(
                    lambda m: m.group(1) if m.group(1).isspace() else "",
                    rendered,
                )

        meta = tmpl.get("metadata", {}) if isinstance(tmpl.get("metadata"), dict) else {}
        trim_blanks_flag = meta.get("trim_blanks")
        if trim_blanks_flag is None:
            try:
                gfile = PROMPTS_DIR / "globals.json"
                if gfile.exists():
                    gdata = json.loads(gfile.read_text())
                    trim_blanks_flag = (
                        gdata.get("render_settings", {}).get("trim_blanks")
                        or gdata.get("global_settings", {}).get("trim_blanks")
                        or gdata.get("trim_blanks")
                    )
            except Exception:
                trim_blanks_flag = None
        if trim_blanks_flag is None:
            env_val = os.environ.get("PROMPT_AUTOMATION_TRIM_BLANKS")
            if env_val is not None:
                if env_val.lower() in {"0", "false", "no", "off"}:
                    trim_blanks_flag = False
                else:
                    trim_blanks_flag = True
        if trim_blanks_flag is None:
            trim_blanks_flag = True
        if trim_blanks_flag:
            rendered = "\n".join([ln.rstrip() for ln in rendered.splitlines()]).strip()
    except Exception:
        pass

    gph = tmpl.get("global_placeholders")
    try:
        reminders = gph.get("reminders") if isinstance(gph, dict) else None
        if reminders:
            if isinstance(reminders, str):
                reminders_list = [reminders]
            elif isinstance(reminders, list):
                reminders_list = [str(r) for r in reminders if str(r).strip()]
            else:
                reminders_list = []
            reminders_list = [r for r in reminders_list if r.strip()]
            if reminders_list:
                rendered += "\n\nReminders:\n" + "\n".join(
                    f"> - {r}" for r in reminders_list
                )
                appended_reminders = True
            else:
                appended_reminders = False
        else:
            appended_reminders = False
        td_val = gph.get("think_deeply") if isinstance(gph, dict) else None
        if isinstance(td_val, str) and td_val.strip():
            token = "{{think_deeply}}"
            if token not in "\n".join(tmpl.get("template", [])) and td_val.strip() not in rendered:
                if "think_deeply" not in exclude_globals:
                    if not rendered.endswith("\n"):
                        rendered += "\n"
                    if appended_reminders:
                        rendered += "\n"
                    rendered += td_val.strip()
    except Exception:
        pass

    return rendered
