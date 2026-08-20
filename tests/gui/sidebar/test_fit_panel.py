"""Smoke tests for FitPanel construction.

FitPanel moved its `apply_button`/`fit_button`/`clear_button` `.clicked.connect(...)`
calls into the constructor via PButton's `on_click=`/`enabled=` params. That made
construction order matter: `fit_button` is built with `enabled=self.scipy_available`,
which requires `self.scipy_available` to already be assigned before
`_create_action_buttons` runs. Nothing previously constructed FitPanel in tests, so a
future construction-order regression (e.g. reordering the scipy check after UI setup)
would go unnoticed. These tests just build the panel and check the buttons exist.
"""
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.commands.project.chart.apply_fit_command import ApplyFitCommand
from pandaplot.gui.components.common.p_button import PButton
from pandaplot.gui.components.sidebar.fit.fit_panel import FitPanel
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.state.app_context import AppContext
from pandaplot.services.fit.fit_service import FitResult


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def app_context():
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    return ctx


@pytest.fixture
def fit_panel(app_context):
    return FitPanel(app_context)


def test_fit_panel_constructs_with_expected_buttons(fit_panel):
    assert isinstance(fit_panel.fit_button, PButton)
    assert isinstance(fit_panel.apply_button, PButton)
    assert isinstance(fit_panel.clear_button, PButton)


def test_fit_button_enabled_state_matches_scipy_availability(fit_panel):
    # Directly covers the construction-order-sensitive `enabled=self.scipy_available`
    # retrofit: fit_button's enabled state must reflect scipy_available as computed
    # at construction time, not some later/default value.
    assert fit_panel.fit_button.isEnabled() == fit_panel.scipy_available


def test_apply_button_starts_disabled(fit_panel):
    assert fit_panel.apply_button.isEnabled() is False


def test_clear_button_click_invokes_clear_results(app_context):
    panel = FitPanel(app_context)
    panel.results_text.setPlainText("some results")

    panel.clear_button.click()

    assert panel.results_text.toPlainText() == ""


def _make_dataset_and_chart_with_id_only_series():
    """Build a Dataset + Chart whose series references columns only via ids.

    This mirrors what the wizard / "+Add series" actually produce: the
    legacy ``x_column``/``y_column`` name fields are left empty, and only
    ``x_column_id``/``y_column_id`` are populated.
    """
    df = pd.DataFrame({"time": [1, 2, 3, 4], "value": [10, 20, 30, 40]})
    dataset = Dataset(id="ds-1", name="dataset", data=df)
    x_id = dataset.column_id("time")
    y_id = dataset.column_id("value")
    assert x_id is not None
    assert y_id is not None

    chart = Chart(id="chart-1", name="chart")
    chart.add_data_series(dataset_id=dataset.id, x_column_id=x_id, y_column_id=y_id)
    return dataset, chart


def _make_fake_fit_result():
    return FitResult(
        fit_type="Linear",
        parameters=np.array([1.0, 0.0]),
        errors=np.array([0.1, 0.1]),
        param_names=["a", "b"],
        params={"a": 1.0, "b": 0.0},
        r_squared=0.99,
        x_fit=np.array([1.0, 2.0]),
        y_fit=np.array([1.0, 2.0]),
        x_data=np.array([1.0, 2.0]),
        y_data=np.array([1.0, 2.0]),
        covariance=np.eye(2),
    )


def test_get_current_data_resolves_id_only_series(app_context):
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.set_project(project)
    panel.load_chart_object(chart)

    result = panel.get_current_data()

    assert result is not None
    df, mask, x_data, y_data, series = result
    assert len(x_data) == 4
    assert len(y_data) == 4


def test_load_chart_object_clears_stale_fit_results_across_charts(app_context):
    dataset, chart_a = _make_dataset_and_chart_with_id_only_series()
    _, chart_b = _make_dataset_and_chart_with_id_only_series()
    chart_b.id = "chart-2"

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.set_project(project)
    panel.load_chart_object(chart_a)

    panel.fit_results = _make_fake_fit_result()
    panel.apply_button.setEnabled(True)

    panel.load_chart_object(chart_b)

    assert panel.fit_results is None
    assert panel.apply_button.isEnabled() is False


def test_apply_fit_resolves_id_only_series_columns(app_context):
    """`_apply_fit` must resolve the id-only series' columns via
    `resolve_series_column` (not read the empty legacy name fields directly),
    and must carry the raw column ids through to the `ApplyFitCommand` it
    executes alongside the resolved names, so downstream axis/series pairing
    in chart_editor (which matches by column name) doesn't misattribute the
    fit to the wrong series when several id-only series share empty legacy
    names.
    """
    dataset, chart = _make_dataset_and_chart_with_id_only_series()
    series = chart.data_series[0]

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.set_project(project)
    panel.load_chart_object(chart)

    panel.fit_results = _make_fake_fit_result()

    executed = {}

    def _capture_execute(command):
        executed["command"] = command
        return True

    panel.app_context.get_command_executor.return_value.execute_command = _capture_execute

    panel._apply_fit()

    command = executed["command"]
    assert isinstance(command, ApplyFitCommand)
    assert command.source_dataset_id == series.dataset_id
    assert command.source_x_column == "time"
    assert command.source_y_column == "value"
    assert command.source_x_column_id == series.x_column_id
    assert command.source_y_column_id == series.y_column_id


def test_on_series_changed_clears_stale_fit_results_within_same_chart(app_context):
    dataset, chart = _make_dataset_and_chart_with_id_only_series()
    x_id = dataset.column_id("time")
    y_id = dataset.column_id("value")
    chart.add_data_series(dataset_id=dataset.id, x_column_id=x_id, y_column_id=y_id, label="second series")

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.set_project(project)
    panel.load_chart_object(chart)

    panel.fit_results = _make_fake_fit_result()
    panel.apply_button.setEnabled(True)

    panel.series_combo.setCurrentIndex(1)

    assert panel.fit_results is None
    assert panel.apply_button.isEnabled() is False
