"""Simple GUI front-end for prompt selection and rendering."""
from __future__ import annotations

import sys
from typing import Dict

from . import logger, menus, paste


def _build_placeholder_layout(sg, tmpl):
    layout = []
    for ph in tmpl.get("placeholders", []):
        label = ph.get("label", ph["name"])
        key = ph["name"]
        if ph.get("options"):
            layout.append([
                sg.Text(label),
                sg.Combo(ph["options"], key=key, size=(30, 1)),
            ])
        elif ph.get("multiline"):
            layout.append([
                sg.Text(label),
                sg.Multiline(key=key, size=(30, 3)),
            ])
        else:
            layout.append([sg.Text(label), sg.Input(key=key, size=(30, 1))])
    return layout


def run() -> None:
    """Launch the GUI. Requires :mod:`PySimpleGUI`."""
    try:
        import PySimpleGUI as sg
    except Exception as e:
        print("[prompt-automation] PySimpleGUI not available:", e, file=sys.stderr)
        return

    sg.theme("SystemDefault")
    styles = menus.list_styles()
    templates_cache: Dict[str, list[str]] = {}

    layout = [
        [sg.Text("Style"), sg.Input(key="-STYLE-FILTER-", enable_events=True)],
        [
            sg.Listbox(styles, size=(25, 10), key="-STYLE-", enable_events=True),
            sg.Column(
                [
                    [sg.Text("Template"), sg.Input(key="-TEMPLATE-FILTER-", enable_events=True)],
                    [sg.Listbox([], size=(30, 10), key="-TEMPLATE-", enable_events=True)],
                ]
            ),
        ],
        [sg.Column([], key="-PH-")],
        [sg.Button("Render"), sg.Button("Paste"), sg.Button("Exit")],
        [sg.Multiline(size=(80, 20), key="-OUTPUT-")],
    ]

    window = sg.Window("Prompt Automation", layout)
    current_tmpl = None
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            break
        if event == "-STYLE-FILTER-":
            query = values["-STYLE-FILTER-"].lower()
            filtered = [s for s in styles if query in s.lower()]
            window["-STYLE-"].update(filtered)
        elif event == "-STYLE-":
            sel = values["-STYLE-"]
            if sel:
                style = sel[0]
                templates = [p.name for p in menus.list_prompts(style)]
                templates_cache[style] = templates
                window["-TEMPLATE-"].update(templates)
                window["-TEMPLATE-FILTER-"].update("")
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
                tmpl_path = menus.PROMPTS_DIR / style_sel[0] / tmpl_sel[0]
                current_tmpl = menus.load_template(tmpl_path)
                window["-PH-"].update(_build_placeholder_layout(sg, current_tmpl))
        elif event == "Render" and current_tmpl:
            ph_vals = {ph["name"]: values.get(ph["name"], "") for ph in current_tmpl.get("placeholders", [])}
            text = menus.render_template(current_tmpl, ph_vals)
            window["-OUTPUT-"].update(text)
        elif event == "Paste" and current_tmpl:
            ph_vals = {ph["name"]: values.get(ph["name"], "") for ph in current_tmpl.get("placeholders", [])}
            text = menus.render_template(current_tmpl, ph_vals)
            if text:
                paste.paste_text(text)
                logger.log_usage(current_tmpl, len(text))
                window["-OUTPUT-"].update(text)
    window.close()
