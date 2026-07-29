"""Chart tab: chart identity fields (title, subtitle, chart type, histogram bins)."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.components.common.value_combo_box import ValueComboBox
from pandaplot.models.chart.chart_configuration import ChartType


class ChartTab(QWidget):
    """Chart-level identity: title, subtitle, chart type, and the
    histogram-only bins control (shown only when chart type is Histogram).

    Deliberately excludes `chart_style_card` (title/subtitle font size,
    figure/margin padding, size, dpi) -- that widget is built and owned by
    the Style tab, per the design doc, even though both live under a
    "Chart" umbrella conceptually.
    """

    configChanged = Signal()
    # Emitted on every chart-type change (including programmatic ones while
    # loading a chart), carrying the new ChartType value. Consumed by the
    # Style tab to hide the Line card for Scatter charts.
    chartTypeChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = None
        self._updating_controls = False
        # Tracks whether the loaded chart's type is one the combo can
        # represent, so an unsupported/hidden type (e.g. a saved "box" or
        # "violin" chart) isn't silently overwritten with "line" just
        # because that's what the combo defaults to for display.
        self._loaded_chart_type_supported: bool = True
        self._chart_type_touched_by_user: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        info_group = QGroupBox("Chart Information")
        info_layout = QGridLayout(info_group)
        info_layout.setSpacing(8)

        info_layout.addWidget(QLabel("Title:"), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Chart title (supports $LaTeX$ math)")
        info_layout.addWidget(self.title_edit, 0, 1, 1, 2)

        info_layout.addWidget(QLabel("Subtitle:"), 1, 0)
        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("Optional (supports $LaTeX$ math)")
        info_layout.addWidget(self.subtitle_edit, 1, 1, 1, 2)

        info_layout.addWidget(QLabel("Type:"), 2, 0)
        self.chart_type_control = ValueComboBox(
            [
                ("Scatter", ChartType.SCATTER),
                ("Line", ChartType.LINE),
                ("Bar", ChartType.BAR),
                ("Histogram", ChartType.HISTOGRAM),
            ]
        )
        info_layout.addWidget(self.chart_type_control, 2, 1, 1, 2)

        self.hist_bins_label = QLabel("Bins:")
        info_layout.addWidget(self.hist_bins_label, 3, 0)
        self.hist_bins_spin = QSpinBox()
        self.hist_bins_spin.setRange(2, 200)
        self.hist_bins_spin.setValue(20)
        self.hist_bins_spin.setToolTip("Number of bins used when chart type is Histogram")
        info_layout.addWidget(self.hist_bins_spin, 3, 1)
        self._update_hist_bins_visibility()

        layout.addWidget(info_group)
        layout.addStretch(1)

        self.title_edit.textChanged.connect(self._on_field_changed)
        self.subtitle_edit.textChanged.connect(self._on_field_changed)
        self.chart_type_control.currentValueChanged.connect(self._on_chart_type_index_changed)
        self.hist_bins_spin.valueChanged.connect(self._on_field_changed)

    def _on_chart_type_index_changed(self):
        """Handle chart type combo changes, tracking explicit user intent.

        Distinguishes a user picking a chart type from the combo being set
        programmatically while loading a chart (see _loaded_chart_type_supported).
        """
        if not self._updating_controls:
            self._chart_type_touched_by_user = True
        self._update_hist_bins_visibility()
        self.chartTypeChanged.emit(self.chart_type_control.currentValue())
        self._on_field_changed()

    def _update_hist_bins_visibility(self):
        """Show the Histogram Bins control only when the chart type is Histogram."""
        is_histogram = self.chart_type_control.currentValue() == ChartType.HISTOGRAM
        self.hist_bins_label.setVisible(is_histogram)
        self.hist_bins_spin.setVisible(is_histogram)

    def _on_field_changed(self):
        if self._chart is None or self._updating_controls:
            return
        config = self._chart.config
        config["title"] = self.title_edit.text()
        config["subtitle"] = self.subtitle_edit.text()
        config["hist_bins"] = self.hist_bins_spin.value()
        if self.chart_type_control.currentValue():
            chart_type_map = {
                ChartType.LINE: "line",
                ChartType.SCATTER: "scatter",
                ChartType.BAR: "bar",
                ChartType.HISTOGRAM: "hist",
            }
            chart_type = self.chart_type_control.currentValue()
            if chart_type in chart_type_map and (
                self._loaded_chart_type_supported or self._chart_type_touched_by_user
            ):
                self._chart.chart_type = chart_type_map[chart_type]
        self.configChanged.emit()

    def load(self, chart):
        previous_guard = self._updating_controls
        self._updating_controls = True
        self._chart = chart
        self._chart_type_touched_by_user = False
        try:
            # Note: the Title field only affects config["title"] (what
            # renders on the chart) -- it must NOT rename the chart item in
            # the project tree, which is a separate concept controlled by
            # its own rename action.
            self.title_edit.setText(chart.config.get("title", chart.name))
            self.subtitle_edit.setText(chart.config.get("subtitle", ""))

            chart_type_map = {
                "line": ChartType.LINE,
                "scatter": ChartType.SCATTER,
                "bar": ChartType.BAR,
                "hist": ChartType.HISTOGRAM,
            }
            self._loaded_chart_type_supported = chart.chart_type in chart_type_map
            chart_type = chart_type_map.get(chart.chart_type, ChartType.LINE)
            self.chart_type_control.setCurrentValue(chart_type)
            self._update_hist_bins_visibility()

            self.hist_bins_spin.setValue(chart.config.get("hist_bins", 20))
        finally:
            self._updating_controls = previous_guard

    def apply_to(self, chart):
        chart.config["title"] = self.title_edit.text()
        chart.config["subtitle"] = self.subtitle_edit.text()
        chart.config["hist_bins"] = self.hist_bins_spin.value()

        chart_type_map = {
            ChartType.LINE: "line",
            ChartType.SCATTER: "scatter",
            ChartType.BAR: "bar",
            ChartType.HISTOGRAM: "hist",
        }
        chart_type = self.chart_type_control.currentValue()
        if chart_type in chart_type_map:
            chart.chart_type = chart_type_map[chart_type]

    def clear(self):
        self._chart = None
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self.title_edit.clear()
            self.subtitle_edit.clear()
            self.chart_type_control.setCurrentValue(ChartType.SCATTER)
            self.hist_bins_spin.setValue(20)
            self._update_hist_bins_visibility()
        finally:
            self._updating_controls = previous_guard

    def apply_theme(self, tokens: dict):
        self.chart_type_control.set_tokens(tokens)
