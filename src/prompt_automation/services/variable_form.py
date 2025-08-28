"""Tkinter form widgets for variable placeholders.

This module exposes :func:`build_widget` which acts as a tiny factory for
constructing Tk based input widgets used during variable collection.  The
factory only performs lightweight widget construction so it can be exercised in
unit tests with simple tkinter stubs.

The returned tuple ``(constructor, binding)`` contains a callable that accepts a
Tk *master* widget and returns the created widget and a *binding* dictionary
exposing helpers and ``tk.Variable`` objects for retrieving or persisting the
value entered by the user.

Supported placeholder features
------------------------------
* Text inputs (single or multi line)
* File path chooser with optional persistence/skip flag
* Remembered context value persistence
* Optional file "view" callback hook
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple
import os

import tkinter as tk  # type: ignore
from tkinter import filedialog  # type: ignore

from ..errorlog import get_logger
from ..gui.single_window.formatting_helpers import next_line_prefix

from ..variables.storage import (
    _get_template_entry,
    _load_overrides,
    _save_overrides,
    _set_template_entry,
    get_remembered_context,
    set_remembered_context,
)


@dataclass
class _Binding:
    """Descriptor returned by :func:`build_widget`.

    Attributes are populated depending on the placeholder type but the
    following keys are always available on the mapping representation::

        get()      -> current value (``""`` when skipped)
        persist()  -> persist any override (no-op for transient values)
    """

    get: Callable[[], str]
    persist: Callable[[], None]
    path_var: tk.Variable | None = None
    skip_var: tk.Variable | None = None
    remember_var: tk.Variable | None = None
    view: Callable[[], None] | None = None

    def as_dict(self) -> Dict[str, Any]:  # pragma: no cover - trivial
        return {
            "get": self.get,
            "persist": self.persist,
            "path_var": self.path_var,
            "skip_var": self.skip_var,
            "remember_var": self.remember_var,
            "view": self.view,
        }


def build_widget(placeholder_spec: Dict[str, Any]) -> Tuple[Callable[[tk.Widget], tk.Widget], Dict[str, Any]]:
    """Return ``(constructor, binding)`` for ``placeholder_spec``.

    The constructor accepts a Tk *master* and returns the created widget.  The
    accompanying binding dictionary exposes ``get``/``persist`` callables and
    relevant ``tk.Variable`` instances to interact with the widget's state.
    """

    name = placeholder_spec.get("name", "")
    ptype = placeholder_spec.get("type")
    multiline = bool(placeholder_spec.get("multiline")) or ptype == "list"
    template_id = placeholder_spec.get("template_id")

    # --------------------------- text inputs ---------------------------------
    if ptype != "file":
        text_ref: Dict[str, tk.Widget | None] = {"widget": None}
        var = tk.StringVar()
        remember = bool(placeholder_spec.get("remember"))
        if remember:
            remembered = get_remembered_context()
            if remembered:
                var.set(remembered)
        initial = placeholder_spec.get("initial")
        if initial:
            var.set(str(initial))

        def _ctor(master: tk.Widget) -> tk.Widget:
            if multiline:
                widget = tk.Text(master)
                text = var.get()
                if text:
                    widget.insert("1.0", text)
                # Optional bullet/checklist auto-prefix on Enter
                fmt = str(placeholder_spec.get("format") or "").strip().lower()
                disabled = os.environ.get("PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX") == "1"
                if fmt in {"bullet", "checklist"} and not disabled:
                    log = get_logger("prompt_automation.gui.single_window")

                    def _on_return(ev, w=widget, format_type=fmt):  # pragma: no cover - runtime bind
                        try:
                            line_start = w.index("insert linestart")
                            line_end = w.index("insert lineend")
                            prev_line = w.get(line_start, line_end)
                            prefix = next_line_prefix(prev_line, format_type)  # type: ignore[arg-type]
                            w.insert("insert", "\n" + prefix)
                            try:
                                log.debug("bullet_insert", extra={"format": format_type, "inserted": prefix})
                            except Exception:
                                pass
                            return "break"
                        except Exception:
                            return None

                    try:
                        widget.bind("<Return>", _on_return)
                    except Exception:
                        pass
                text_ref["widget"] = widget
                return widget
            widget = tk.Entry(master, textvariable=var)
            text_ref["widget"] = widget
            return widget

        def _get() -> str:
            if multiline:
                widget = text_ref["widget"]
                if widget is None:
                    return ""
                return str(widget.get("1.0", "end-1c"))
            return str(var.get())

        def _persist() -> None:
            if remember:
                remember_var = binding.remember_var
                if remember_var is not None and bool(remember_var.get()):
                    set_remembered_context(_get())
                elif remember_var is not None and not bool(remember_var.get()):
                    set_remembered_context(None)

        remember_var = tk.BooleanVar(value=False) if remember else None

        binding = _Binding(
            get=_get,
            persist=_persist,
            remember_var=remember_var,
        )
        return _ctor, binding.as_dict()

    # ------------------------- file placeholders -----------------------------
    overrides = _load_overrides() if placeholder_spec.get("override") else {}
    entry = (
        _get_template_entry(overrides, template_id, name)
        if placeholder_spec.get("override") and template_id is not None
        else {}
    ) or {}
    initial_path = entry.get("path", "")
    initial_skip = bool(entry.get("skip"))

    path_var = tk.StringVar(value=initial_path)
    skip_var = tk.BooleanVar(value=initial_skip)

    def _browse() -> None:
        fname = filedialog.askopenfilename(title=placeholder_spec.get("label", name))
        if fname:
            path_var.set(fname)
            skip_var.set(False)

    view_cb = placeholder_spec.get("on_view")
    def _view() -> None:
        if view_cb:
            view_cb(path_var.get())

    def _ctor(master: tk.Widget) -> tk.Widget:
        frame = tk.Frame(master)
        entry_w = tk.Entry(frame, textvariable=path_var)
        browse_btn = tk.Button(frame, text="Browse", command=_browse)
        skip_btn = tk.Checkbutton(frame, text="Skip", variable=skip_var)
        # widgets are attached for potential external use but not packed to keep
        # the constructor light-weight and headless-test friendly.
        frame.entry = entry_w  # type: ignore[attr-defined]
        frame.browse_btn = browse_btn  # type: ignore[attr-defined]
        frame.skip_btn = skip_btn  # type: ignore[attr-defined]
        if view_cb:
            view_btn = tk.Button(frame, text="View", command=_view)
            frame.view_btn = view_btn  # type: ignore[attr-defined]
        return frame

    def _persist() -> None:
        if placeholder_spec.get("override") and template_id is not None:
            payload = {"path": path_var.get(), "skip": bool(skip_var.get())}
            _set_template_entry(overrides, template_id, name, payload)
            _save_overrides(overrides)

    def _get() -> str:
        return "" if bool(skip_var.get()) else str(path_var.get())

    binding = _Binding(
        get=_get,
        persist=_persist,
        path_var=path_var,
        skip_var=skip_var,
        view=_view if view_cb else None,
    )
    return _ctor, binding.as_dict()


__all__ = ["build_widget"]
