"""Tests for AnalyzeFitCommand (derivative/integral/arc-length on fitted curves)."""

from unittest.mock import Mock

import numpy as np
import pytest

from pandaplot.analysis import AnalysisType
from pandaplot.commands.project.chart.analyze_fit_command import AnalyzeFitCommand
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project
from pandaplot.models.state import AppContext, AppState


@pytest.fixture
def ctx():
    project = Project(name="P")
    chart = Chart(id="chart-1", name="C")
    x = np.linspace(0.0, 10.0, 101)
    chart.add_fit_data(
        source_dataset_id="ds-1", fit_type="quadratic",
        x_data=x, y_data=x ** 2, label="Quadratic Fit", source_x_column="t",
    )
    project.add_item(chart)

    app_context = Mock(spec=AppContext)
    app_state = Mock(spec=AppState)
    app_state.has_project = True
    app_state.current_project = project
    app_state.event_bus = Mock()
    app_context.get_app_state.return_value = app_state
    return app_context, project


class TestAnalyzeFitCommand:
    def test_derivative_creates_dataset(self, ctx):
        app_context, project = ctx
        command = AnalyzeFitCommand(app_context, "chart-1", 0, AnalysisType.DERIVATIVE)
        assert command.execute() is True

        result = project.find_item(command.result_dataset_id)
        assert result is not None
        # Columns: source x label + derivative label.
        assert "t" in result.data.columns
        deriv_col = [c for c in result.data.columns if c != "t"][0]
        # d/dt of t^2 = 2t; check mid-curve.
        mid = len(result.data) // 2
        assert result.data[deriv_col].iloc[mid] == pytest.approx(2 * result.data["t"].iloc[mid], abs=0.2)

    def test_integral_total(self, ctx):
        app_context, project = ctx
        command = AnalyzeFitCommand(app_context, "chart-1", 0, AnalysisType.INTEGRAL)
        assert command.execute() is True
        result = project.find_item(command.result_dataset_id)
        int_col = [c for c in result.data.columns if c != "t"][0]
        # Integral of t^2 from 0..10 = 1000/3; final cumulative value.
        assert result.data[int_col].iloc[-1] == pytest.approx(1000 / 3, rel=1e-3)

    def test_arc_length_line_on_plot(self, ctx):
        app_context, project = ctx
        command = AnalyzeFitCommand(app_context, "chart-1", 0, AnalysisType.ARC_LENGTH)
        assert command.execute() is True
        result = project.find_item(command.result_dataset_id)
        arc_col = [c for c in result.data.columns if c != "t"][0]
        exact = 0.5 * (10 * np.sqrt(1 + 400) + 0.5 * np.arcsinh(20))
        assert result.data[arc_col].iloc[-1] == pytest.approx(exact, rel=1e-3)

    def test_segment_restricts_range(self, ctx):
        app_context, project = ctx
        command = AnalyzeFitCommand(
            app_context, "chart-1", 0, AnalysisType.INTEGRAL, start_index=0, end_index=51
        )
        assert command.execute() is True
        result = project.find_item(command.result_dataset_id)
        # 51 points of the 101-point curve (t in [0, 5]).
        assert len(result.data) == 51
        assert result.data["t"].iloc[-1] == pytest.approx(5.0)

    def test_undo_removes_dataset(self, ctx):
        app_context, project = ctx
        command = AnalyzeFitCommand(app_context, "chart-1", 0, AnalysisType.DERIVATIVE)
        command.execute()
        new_id = command.result_dataset_id
        assert project.find_item(new_id) is not None
        assert command.undo() is True
        assert project.find_item(new_id) is None

    def test_invalid_fit_index_fails(self, ctx):
        app_context, _ = ctx
        command = AnalyzeFitCommand(app_context, "chart-1", 5, AnalysisType.DERIVATIVE)
        assert command.execute() is False
