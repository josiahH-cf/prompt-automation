"""Scroll snapping helpers for single-window GUI forms.

Provides a pure function for computing the desired top of the viewport
and a Tk-using helper that applies the adjustment to a canvas.
"""
from __future__ import annotations
from ...errorlog import get_logger


def compute_scroll_adjustment(
    widget_top: int, widget_bottom: int, view_top: int, view_bottom: int
) -> int | None:
    """Return the new ``view_top`` if adjustment is needed, else ``None``.

    Ensures the entire widget rectangle [widget_top, widget_bottom] is visible
    within the current viewport [view_top, view_bottom]. If the widget is
    already fully visible, returns ``None``.
    """
    # Already fully visible
    if widget_top >= view_top and widget_bottom <= view_bottom:
        return None
    # If below the viewport, scroll so the widget top aligns to the top,
    # or minimally so its bottom becomes visible. Prefer aligning the top.
    if widget_bottom > view_bottom:
        return max(widget_top, widget_bottom - (view_bottom - view_top))
    # If above the viewport, align its top to the top.
    if widget_top < view_top:
        return widget_top
    return None


def ensure_visible(canvas, inner, widget) -> None:  # pragma: no cover - Tk runtime
    """Adjust the canvas yview so ``widget`` becomes fully visible.

    ``canvas`` is a ``tk.Canvas`` containing an inner frame ``inner``.
    """
    try:
        canvas.update_idletasks()
        inner.update_idletasks()
        # Compute coordinates in the inner frame space
        w_top = widget.winfo_rooty() - inner.winfo_rooty()
        w_bot = w_top + widget.winfo_height()
        v_top = canvas.canvasy(0)
        v_bot = v_top + canvas.winfo_height()
        new_top = compute_scroll_adjustment(int(w_top), int(w_bot), int(v_top), int(v_bot))
        if new_top is None:
            return
        total_h = max(1, inner.winfo_height())
        cv_h = max(1, canvas.winfo_height())
        # Normalize to fraction for yview_moveto; clamp to [0,1]
        denom = max(1, total_h - cv_h)
        frac = max(0.0, min(1.0, new_top / denom))
        canvas.yview_moveto(frac)
        try:
            get_logger("prompt_automation.gui.single_window").debug(
                "scroll_adjust", extra={
                    "delta": int(new_top - v_top),
                    "widget_top": int(w_top),
                    "widget_bottom": int(w_bot),
                }
            )
        except Exception:
            pass
    except Exception:
        # Best-effort only; avoid raising in runtime UI
        pass


def ensure_insert_visible(canvas, inner, text_widget) -> None:  # pragma: no cover - Tk runtime
    """Scroll the outer canvas so the Text widget's insertion cursor is visible.

    This accounts for the caret location within a scrolled Text widget by
    querying ``text_widget.bbox('insert')`` and translating to the canvas
    coordinate system, then applying the same adjustment policy used by
    :func:`ensure_visible`.
    """
    try:
        # Make sure layout metrics are up-to-date
        canvas.update_idletasks()
        inner.update_idletasks()
        text_widget.update_idletasks()
        bbox = text_widget.bbox("insert")
        if not bbox:
            # Fallback: ensure entire widget visibility if caret bbox missing
            return ensure_visible(canvas, inner, text_widget)
        # bbox is (x, y, width, height) relative to the Text widget's visible area
        _, by, _, bh = bbox
        # Convert to inner frame coordinates
        w_top_abs = text_widget.winfo_rooty() - inner.winfo_rooty()
        caret_top = int(w_top_abs + by)
        caret_bottom = int(caret_top + bh)
        v_top = int(canvas.canvasy(0))
        v_bot = int(v_top + canvas.winfo_height())
        new_top = compute_scroll_adjustment(caret_top, caret_bottom, v_top, v_bot)
        if new_top is None:
            return
        total_h = max(1, inner.winfo_height())
        cv_h = max(1, canvas.winfo_height())
        denom = max(1, total_h - cv_h)
        frac = max(0.0, min(1.0, new_top / denom))
        canvas.yview_moveto(frac)
    except Exception:
        pass


__all__ = ["compute_scroll_adjustment", "ensure_visible", "ensure_insert_visible"]
