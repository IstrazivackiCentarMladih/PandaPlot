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


def test_fit_button_enabled_state_matches_scipy_availability(app_context):
    # Directly covers the construction-order-sensitive `enabled=self.scipy_available`
    # retrofit: fit_button's enabled state must reflect scipy_available as computed
    # at construction time, not some later/default value.
    #
    # A valid series with enough data points must be loaded first: the fit
    # button is also gated on data availability (see
    # test_fit_button_disabled_when_data_is_insufficient), so with no chart
    # loaded the button is disabled regardless of scipy_available.
    dataset, chart = _make_dataset_and_chart_with_id_only_series()
    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.load_chart_object(chart)

    assert panel.fit_button.isEnabled() == panel.scipy_available


def test_fit_button_disabled_when_data_is_insufficient(fit_panel):
    assert fit_panel.fit_button.isEnabled() is False


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
    panel.load_chart_object(chart_a)

    panel.fit_results = _make_fake_fit_result()
    panel.apply_button.setEnabled(True)

    panel.load_chart_object(chart_b)

    assert panel.fit_results is None
    assert panel.apply_button.isEnabled() is False


def test_load_chart_object_calls_get_current_data_exactly_once(app_context):
    """Regression test (PR review): populating series_combo in
    load_chart_object() used to fire currentIndexChanged mid-update (via
    clear()/addItem()), triggering get_current_data() multiple times for
    the same load and producing duplicate/misleading log warnings for one
    state change. blockSignals() fixed it; this pins the fix down so a
    regression (e.g. removing blockSignals, or moving the explicit
    _on_series_changed() call back inside an `if count() > 0` guard) fails
    a test instead of silently reintroducing the duplicate calls."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project

    call_count = 0
    original_get_current_data = panel.get_current_data

    def _counting_get_current_data():
        nonlocal call_count
        call_count += 1
        return original_get_current_data()

    panel.get_current_data = _counting_get_current_data

    panel.load_chart_object(chart)

    assert call_count == 1


def test_current_project_reflects_app_state_without_explicit_sync(app_context):
    """`current_project` must be a live read of app_state, not a cache that
    needs an explicit setter call to stay in sync (see issue #246 follow-up:
    every real call site was already re-deriving the same value moments
    later via load_chart_object, making the old set_project() cache
    write-only and pointless)."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()
    project_a = Mock()
    project_a.find_item = Mock(return_value=dataset)
    project_b = Mock()
    project_b.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project_a
    panel.load_chart_object(chart)

    assert panel.current_project is project_a

    # Swap the project directly on app_state, with no set_project() call.
    panel.app_context.app_state.current_project = project_b

    assert panel.current_project is project_b


def test_get_current_data_returns_none_when_project_goes_away(app_context):
    """A project that disappears out from under an already-loaded chart
    (e.g. project closed) must make get_current_data() return None, even
    though series_combo still has a selected series -- proving there's no
    stale cached project keeping stale data usable."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()
    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.load_chart_object(chart)

    assert panel.get_current_data() is not None  # sanity check: data loads fine first

    panel.app_context.app_state.current_project = None

    assert panel.series_combo.currentData() is not None  # series selection untouched
    assert panel.get_current_data() is None


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


def test_on_tab_changed_skips_work_while_panel_not_visible(app_context):
    """Regression test for issue #246: FitPanel must not do get_current_data()
    work (via load_chart_object) on tab-change events while it isn't the
    visible sidebar panel."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(side_effect=lambda item_id: chart if item_id == chart.id else dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project

    assert panel.isVisible() is False

    panel._on_tab_changed({"tab_type": "chart", "tab_id": chart.id})

    assert panel.current_chart is None
    assert panel.series_combo.count() == 0


def test_on_tab_changed_resyncs_when_panel_becomes_visible(app_context):
    """The tab-change event skipped while hidden must be replayed once the
    panel is shown again, so its context catches up."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(side_effect=lambda item_id: chart if item_id == chart.id else dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project

    panel._on_tab_changed({"tab_type": "chart", "tab_id": chart.id})
    assert panel.current_chart is None

    panel.show()
    QApplication.processEvents()

    assert panel.current_chart is not None
    assert panel.current_chart.id == chart.id
    assert panel.series_combo.count() == len(chart.data_series)

    panel.close()


def test_on_chart_updated_skips_work_while_panel_not_visible(app_context):
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project

    assert panel.isVisible() is False

    panel._on_chart_updated({"chart": chart})

    assert panel.current_chart is None
    assert panel.series_combo.count() == 0


def test_reshowing_panel_without_new_tab_change_preserves_fit_results(app_context):
    """Regression test: showEvent must not replay a tab-change event that
    was already applied while the panel was visible -- otherwise switching
    to another sidebar panel and back would silently wipe completed fit
    results even though nothing changed while the Fit panel was hidden."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(side_effect=lambda item_id: chart if item_id == chart.id else dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project

    panel.show()
    QApplication.processEvents()

    panel._on_tab_changed({"tab_type": "chart", "tab_id": chart.id})
    panel.fit_results = _make_fake_fit_result()
    panel.apply_button.setEnabled(True)

    # Simulate switching to another sidebar panel and back -- no new
    # tab-change event occurs in between.
    panel.hide()
    QApplication.processEvents()
    panel.show()
    QApplication.processEvents()

    assert panel.fit_results is not None
    assert panel.apply_button.isEnabled() is True

    panel.close()


def test_chart_updated_while_hidden_refreshes_chart_on_show(app_context):
    """A chart update skipped while the panel is hidden -- with no
    tab-change event at all in this scenario, pending or otherwise -- must
    still be picked up once the panel becomes visible again. Seeds context
    via load_chart_object() directly (not _on_tab_changed) so this only
    exercises the chart-refresh path, not the tab-change-replay path."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(side_effect=lambda item_id: chart if item_id == chart.id else dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project

    panel.load_chart_object(chart)
    panel.show()
    QApplication.processEvents()
    panel.hide()
    QApplication.processEvents()

    # Chart gains a second series while the panel is hidden; find_item
    # keeps returning the same (mutated) chart object.
    x_id = dataset.column_id("time")
    y_id = dataset.column_id("value")
    chart.add_data_series(dataset_id=dataset.id, x_column_id=x_id, y_column_id=y_id, label="second series")

    panel._on_chart_updated({"chart": chart})
    assert panel.series_combo.count() == 1  # not yet refreshed while hidden

    panel.show()
    QApplication.processEvents()

    assert panel.series_combo.count() == 2

    panel.close()


def test_chart_updated_for_unrelated_chart_while_hidden_does_not_trigger_refresh(app_context):
    """Regression test: a CHART_UPDATED event for some *other* chart while
    the Fit panel is hidden must not mark a refresh as owed -- otherwise an
    unrelated chart edit elsewhere would cause the panel to reload its own
    chart (wiping fit results) the next time it's shown, for no reason."""
    dataset, chart = _make_dataset_and_chart_with_id_only_series()
    _, other_chart = _make_dataset_and_chart_with_id_only_series()
    other_chart.id = "chart-2"

    project = Mock()
    project.find_item = Mock(side_effect=lambda item_id: chart if item_id == chart.id else dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project

    panel.load_chart_object(chart)
    panel.fit_results = _make_fake_fit_result()
    panel.apply_button.setEnabled(True)

    panel.show()
    QApplication.processEvents()
    panel.hide()
    QApplication.processEvents()

    panel._on_chart_updated({"chart": other_chart})
    assert panel._needs_chart_refresh is False

    panel.show()
    QApplication.processEvents()

    assert panel.fit_results is not None
    assert panel.apply_button.isEnabled() is True

    panel.close()


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
    panel.load_chart_object(chart)

    panel.fit_results = _make_fake_fit_result()
    panel.apply_button.setEnabled(True)

    panel.series_combo.setCurrentIndex(1)

    assert panel.fit_results is None
    assert panel.apply_button.isEnabled() is False


def test_range_controls_start_in_auto_mode(fit_panel):
    assert fit_panel.range_auto_check.isChecked() is True
    assert fit_panel.range_min_spin.isEnabled() is False
    assert fit_panel.range_max_spin.isEnabled() is False


def test_unchecking_auto_enables_range_spinboxes_and_seeds_data_range(app_context):
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.load_chart_object(chart)

    panel.range_auto_check.setChecked(False)

    assert panel.range_min_spin.isEnabled() is True
    assert panel.range_max_spin.isEnabled() is True
    assert panel.range_min_spin.value() == 1.0  # min of the "time" column [1, 2, 3, 4]
    assert panel.range_max_spin.value() == 4.0  # max of the "time" column


def test_invalid_range_disables_fit_button_and_shows_warning(app_context):
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.load_chart_object(chart)

    # isVisible() only reflects the widget's own setVisible() flag once the
    # panel itself has actually been shown (Qt reports False for any
    # descendant of a never-shown top-level regardless of its own flag).
    panel.show()
    QApplication.processEvents()

    panel.range_auto_check.setChecked(False)
    panel.range_min_spin.setValue(10.0)
    panel.range_max_spin.setValue(5.0)

    assert panel.fit_button.isEnabled() is False
    assert panel.range_warning_label.isVisible() is True

    panel.close()


def test_perform_fit_passes_custom_range_to_command(app_context):
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.load_chart_object(chart)

    panel.range_auto_check.setChecked(False)
    panel.range_min_spin.setValue(-5.0)
    panel.range_max_spin.setValue(10.0)

    executed = {}

    def _capture_execute(command):
        executed["command"] = command
        return True

    panel.app_context.get_command_executor.return_value.execute_command = _capture_execute

    panel._perform_fit()

    command = executed["command"]
    assert command.x_min == -5.0
    assert command.x_max == 10.0


def test_perform_fit_passes_none_range_when_auto(app_context):
    dataset, chart = _make_dataset_and_chart_with_id_only_series()

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    panel = FitPanel(app_context)
    panel.app_context.app_state = Mock()
    panel.app_context.app_state.current_project = project
    panel.load_chart_object(chart)

    executed = {}

    def _capture_execute(command):
        executed["command"] = command
        return True

    panel.app_context.get_command_executor.return_value.execute_command = _capture_execute

    panel._perform_fit()

    command = executed["command"]
    assert command.x_min is None
    assert command.x_max is None
