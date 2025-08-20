from __future__ import annotations

# Shared GUI instruction strings and hotkey labels.
INSTR_ACCEPT_RESET_REFRESH_CANCEL = (
    "Ctrl+Enter = Continue   |   Ctrl+R = Reset   |   Ctrl+U = Refresh   |   Esc = Cancel"
)
INSTR_FINISH_COPY_CLOSE = (
    "Ctrl+Enter = Finish (copies & closes), Ctrl+Shift+C = Copy without closing, Esc = Cancel"
)
INSTR_FINISH_COPY_AGAIN = (
    "Ctrl+Enter = Finish (copies & closes), Ctrl+Shift+C = Copy again, Esc = Cancel"
)
INFO_CLOSE_SAVE = "Ctrl+Enter/Esc = Close & Save"

__all__ = [
    "INSTR_ACCEPT_RESET_REFRESH_CANCEL",
    "INSTR_FINISH_COPY_CLOSE",
    "INSTR_FINISH_COPY_AGAIN",
    "INFO_CLOSE_SAVE",
]
