"""Tests for ChartSignalAnalysisPanel: source picker filtering, segment
index -> (x, y) preview labels, method/parameter widget wiring, the
sampling-rate pre-fill, and the async run/apply dispatch (mirroring
test_chart_analysis_panel.py and test_signal_panel.py respectively).
"""
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.analysis import SIGNAL_ANALYSES, SignalAnalysisType
from pandaplot.gui.components.sidebar.chart_signal.chart_signal_analysis_panel import (
    ChartSignalAnalysisPanel,
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
    # A known-frequency signal: 100 samples/second over 1 second, 5 Hz sine.
    t = np.linspace(0.0, 1.0, 101)
    y = np.sin(2 * np.pi * 5 * t)
    dataset = Dataset(id="ds-1", name="Data", data=pd.DataFrame({"t": t, "signal": y}))
    project.add_item(dataset)

    chart = Chart(id="chart-1", name="C")
    x_id = dataset.column_id("t")
    y_id = dataset.column_id("signal")
    chart.add_data_series(dataset_id="ds-1", x_column_id=x_id, y_column_id=y_id,
                          x_column="t", y_column="signal", label="Signal")
    project.add_item(chart)
    return project


@pytest.fixture
def app_context(project):
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    app_state = Mock(spec=AppState)
    app_state.current_project = project
    ctx.get_app_state.return_value = app_state
    return ctx


@pytest.fixture
def panel(app_context, project):
    panel = ChartSignalAnalysisPanel(app_context)
    panel.current_chart = project.find_item("chart-1")
    panel.current_chart_id = "chart-1"
    panel._populate_sources()
    return panel


class TestSourcePickerFiltering:
    """Same filtering rules as ChartAnalysisPanel (#202): series types with
    no meaningful ordered (x, y) curve are excluded from the source picker."""

    def _combo_labels(self, panel):
        return [panel.source_combo.itemText(i) for i in range(panel.source_combo.count())]

    def test_bar_series_is_excluded_from_the_source_picker(self, panel):
        panel.current_chart.data_series[0].series_type = SeriesType.BAR
        panel._populate_sources()

        assert self._combo_labels(panel) == []
        assert panel.run_btn.isEnabled() is False

    def test_line_and_scatter_series_are_offered(self, panel):
        assert any("Signal" in label for label in self._combo_labels(panel))


class TestSegmentRangeLabels:
    def test_labels_show_no_selection_placeholder_without_source(self, app_context):
        panel = ChartSignalAnalysisPanel(app_context)

        assert panel.start_value_label.text() == "–"
        assert panel.end_value_label.text() == "–"

    def test_start_label_updates_on_index_change(self, panel):
        panel.start_index.setValue(10)

        # sin(2*pi*5*0.1) == sin(pi) ~ 0 (numerically ~1e-16, formatted as such).
        assert panel.start_value_label.text().startswith("x=0.1, y=")

    def test_end_index_defaults_to_the_last_point(self, panel):
        assert panel.end_index.minimum() == 0
        assert panel.end_index.value() == 100
        assert panel.end_value_label.text() != "–"

    def test_end_label_updates_on_explicit_index(self, panel):
        panel.end_index.setValue(50)

        assert panel.end_value_label.text() != "–"

    def test_build_parameters_sends_inclusive_end_as_exclusive_boundary(self, panel):
        panel.start_index.setValue(0)
        panel.end_index.setValue(50)

        assert panel._build_parameters()["end_index"] == 51


class TestMethodDropdownAndParameterWidgets:
    def test_method_dropdown_lists_exactly_the_signal_analyses(self, panel):
        assert panel.analysis_combo.count() == len(SIGNAL_ANALYSES)
        types = {panel.analysis_combo.itemData(i) for i in range(panel.analysis_combo.count())}
        assert types == set(SIGNAL_ANALYSES.keys())

    def _select(self, panel, analysis_type: SignalAnalysisType):
        index = panel.analysis_combo.findData(analysis_type)
        assert index != -1
        panel.analysis_combo.setCurrentIndex(index)

    def test_fft_shows_sampling_rate_nfft_and_window(self, panel):
        self._select(panel, SignalAnalysisType.FFT)

        assert panel.sampling_rate is not None
        assert panel.nfft_spin is not None
        assert panel.window_combo is not None
        assert panel.nperseg_spin is None
        assert panel.height_spin is None

    def test_peaks_shows_peak_params_and_no_sampling_rate(self, panel):
        self._select(panel, SignalAnalysisType.PEAKS)

        assert panel.sampling_rate is None
        assert panel.height_spin is not None
        assert panel.distance_spin is not None
        assert panel.prominence_spin is not None
        assert panel.threshold_spin is not None

    def test_autocorrelation_has_no_sampling_rate_widget(self, panel):
        self._select(panel, SignalAnalysisType.AUTOCORRELATION)

        assert panel.sampling_rate is None


class TestSamplingRatePrefill:
    def test_prefill_reflects_median_sample_spacing_over_the_segment(self, panel):
        index = panel.analysis_combo.findData(SignalAnalysisType.FFT)
        panel.analysis_combo.setCurrentIndex(index)

        # t = linspace(0, 1, 101) -> spacing 0.01 -> sampling rate ~100 Hz.
        assert panel.sampling_rate.value() == pytest.approx(100.0, rel=1e-2)

    def test_prefill_changes_when_the_segment_changes(self, panel):
        index = panel.analysis_combo.findData(SignalAnalysisType.FFT)
        panel.analysis_combo.setCurrentIndex(index)

        panel.start_index.setValue(0)
        panel.end_index.setValue(10)  # spacing still 0.01 -> same rate, but recomputed
        first = panel.sampling_rate.value()

        # Manually overwrite, then force a recompute via a segment change --
        # this asserts the panel actively recomputes on segment change
        # (not just leaves whatever the user set).
        panel.sampling_rate.setValue(1.0)
        panel.end_index.setValue(20)

        assert panel.sampling_rate.value() == pytest.approx(first, rel=1e-2)
        assert panel.sampling_rate.value() != 1.0


class TestRunAnalysisAsyncDispatch:
    def _fake_result(self):
        result = Mock()
        result.analysis_name = "FFT"
        result.data = pd.DataFrame({"frequency": [1.0, 2.0], "magnitude": [0.1, 0.2]})
        result.metadata = {}
        return result

    def test_success_path_populates_results_and_enables_add(self, panel):
        captured = {}
        fake_command = Mock()
        fake_command.run_analysis_async = lambda on_complete: captured.update(on_complete=on_complete)
        panel._build_command = lambda: fake_command

        panel.run_analysis()

        assert panel.busy_spinner.is_running is True
        assert panel.run_btn.isEnabled() is False
        assert panel.add_btn.isEnabled() is False

        captured["on_complete"](self._fake_result(), None)

        assert panel.busy_spinner.is_running is False
        assert panel.run_btn.isEnabled() is True
        assert panel.add_btn.isEnabled() is True
        assert "FFT" in panel.results_text.toPlainText()

    def test_failure_path_shows_error(self, panel):
        captured = {}
        fake_command = Mock()
        fake_command.run_analysis_async = lambda on_complete: captured.update(on_complete=on_complete)
        panel._build_command = lambda: fake_command

        panel.run_analysis()
        captured["on_complete"](None, "boom")

        assert panel.busy_spinner.is_running is False
        assert panel.add_btn.isEnabled() is False
        assert "boom" in panel.results_text.toPlainText()


class TestRunAndAddMutualExclusion:
    """Regression coverage (mirrors SignalPanel's): Run and Add to Project
    share one busy spinner and one _pending_command slot."""

    def test_add_is_a_no_op_while_run_is_in_flight(self, panel):
        run_captured = {}
        run_command = Mock()
        run_command.run_analysis_async = lambda on_complete: run_captured.update(on_complete=on_complete)
        panel._build_command = lambda: run_command
        panel.run_analysis()
        assert panel._pending_command is run_command

        add_attempted = {}

        def _build_add_command():
            add_attempted["built"] = True
            return Mock()

        panel._build_command = _build_add_command
        panel.add_results_to_project()

        assert "built" not in add_attempted
        assert panel._pending_command is run_command

    def test_run_is_a_no_op_while_add_is_in_flight(self, panel):
        add_command = Mock()
        add_command.result = Mock()
        panel.app_context.get_command_executor.return_value.execute_command = lambda command: True
        panel._build_command = lambda: add_command
        panel.add_results_to_project()
        assert panel._pending_command is add_command

        run_attempted = {}

        def _build_run_command():
            run_attempted["built"] = True
            return Mock()

        panel._build_command = _build_run_command
        panel.run_analysis()

        assert "built" not in run_attempted
        assert panel._pending_command is add_command


class TestPopulateSourcesRespectsPendingCommand:
    """Regression: switching the active chart tab while a Run/Add-to-Project
    computation is still in flight for the previous chart used to
    re-enable the Run button via _populate_sources() (has_sources alone),
    even though _pending_command was still set -- the button looked live
    but silently no-op'd until the in-flight computation completed."""

    def test_run_button_stays_disabled_while_a_command_is_pending(self, panel):
        run_captured = {}
        run_command = Mock()
        run_command.run_analysis_async = lambda on_complete: run_captured.update(on_complete=on_complete)
        panel._build_command = lambda: run_command
        panel.run_analysis()
        assert panel._pending_command is run_command
        assert panel.run_btn.isEnabled() is False

        # Simulate switching to another (still valid) chart tab while the
        # run is still in flight.
        panel._populate_sources()

        assert panel.run_btn.isEnabled() is False

    def test_run_button_re_enables_once_pending_command_clears(self, panel):
        run_captured = {}
        run_command = Mock()
        run_command.run_analysis_async = lambda on_complete: run_captured.update(on_complete=on_complete)
        panel._build_command = lambda: run_command
        panel.run_analysis()

        run_captured["on_complete"](
            Mock(analysis_name="FFT", data=pd.DataFrame({"a": [1.0]}), metadata={}), None,
        )
        panel._populate_sources()

        assert panel.run_btn.isEnabled() is True


class TestRangeCommandCaching:
    """Regression: _range_command() used to build a brand-new
    ChartSignalAnalysisCommand on every call, defeating its own
    _resolved_xy_cache and forcing the sampling-rate pre-fill to loop
    resolve_point() once per index in the segment. It now reuses one
    instance per (chart, source) -- invalidated whenever sources are
    repopulated, since a chart update may have changed the underlying data
    -- and computes the sampling-rate default via one vectorized
    resolve_segment_x() call instead."""

    def test_range_command_is_reused_for_the_same_source(self, panel):
        first = panel._range_command("series", 0)
        second = panel._range_command("series", 0)
        assert first is second

    def test_range_command_cache_is_invalidated_on_repopulate(self, panel):
        first = panel._range_command("series", 0)
        panel._populate_sources()
        second = panel._range_command("series", 0)
        assert first is not second

    def test_sampling_rate_prefill_uses_resolve_segment_x_not_a_per_index_loop(self, panel):
        index = panel.analysis_combo.findData(SignalAnalysisType.FFT)
        panel.analysis_combo.setCurrentIndex(index)

        command = panel._range_command("series", 0)
        command.resolve_point = Mock(
            side_effect=AssertionError("resolve_point should not be used for the sampling-rate prefill")
        )

        panel._refresh_sampling_rate_default()

        command.resolve_point.assert_not_called()
