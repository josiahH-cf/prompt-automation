from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any, Dict, Sequence


def _escape(s: str) -> str:
    return html.escape(s, quote=False)


def _md_to_html(text: str) -> str:
    """Very small markdown-to-HTML converter (headings, code, bold).

    Avoid external deps; sufficient for reference file previews. Sanitizes by
    escaping first, then reintroducing minimal tags.
    """
    esc = _escape(text).replace("\r", "")
    out_lines: list[str] = []
    in_code = False
    for raw in esc.splitlines():
        if raw.strip().startswith("```"):
            if not in_code:
                out_lines.append("<pre><code>")
                in_code = True
            else:
                out_lines.append("</code></pre>")
                in_code = False
            continue
        if not in_code:
            if raw.startswith("### "):
                out_lines.append(f"<h3>{raw[4:]}</h3>")
                continue
            if raw.startswith("## "):
                out_lines.append(f"<h2>{raw[3:]}</h2>")
                continue
            if raw.startswith("# "):
                out_lines.append(f"<h1>{raw[2:]}</h1>")
                continue
            # bold
            ln = raw.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            out_lines.append(f"<p>{ln}</p>" if ln.strip() else "")
        else:
            out_lines.append(raw)
    if in_code:
        out_lines.append("</code></pre>")
    return "\n".join(l for l in out_lines if l is not None)


def apply_markdown_rendering(
    tmpl: Dict[str, Any],
    vars: Dict[str, Any],
    placeholders: Sequence[Dict[str, Any]],
) -> None:
    """Replace markdown placeholders with HTML and wrappers when appropriate.

    Rules:
      - Only applies when placeholder has render == 'markdown'.
      - If placeholder line is not the last non-empty template line => wrap in
        a collapsible <details> block. The summary includes the filename when
        a corresponding *_path variable exists.
      - If last => insert expanded HTML without wrapper.
      - Controlled by env PROMPT_AUTOMATION_MD_REF_HTML ("0" disables).
    """
    if os.environ.get("PROMPT_AUTOMATION_MD_REF_HTML", "1") == "0":
        return
    lines = tmpl.get("template", []) or []
    if not isinstance(lines, list):
        return
    # Compute last non-empty line index
    last_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        if str(lines[i]).strip():
            last_idx = i
            break
    if last_idx < 0:
        return
    # Map name -> index of first occurrence
    occ: dict[str, int] = {}
    for i, ln in enumerate(lines):
        for ph in placeholders:
            nm = ph.get("name")
            if not nm or ph.get("render") != "markdown":
                continue
            tok = f"{{{{{nm}}}}}"
            if tok in str(ln) and nm not in occ:
                occ[nm] = i
    for ph in placeholders:
        nm = ph.get("name")
        if not nm or ph.get("render") != "markdown":
            continue
        val = vars.get(nm)
        if not isinstance(val, str) or not val:
            continue
        html_payload = _md_to_html(val)
        idx = occ.get(nm, -1)
        if idx >= 0 and idx < last_idx:
            # Mid-sequence -> collapsible
            summary = "Reference"
            pth = vars.get(f"{nm}_path") or vars.get("reference_file_path")
            try:
                if isinstance(pth, str) and pth.strip():
                    summary = f"Reference: {Path(pth).name}"
            except Exception:
                pass
            wrapped = f"<details><summary>{_escape(summary)}</summary>\n{html_payload}\n</details>"
            vars[nm] = wrapped
        else:
            # End-of-sequence -> expanded
            vars[nm] = html_payload

