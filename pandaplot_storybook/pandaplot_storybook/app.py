from __future__ import annotations

import sys

from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.state.config import ApplicationConfig
from pandaplot.services.theme.theme_manager import ThemeManager
from PySide6.QtWidgets import QApplication

from pandaplot_storybook import stories  # noqa: F401  (registers all stories)
from pandaplot_storybook.main_window import MainWindow


class _StaticConfigProvider:
    """Minimal config_provider for ThemeManager: exposes the live
    ApplicationConfig the storybook mutates directly. No on-disk
    persistence, no ConfigEvents -- MainWindow calls apply_from_config()
    itself whenever the theme switch changes.
    """

    def __init__(self, config: ApplicationConfig):
        self.config = config


def build_main_window(qt_app: QApplication) -> MainWindow:
    event_bus = EventBus()
    config = ApplicationConfig.default()
    theme_manager = ThemeManager(event_bus, config_provider=_StaticConfigProvider(config), qt_app=qt_app)
    theme_manager.apply_from_config(config)

    window = MainWindow(theme_manager=theme_manager, config=config, event_bus=event_bus)
    window.resize(1100, 700)
    return window


def run() -> int:
    app = QApplication(sys.argv)
    window = build_main_window(app)
    window.show()
    return app.exec()


__all__ = ["build_main_window", "run"]
