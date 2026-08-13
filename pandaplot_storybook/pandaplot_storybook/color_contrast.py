"""WCAG contrast-ratio utilities used to verify storybook-local color overrides.

Kept dependency-free (no Qt) so it's trivially unit-testable headless.
"""
from __future__ import annotations


def _srgb_channel_to_linear(channel: float) -> float:
    """Convert an sRGB channel value (0-1) to its linear-light equivalent."""
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance (0=black, 1=white) for a '#RRGGBB' hex color."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Expected a 6-digit hex color, got {hex_color!r}")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    r_lin, g_lin, b_lin = (_srgb_channel_to_linear(c) for c in (r, g, b))
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG contrast ratio between two '#RRGGBB' (or 'RRGGBB') colors.

    Ranges from 1.0 (no contrast, identical colors) to 21.0 (black on white
    or white on black).
    """
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# Storybook-only override for the theme-switch SegmentedControl's selected
# state (see main_window.py). Pandaplot's global QSS pairs
# `accent_selected_bg` with `accent_active_text`, which in dark mode falls
# below WCAG AA (4.5:1). These are chosen to clear 4.5:1 against both the
# light and dark `accent_selected_bg` tokens (verified in
# storybook_tests/test_color_contrast.py against real ThemeManager tokens),
# without touching pandaplot's shared stylesheet.
SEGMENTED_SELECTED_TEXT = {
    "light": "#1C1E26",
    "dark": "#FFFFFF",
}


__all__ = ["SEGMENTED_SELECTED_TEXT", "contrast_ratio"]
