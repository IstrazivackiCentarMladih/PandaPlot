"""Step 1 of the chart creation wizard: pick a chart type, see a live preview.

`ChartCanvas` (and the matplotlib it pulls in) is imported lazily inside
`_render_preview`, not at module scope, so this page stays safe to import
from anywhere in the app's menu/command wiring without eagerly loading
matplotlib (see tests/gui/test_main_menu_lazy_imports.py).
"""
from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Signal

from pandaplot.gui.core.widget_extension import PWizardPage
from pandaplot.gui.dialogs.chart.chart_role_spec import CHART_ROLE_SPECS
from pandaplot.models.state.app_context import AppContext

_SAMPLE_X = [1, 2, 3, 4, 5]
_SAMPLE_Y = [2, 3, 1, 4, 3]


class ChartTypePage(PWizardPage):
    emptyRequested = Signal()

    def __init__(self, app_context: AppContext, parent: Optional[QWidget] = None):
        super().__init__(app_context=app_context, parent=parent)
        self._preview_canvas = None
        self._initialize()

    def _init_ui(self):
        self.setTitle("Choose a chart type")
        layout = QHBoxLayout(self)

        self.type_list = QListWidget()
        for chart_type, spec in CHART_ROLE_SPECS.items():
            item = QListWidgetItem(spec.display_name)
            item.setData(1, chart_type)
            self.type_list.addItem(item)
        self.type_list.currentItemChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_list, 0)

        preview_column = QVBoxLayout()
        self.preview_container = QWidget()
        self.preview_container.setLayout(QVBoxLayout())
        preview_column.addWidget(self.preview_container, 1)

        self.empty_button = QPushButton("Create empty plot")
        self.empty_button.clicked.connect(self.emptyRequested.emit)
        preview_column.addWidget(self.empty_button, 0)

        layout.addLayout(preview_column, 1)
        self.type_list.setCurrentRow(0)

    def _apply_theme(self):
        pass

    def _on_type_changed(self, current: Optional[QListWidgetItem], _previous):
        if current is None:
            return
        self._render_preview(current.data(1))
        self.completeChanged.emit()

    def _render_preview(self, chart_type: str):
        from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas

        if self._preview_canvas is not None:
            self.preview_container.layout().removeWidget(self._preview_canvas)
            self._preview_canvas.setParent(None)
            self._preview_canvas.deleteLater()

        canvas = ChartCanvas(width=4, height=3, dpi=80)
        axes = canvas.axes
        if chart_type == "line":
            axes.plot(_SAMPLE_X, _SAMPLE_Y)
        elif chart_type == "scatter":
            axes.scatter(_SAMPLE_X, _SAMPLE_Y)
        elif chart_type == "bar":
            axes.bar(_SAMPLE_X, _SAMPLE_Y)
        elif chart_type == "hist":
            axes.hist(_SAMPLE_Y, bins=5)
        canvas.draw()

        self.preview_container.layout().addWidget(canvas)
        self._preview_canvas = canvas

    def selected_chart_type(self) -> Optional[str]:
        item = self.type_list.currentItem()
        return item.data(1) if item is not None else None

    def isComplete(self) -> bool:
        return self.selected_chart_type() is not None
