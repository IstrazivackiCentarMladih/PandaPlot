"""Shared, theme-token-driven leaf widgets for redesigned panels.

These widgets are plain QWidget subclasses (not PWidget) — they have no
AppContext dependency. Each exposes set_tokens(tokens: dict) so an owning
PWidget-based panel can push design tokens down from its own _apply_theme().
"""
