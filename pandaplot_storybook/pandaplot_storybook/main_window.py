from __future__ import annotations

from pandaplot.gui.components.common.segmented_control import SegmentedControl
from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.events.event_types import ThemeEvents
from pandaplot.models.state.config import ApplicationConfig, Theme
from pandaplot.services.theme.theme_manager import ThemeManager
from PySide6.QtWidgets import QListWidget, QMainWindow, QSplitter, QVBoxLayout, QWidget

from pandaplot_storybook.controls import ControlsPanel
from pandaplot_storybook.registry import StoryDef, all_story_names, get_story

_THEME_OPTIONS = [("Light", "light"), ("Dark", "dark"), ("System", "system")]


class MainWindow(QMainWindow):
    def __init__(
        self,
        theme_manager: ThemeManager,
        config: ApplicationConfig,
        event_bus: EventBus,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("PandaPlot Storybook")
        self._theme_manager = theme_manager
        self._config = config
        self._current_story_def: StoryDef | None = None
        self._current_story_name: str | None = None
        self._current_controls_panel: ControlsPanel | None = None

        self._sidebar = QListWidget()
        self._sidebar.setObjectName("storySidebar")
        self._sidebar.addItems(all_story_names())
        self._sidebar.currentTextChanged.connect(self._on_story_selected)

        self._preview_container = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_container)

        self._controls_host = QWidget()
        self._controls_host_layout = QVBoxLayout(self._controls_host)

        splitter = QSplitter()
        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._preview_container)
        splitter.addWidget(self._controls_host)
        splitter.setSizes([200, 500, 300])

        theme_switch = SegmentedControl(list(_THEME_OPTIONS))
        theme_switch.setCurrentValue(config.appearance.theme.value)
        theme_switch.currentValueChanged.connect(self.set_theme)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.addWidget(theme_switch)
        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        event_bus.subscribe(ThemeEvents.THEME_CHANGED, lambda _data: self._refresh_preview())

        if self._sidebar.count():
            self._sidebar.setCurrentRow(0)

    def current_preview_widget(self) -> QWidget | None:
        if self._preview_layout.count() == 0:
            return None
        return self._preview_layout.itemAt(0).widget()

    def set_theme(self, theme_value: str) -> None:
        self._config.appearance.theme = Theme(theme_value)
        self._theme_manager.apply_from_config(self._config)

    def _on_story_selected(self, name: str) -> None:
        if not name:
            return
        self._current_story_name = name
        self._current_story_def = get_story(name)
        self._rebuild_controls_panel()
        self._refresh_preview()

    def _rebuild_controls_panel(self) -> None:
        self._clear_layout(self._controls_host_layout)
        assert self._current_story_def is not None
        panel = ControlsPanel(self._current_story_def.controls)
        panel.valuesChanged.connect(lambda _values: self._refresh_preview())
        self._controls_host_layout.addWidget(panel)
        self._current_controls_panel = panel

    def _refresh_preview(self) -> None:
        if self._current_story_def is None:
            return
        self._clear_layout(self._preview_layout)
        values = self._current_controls_panel.values() if self._current_controls_panel else {}
        tokens = self._theme_manager.get_design_tokens()
        widget = self._current_story_def.make_widget(values, tokens)
        if not isinstance(widget, QWidget):
            raise TypeError(f"Story '{self._current_story_name}' returned {widget!r}, expected a QWidget")
        if hasattr(widget, "set_tokens"):
            widget.set_tokens(tokens)
        self._preview_layout.addWidget(widget)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


__all__ = ["MainWindow"]
