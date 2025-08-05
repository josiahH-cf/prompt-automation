"""Simple GUI front-end for prompt selection and rendering."""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict

from . import logger, menus, paste, update
from .errorlog import get_logger


_log = get_logger(__name__)


def _build_placeholder_layout(sg, tmpl):
    layout = []
    for ph in tmpl.get("placeholders", []):
        label = ph.get("label", ph["name"])
        key = ph["name"]
        ptype = ph.get("type")
        if ph.get("options"):
            layout.append([
                sg.Text(label),
                sg.Combo(ph["options"], key=key, size=(30, 1)),
            ])
        elif ptype == "file":
            layout.append([
                sg.Text(label),
                sg.Input(key=key, size=(30, 1), enable_events=True),
                sg.FileBrowse(target=key),
                sg.Button("Clear", key=f"{key}_clear"),
            ])
        elif ptype == "list" or ph.get("multiline"):
            layout.append([
                sg.Text(label),
                sg.Multiline(key=key, size=(30, 3)),
            ])
        else:
            layout.append([sg.Text(label), sg.Input(key=key, size=(30, 1))])
    return layout


def _validate_file_inputs(window, tmpl, values):
    invalid = []
    if not tmpl:
        return invalid
    for ph in tmpl.get("placeholders", []):
        if ph.get("type") == "file":
            key = ph["name"]
            path = values.get(key, "")
            if path and not Path(path).expanduser().is_file():
                window[key].update(background_color="#ffdddd")
                invalid.append(key)
            else:
                window[key].update(background_color=None)
    return invalid


def _prompt_missing_file(sg, window, key, path):
    choice = sg.popup(
        f"File not found:\n{path}",
        "Browse to locate, Skip to ignore, or Remove to clear.",
        custom_text=("Browse", "Skip", "Remove"),
    )
    if choice == "Browse":
        new_path = sg.popup_get_file("Select file", no_window=True)
        if new_path:
            window[key].update(new_path)
            _log.info("updated file placeholder %s to %s", key, new_path)
            return new_path, False
    elif choice == "Remove":
        window[key].update("")
        _log.info("removed file placeholder %s", key)
        return "", False
    _log.info("skipped missing file %s for %s", path, key)
    return path, True


def _edit_template_window(sg, data=None, path=None):
    """Open modal editor for a template and return saved path or ``None``."""
    if data is None:
        data = {"id": "", "title": "", "style": "", "role": "", "template": [], "placeholders": []}
    layout = [
        [sg.Text("ID"), sg.Input(str(data.get("id", "")), key="id")],
        [sg.Text("Title"), sg.Input(data.get("title", ""), key="title")],
        [sg.Text("Style"), sg.Input(data.get("style", ""), key="style")],
        [sg.Text("Role"), sg.Input(data.get("role", ""), key="role")],
        [
            sg.Text("Template"),
            sg.Multiline("\n".join(data.get("template", [])), size=(60, 10), key="template"),
        ],
        [
            sg.Text("Placeholders (JSON)"),
            sg.Multiline(
                json.dumps(data.get("placeholders", []), indent=2),
                size=(60, 10),
                key="placeholders",
            ),
        ],
        [sg.Button("Save"), sg.Button("Cancel")],
    ]
    win = sg.Window("Template", layout, modal=True)
    result = None
    while True:
        ev, vals = win.read()
        if ev in (sg.WIN_CLOSED, "Cancel"):
            break
        if ev == "Save":
            try:
                tpl = {
                    "id": int(vals["id"]),
                    "title": vals["title"],
                    "style": vals["style"],
                    "role": vals["role"],
                    "template": [l for l in vals["template"].splitlines()],
                    "placeholders": json.loads(vals["placeholders"] or "[]"),
                }
                result = menus.save_template(tpl, orig_path=path)
                break
            except Exception as e:
                sg.popup_error(f"Error saving template: {e}")
    win.close()
    return result


def run() -> None:
    """Launch the GUI. Requires :mod:`FreeSimpleGUI` or :mod:`PySimpleGUI`. Falls back to CLI if GUI fails."""
    update.check_and_prompt()
    try:
        # Try FreeSimpleGUI first (open source), then PySimpleGUI (commercial)
        try:
            import FreeSimpleGUI as sg
            _log.info("Using FreeSimpleGUI for GUI")
        except ImportError:
            try:
                import PySimpleGUI as sg
                _log.info("Using PySimpleGUI for GUI")
            except ImportError:
                raise ImportError("Neither FreeSimpleGUI nor PySimpleGUI is available")
    except Exception as e:
        _log.warning("GUI library not available: %s", e)
        print("[prompt-automation] GUI not available, falling back to terminal mode:", e, file=sys.stderr)
        # Fall back to CLI
        from . import cli
        cli.main(["--terminal"])
        return

    try:
        sg.theme("SystemDefault")
        styles = menus.list_styles()
        templates_cache: Dict[str, list[str]] = {}

        layout = [
            [
                sg.Text("Style"),
                sg.Input(key="-STYLE-FILTER-", enable_events=True),
                sg.Button("New Style"),
                sg.Button("Del Style"),
            ],
            [
                sg.Listbox(styles, size=(25, 10), key="-STYLE-", enable_events=True),
                sg.Column(
                    [
                        [
                            sg.Text("Template"),
                            sg.Input(key="-TEMPLATE-FILTER-", enable_events=True),
                            sg.Button("New"),
                            sg.Button("Edit"),
                            sg.Button("Del"),
                        ],
                        [
                            sg.Listbox(
                                [], size=(30, 10), key="-TEMPLATE-", enable_events=True
                            )
                        ],
                    ]
                ),
            ],
            [sg.Column([], key="-PH-")],
            [sg.Button("Render"), sg.Button("Paste"), sg.Button("Exit")],
            [sg.Multiline(size=(80, 20), key="-OUTPUT-")],
        ]
    except Exception as e:
        _log.error("Failed to initialize GUI: %s", e)
        print("[prompt-automation] Failed to initialize GUI, falling back to terminal mode:", e, file=sys.stderr)
        # Fall back to CLI
        from . import cli
        cli.main(["--terminal"])
        return

    try:
        window = sg.Window("Prompt Automation", layout, return_keyboard_events=True)
        current_tmpl = None
        current_path = None
        file_keys: set[str] = set()
        while True:
            event, values = window.read()
            if event in (sg.WIN_CLOSED, "Exit"):
                break
            if event == "-STYLE-FILTER-":
                query = values["-STYLE-FILTER-"].lower()
                filtered = [s for s in styles if query in s.lower()]
                window["-STYLE-"].update(filtered)
            elif event == "New Style":
                name = sg.popup_get_text("New style name:")
                if name:
                    menus.add_style(name)
                    styles = menus.list_styles()
                    window["-STYLE-"].update(styles)
            elif event == "Del Style":
                sel = values["-STYLE-"]
                if sel and sg.popup_ok_cancel(f"Delete style {sel[0]}?") == "OK":
                    try:
                        menus.delete_style(sel[0])
                        styles = menus.list_styles()
                        window["-STYLE-"].update(styles)
                        window["-TEMPLATE-"].update([])
                    except Exception as e:
                        sg.popup_error(f"Cannot delete style: {e}")
            elif event == "-STYLE-":
                sel = values["-STYLE-"]
                if sel:
                    style = sel[0]
                    templates = [p.name for p in menus.list_prompts(style)]
                    templates_cache[style] = templates
                    window["-TEMPLATE-"].update(templates)
                    window["-TEMPLATE-FILTER-"].update("")
            elif event == "New":
                sel = values["-STYLE-"]
                data = {"style": sel[0]} if sel else None
                path = _edit_template_window(sg, data)
                if path:
                    styles = menus.list_styles()
                    window["-STYLE-"].update(styles)
                    style = path.parent.name
                    templates = [p.name for p in menus.list_prompts(style)]
                    templates_cache[style] = templates
                    window["-TEMPLATE-"].update(templates)
            elif event == "Edit" and current_tmpl and current_path:
                path = _edit_template_window(sg, current_tmpl, current_path)
                if path:
                    current_path = path
                    current_tmpl = menus.load_template(path)
                    styles = menus.list_styles()
                    window["-STYLE-"].update(styles)
                    style = path.parent.name
                    templates = [p.name for p in menus.list_prompts(style)]
                    templates_cache[style] = templates
                    window["-TEMPLATE-"].update(templates)
                    window["-PH-"].update(_build_placeholder_layout(sg, current_tmpl))
                    file_keys = {p["name"] for p in current_tmpl.get("placeholders", []) if p.get("type") == "file"}
            elif event == "Del" and current_path:
                if sg.popup_ok_cancel(f"Delete {current_path.name}?") == "OK":
                    menus.delete_template(current_path)
                    current_path = None
                    current_tmpl = None
                    sel = values["-STYLE-"]
                    if sel:
                        style = sel[0]
                        templates = [p.name for p in menus.list_prompts(style)]
                        templates_cache[style] = templates
                        window["-TEMPLATE-"].update(templates)
                    window["-PH-"].update([])
                    window["-OUTPUT-"].update("")
                    file_keys = set()
            elif event == "-TEMPLATE-FILTER-":
                sel = values["-STYLE-"]
                if sel:
                    style = sel[0]
                    templates = templates_cache.get(style) or [p.name for p in menus.list_prompts(style)]
                    query = values["-TEMPLATE-FILTER-"].lower()
                    filtered = [t for t in templates if query in t.lower()]
                    window["-TEMPLATE-"].update(filtered)
            elif event == "-TEMPLATE-":
                style_sel = values["-STYLE-"]
                tmpl_sel = values["-TEMPLATE-"]
                if style_sel and tmpl_sel:
                    current_path = menus.PROMPTS_DIR / style_sel[0] / tmpl_sel[0]
                    current_tmpl = menus.load_template(current_path)
                    window["-PH-"].update(_build_placeholder_layout(sg, current_tmpl))
                    file_keys = {p["name"] for p in current_tmpl.get("placeholders", []) if p.get("type") == "file"}
            elif current_tmpl and event in file_keys:
                _validate_file_inputs(window, current_tmpl, values)
            elif current_tmpl and isinstance(event, str) and event.endswith("_clear"):
                key = event[:-6]
                window[key].update("")
                values[key] = ""
                _validate_file_inputs(window, current_tmpl, values)
            elif event == "Render" and current_tmpl:
                skip_keys = set()
                invalid = _validate_file_inputs(window, current_tmpl, values)
                for key in invalid:
                    path = values.get(key, "")
                    new_path, skip = _prompt_missing_file(sg, window, key, path)
                    values[key] = new_path
                    if skip:
                        skip_keys.add(key)
                ph_vals = {}
                for ph in current_tmpl.get("placeholders", []):
                    key = ph["name"]
                    val = values.get(key, "")
                    if key in skip_keys:
                        val = ""
                    if ph.get("type") == "list":
                        val = [v for v in val.splitlines() if v]
                    ph_vals[key] = val
                text = menus.render_template(current_tmpl, ph_vals)
                window["-OUTPUT-"].update(text)
            elif event == "Paste":
                text = values.get("-OUTPUT-", "")
                if not text and current_tmpl:
                    skip_keys = set()
                    invalid = _validate_file_inputs(window, current_tmpl, values)
                    for key in invalid:
                        path = values.get(key, "")
                        new_path, skip = _prompt_missing_file(sg, window, key, path)
                        values[key] = new_path
                        if skip:
                            skip_keys.add(key)
                    ph_vals = {}
                    for ph in current_tmpl.get("placeholders", []):
                        key = ph["name"]
                        val = values.get(key, "")
                        if key in skip_keys:
                            val = ""
                        if ph.get("type") == "list":
                            val = [v for v in val.splitlines() if v]
                        ph_vals[key] = val
                    text = menus.render_template(current_tmpl, ph_vals)
                    window["-OUTPUT-"].update(text)
                if text:
                    paste.paste_text(text)
                    if current_tmpl:
                        logger.log_usage(current_tmpl, len(text))
            elif isinstance(event, str) and event.startswith("Return"):
                text = values.get("-OUTPUT-", "")
                if text:
                    paste.paste_text(text)
                    if current_tmpl:
                        logger.log_usage(current_tmpl, len(text))
        window.close()
    except Exception as e:
        _log.error("GUI runtime error: %s", e)
        print("[prompt-automation] GUI failed during execution, falling back to terminal mode:", e, file=sys.stderr)
        # Fall back to CLI
        from . import cli
        cli.main(["--terminal"])
        return
