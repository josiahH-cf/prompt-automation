from __future__ import annotations

from typing import Dict


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join([c * 2 for c in h])
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return r, g, b


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    # sRGB to linear RGB
    def _lin(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    R = _lin(r)
    G = _lin(g)
    B = _lin(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    L1 = _relative_luminance(_hex_to_rgb(fg_hex))
    L2 = _relative_luminance(_hex_to_rgb(bg_hex))
    Lmax, Lmin = (L1, L2) if L1 >= L2 else (L2, L1)
    return (Lmax + 0.05) / (Lmin + 0.05)


class ThemeRegistry:
    def __init__(self) -> None:
        self._themes: Dict[str, Dict[str, str]] = {}

    def register(self, name: str, tokens: Dict[str, str]) -> None:
        if not name or not isinstance(name, str):
            return
        if not all(k in tokens for k in (
            'background','surface','surfaceAlt','border','divider','textPrimary','textSecondary','textMuted',
            'accentPrimary','accentHover','success','warning','error','info','selectionBackground','selectionForeground','focusOutline'
        )):
            # Require all tokens for safety
            return
        self._themes[name] = dict(tokens)
        self._themes[name]['name'] = name

    def get(self, name: str) -> Dict[str, str] | None:
        t = self._themes.get(name)
        return dict(t) if t else None

    def has(self, name: str) -> bool:
        return name in self._themes

    def list(self) -> list[str]:
        return sorted(self._themes.keys())


_REGISTRY = ThemeRegistry()


def _register_builtins() -> None:
    # Light theme: identity/no-op for now; applier treats light as no-op
    light = {
        'background': '#FFFFFF',
        'surface': '#FFFFFF',
        'surfaceAlt': '#F7F7F7',
        'border': '#DDDDDD',
        'divider': '#E6E6E6',
        'textPrimary': '#111111',
        'textSecondary': '#333333',
        'textMuted': '#666666',
        'accentPrimary': '#0B67FF',
        'accentHover': '#3A86FF',
        'success': '#12A150',
        'warning': '#C98500',
        'error': '#D12F2F',
        'info': '#1479FF',
        'selectionBackground': '#CCE0FF',
        'selectionForeground': '#0A1A33',
        'focusOutline': '#3A86FF',
    }
    dark = {
        'background': '#121417',
        'surface': '#1E2227',
        'surfaceAlt': '#161A1F',
        'border': '#2B3138',
        'divider': '#2C3238',
        'textPrimary': '#E6EAF0',
        'textSecondary': '#B4BEC9',
        'textMuted': '#8491A1',
        'accentPrimary': '#5AA9E6',
        'accentHover': '#7BC4FF',
        'success': '#4CC38A',
        'warning': '#FFB757',
        'error': '#E5484D',
        'info': '#7AA7FF',
        'selectionBackground': '#2D4A72',
        'selectionForeground': '#F7FAFF',
        'focusOutline': '#6CA4FF',
    }
    _REGISTRY.register('light', light)
    _REGISTRY.register('dark', dark)


_register_builtins()


def register_theme(name: str, tokens: Dict[str, str]) -> None:
    _REGISTRY.register(name, tokens)


def get_theme(name: str) -> Dict[str, str]:
    t = _REGISTRY.get(name)
    if not t:
        t = _REGISTRY.get('light') or {}
        t['name'] = 'light'
    return t


def list_themes() -> list[str]:
    return _REGISTRY.list()


def get_registry() -> ThemeRegistry:
    return _REGISTRY

