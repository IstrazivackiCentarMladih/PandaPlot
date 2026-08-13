from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.state.config import ApplicationConfig
from pandaplot.services.theme.theme_manager import ThemeManager
from PySide6.QtWidgets import QListWidget

import pandaplot_storybook.stories  # noqa: F401  (registers all stories)
from pandaplot_storybook.main_window import MainWindow


def _make_window(qtbot):
    event_bus = EventBus()
    config = ApplicationConfig.default()
    theme_manager = ThemeManager(event_bus, config_provider=_StaticConfigProvider(config))
    window = MainWindow(theme_manager=theme_manager, config=config, event_bus=event_bus)
    qtbot.addWidget(window)
    return window


class _StaticConfigProvider:
    def __init__(self, config):
        self.config = config


def test_sidebar_lists_every_registered_story(qtbot):
    window = _make_window(qtbot)
    sidebar = window.findChild(QListWidget, "storySidebar")
    assert sidebar is not None
    names = {sidebar.item(i).text() for i in range(sidebar.count())}
    assert "PButton" in names
    assert "ToggleSwitch" in names


def test_selecting_a_story_populates_a_preview(qtbot):
    window = _make_window(qtbot)
    sidebar = window.findChild(QListWidget, "storySidebar")
    row = [sidebar.item(i).text() for i in range(sidebar.count())].index("PButton")
    sidebar.setCurrentRow(row)
    assert window.current_preview_widget() is not None


def test_switching_theme_rebuilds_the_preview(qtbot):
    window = _make_window(qtbot)
    sidebar = window.findChild(QListWidget, "storySidebar")
    row = [sidebar.item(i).text() for i in range(sidebar.count())].index("ToggleSwitch")
    sidebar.setCurrentRow(row)
    first_widget = window.current_preview_widget()

    window.set_theme("dark")

    second_widget = window.current_preview_widget()
    assert second_widget is not None
    assert second_widget is not first_widget
