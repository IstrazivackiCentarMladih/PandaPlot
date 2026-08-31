"""Tests for ChartTransformPanel."""

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.commands.base_command import CommandResult
from pandaplot.gui.components.sidebar.chart_transform.chart_transform_panel import (
    ChartTransformPanel,
)
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def project():
    project = Project(name="P")
    t = np.linspace(0.0, 10.0, 11)
    dataset = Dataset(id="ds-1", name="Data", data=pd.DataFrame({"t": t, "sq": t ** 2}))
    project.add_item(dataset)

    chart = Chart(id="chart-1", name="C")
    x_id = dataset.column_id("t")
    y_id = dataset.column_id("sq")
    chart.add_data_series(dataset_id="ds-1", x_column_id=x_id, y_column_id=y_id,
                          x_column="t", y_column="sq", label="Squared")
    project.add_item(chart)
    return project


@pytest.fixture
def app_context(project):
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    app_state = Mock(spec=AppState)
    app_state.has_project = True
    app_state.current_project = project
    app_state.event_bus = Mock()
    ctx.get_app_state.return_value = app_state
    executor = Mock()
    executor.execute_command.side_effect = lambda cmd: cmd.execute() is CommandResult.SUCCESS
    ctx.get_command_executor.return_value = executor
    return ctx


@pytest.fixture
def panel(app_context, project):
    panel = ChartTransformPanel(app_context)
    panel.current_chart = project.find_item("chart-1")
    panel.current_chart_id = "chart-1"
    panel._populate_sources()
    return panel


class TestChartTransformPanelSourcePicker:
    def _combo_labels(self, panel):
        return [panel.source_combo.itemText(i) for i in range(panel.source_combo.count())]

    def test_line_series_is_offered(self, panel):
        assert any("Squared" in label for label in self._combo_labels(panel))

    def test_bar_series_is_excluded(self, panel):
        panel.current_chart.data_series[0].series_type = SeriesType.BAR
        panel._populate_sources()
        assert self._combo_labels(panel) == []
        assert panel.apply_btn.isEnabled() is False


class TestChartTransformPanelTarget:
    def test_default_target_is_y(self, panel):
        assert panel.target_combo.currentData() == "y"

    def test_target_x_is_selectable(self, panel):
        panel.target_combo.setCurrentIndex(1)
        assert panel.target_combo.currentData() == "x"


class TestChartTransformPanelApply:
    def test_apply_with_no_expression_shows_error(self, panel):
        panel.apply()
        assert "Select a series" in panel.preview_text.toPlainText()

    def test_preview_shows_the_result(self, panel):
        panel.expression_text.setPlainText("y * 2")
        panel.preview()
        assert "Result:" in panel.preview_text.toPlainText()

    def test_preview_shows_an_error_for_an_unsafe_expression(self, panel):
        panel.expression_text.setPlainText("__import__('os')")
        panel.preview()
        assert "Preview error" in panel.preview_text.toPlainText()

    def test_apply_creates_a_new_dataset(self, panel, project):
        panel.expression_text.setPlainText("y * 2")
        panel.apply()
        assert "Created a new dataset" in panel.preview_text.toPlainText()
        datasets = [item for item in project.get_all_items() if isinstance(item, Dataset)]
        assert len(datasets) == 2

    def test_clear_inputs_resets_the_form(self, panel):
        panel.expression_text.setPlainText("y * 2")
        panel.result_name.setText("Custom")
        panel.clear_inputs()
        assert panel.expression_text.toPlainText() == ""
        assert panel.result_name.text() == ""
