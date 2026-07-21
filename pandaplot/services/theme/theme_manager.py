"""Theme Manager (Phase 3).

Applies application-wide theming based on configuration and reacts to
configuration changes via the event bus. Emits a lightweight
``theme.changed`` event whenever an application-level theme (light/dark/system)
change or accent/font change is applied.

Responsibilities:
    * Build a global Qt stylesheet (QSS) from current configuration
    * Apply palette / font size adjustments (minimal for now)
    * Subscribe to ``config.loaded`` & ``config.updated`` events
    * Emit ``theme.changed`` after applying style

Non-goals (future phases): advanced component‑specific palettes, high‑contrast
accessibility themes, dynamic chart color palettes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.events.event_types import ConfigEvents, ThemeEvents
from pandaplot.models.state.config import ApplicationConfig, Theme


@dataclass(slots=True)
class ThemeContext:
    """Snapshot of theme-relevant config values."""

    theme: Theme
    accent: str
    interface_font_size: int


class ThemeManager:
    def __init__(self, event_bus: EventBus, config_provider, qt_app: Optional[QApplication] = None):
        """Create manager.

        Args:
            event_bus: shared event bus
            config_provider: object exposing ``config`` attribute (ConfigManager)
            qt_app: QApplication (can be injected later via ``set_qt_app``)
        """
        self._bus = event_bus
        self._provider = config_provider
        self._app: Optional[QApplication] = qt_app
        self._current: Optional[ThemeContext] = None
        # Subscribe to configuration lifecycle events
        self._bus.subscribe(ConfigEvents.CONFIG_UPDATED, self._on_config_event)

    def set_qt_app(self, app: QApplication) -> None:
        self._app = app

    def apply_current(self) -> None:
        cfg: ApplicationConfig = self._provider.config  # type: ignore[attr-defined]
        self.apply_from_config(cfg)

    def apply_from_config(self, cfg: ApplicationConfig) -> None:
        ctx = ThemeContext(
            theme=cfg.appearance.theme,
            accent=cfg.appearance.accent_color,
            interface_font_size=cfg.appearance.interface_font_size,
        )
        if self._current and self._current == ctx:
            return  # no change
        self._current = ctx
        if self._app is not None:
            self._apply_to_qapp(ctx)
        self._bus.emit(ThemeEvents.THEME_CHANGED, {
            "theme": ctx.theme.value,
            "accent": ctx.accent,
            "font_size": ctx.interface_font_size,
        })

    def build_stylesheet(self, ctx: ThemeContext) -> str:
        accent = ctx.accent
        text_color = "#000000"  # fallback
        hover = accent
        pressed = accent
        try:
            c = QColor(accent)
            if c.isValid():
                # Derive hover / pressed variants
                hover = c.lighter(110).name()
                pressed = c.darker(115).name()
                # Compute relative luminance to decide contrasting text color
                r, g, b = c.red(), c.green(), c.blue()
                lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
                # If accent is light, use dark text; if dark, use light text
                if lum > 0.6:
                    text_color = "#000000"
                else:
                    text_color = "#FFFFFF"
            # Adjust for overall theme preference so light theme favors dark text unless accent is extremely dark
            if ctx.theme != Theme.DARK and text_color == "#FFFFFF":
                # Force dark text if accent still offers 4.5:1 contrast against white background (approx luminance threshold)
                # If accent is very dark (lum < 0.25) keep white text.
                if lum >= 0.25:
                    text_color = "#000000"
        except Exception:  # noqa: BLE001
            pass

        return f"""
            QPushButton[primary="true"] {{
                background-color: {accent};
                border: 1px solid {accent};
                border-radius: 4px;
                padding: 4px 8px;
                color: {text_color};
            }}
            QPushButton[primary="true"]:hover {{
                background-color: {hover};
                border-color: {hover};
            }}
            QPushButton[primary="true"]:pressed {{
                background-color: {pressed};
                border-color: {pressed};
            }}
            QTabBar::tab:selected {{ color: {accent}; }}
        """

    def _apply_to_qapp(self, ctx: ThemeContext) -> None:
        """Apply palette & global QSS to the QApplication."""
        if not self._app:
            return
        palette = self._app.palette() if self._app else QPalette()
        if ctx.theme == Theme.DARK:
            bg = QColor(30, 30, 30)
            fg = QColor(224, 224, 224)
        else:
            bg = QColor(255, 255, 255)
            fg = QColor(0, 0, 0)
        palette.setColor(QPalette.ColorRole.Window, bg)
        palette.setColor(QPalette.ColorRole.WindowText, fg)
        palette.setColor(QPalette.ColorRole.Base, bg)
        palette.setColor(QPalette.ColorRole.Text, fg)
        self._app.setPalette(palette)
        self._app.setStyleSheet(self.build_stylesheet(ctx))
        f = self._app.font()
        f.setPointSize(ctx.interface_font_size)
        self._app.setFont(f)

    def get_surface_palette(self) -> dict:
        if not self._current:
            return {
                "card_bg": "#f8f9fa",
                "card_hover": "#e9ecef",
                "card_pressed": "#dee2e6",
                "card_border": "#dee2e6",
                "base_fg": "#000000",
                "secondary_fg": "#555555",
                "accent": "#4A90E2",
            }
        ctx = self._current
        if ctx.theme == Theme.DARK:
            return {
                "card_bg": "#2a2c2e",
                "card_hover": "#323437",
                "card_pressed": "#3a3d40",
                "card_border": "#404347",
                "base_fg": "#e2e2e2",
                "secondary_fg": "#a8adb2",
                "accent": ctx.accent,
            }
        return {
            "card_bg": "#f8f9fa",
            "card_hover": "#e9ecef",
            "card_pressed": "#dee2e6",
            "card_border": "#dee2e6",
            "base_fg": "#000000",
            "secondary_fg": "#555555",
            "accent": ctx.accent,
        }

    def get_design_tokens(self) -> dict:
        """Full token set for the chart-properties redesign's shared widgets.

        Superset of get_surface_palette(); both stay in sync with the
        current ThemeContext (theme + accent) so callers always see the
        user's live theme/accent choice.
        """
        accent = self._current.accent if self._current else "#4A56C6"
        is_dark = self._current is not None and self._current.theme == Theme.DARK

        c = QColor(accent)
        accent_active_text = c.darker(115).name() if c.isValid() else accent
        accent_disabled = c.lighter(140).name() if c.isValid() else "#AAB1E3"

        if is_dark:
            return {
                "text_primary": "#E2E2E2", "text_secondary": "#C7CAD1",
                "text_muted": "#9AA0AB", "text_hint": "#6B7280",
                "border_panel": "#3A3D40", "border_control": "#4A4D52",
                "border_subtle": "#33363A",
                "surface_white": "#2A2C2E", "surface_chrome": "#232527",
                "surface_inset": "#26282B",
                "accent": accent, "accent_active_text": accent_active_text,
                "accent_selected_bg": "#2E3350", "accent_disabled": accent_disabled,
                "status_modified_dot": "#E09A1F", "status_modified_text": "#E0A94A",
                "status_success": "#3FA46A",
                "y2_accent": "#B27FD1", "y2_accent_bg": "#3A2E45",
                "series_palette": ["#C24141", "#6B77E8", "#3F9BB0", "#3FA46A", "#E09A1F"],
                "radius_swatch": 4, "radius_control": 5, "radius_card": 6, "radius_chip": 12,
            }
        return {
            "text_primary": "#1C1E26", "text_secondary": "#3F4350",
            "text_muted": "#6B7280", "text_hint": "#9AA0AB",
            "border_panel": "#E5E6EA", "border_control": "#DCDEE4",
            "border_subtle": "#ECEEF2",
            "surface_white": "#FFFFFF", "surface_chrome": "#FBFBFC",
            "surface_inset": "#F4F5F8",
            "accent": accent, "accent_active_text": accent_active_text,
            "accent_selected_bg": "#EEF0FB", "accent_disabled": accent_disabled,
            "status_modified_dot": "#E09A1F", "status_modified_text": "#B06A00",
            "status_success": "#3FA46A",
            "y2_accent": "#8A4BB8", "y2_accent_bg": "#F5EEFB",
            "series_palette": ["#A01818", "#4A56C6", "#2B7A8C", "#3FA46A", "#E09A1F"],
            "radius_swatch": 4, "radius_control": 5, "radius_card": 6, "radius_chip": 12,
        }

    def _on_config_event(self, data):  # signature per EventBus
        cfg = data.get("config")
        if cfg is None:
            return
        self.apply_from_config(cfg)


__all__ = ["ThemeManager", "ThemeContext"]
