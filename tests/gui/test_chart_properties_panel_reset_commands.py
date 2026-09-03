"""Regression tests for `ChartPropertiesPanel` Reset behavior with series commands (#313)."""


from pandaplot.app import build_app_context
from pandaplot.commands.project.chart import (
    AddSeriesCommand,
    ConvertSeriesToFitCommand,
    RemoveFitDataCommand,
    RemoveSeriesCommand,
)
from pandaplot.gui.components.sidebar.chart.chart_properties_panel import ChartPropertiesPanel
from pandaplot.models.project.items.chart import Chart, DataSeries
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project


def _setup_app_and_chart(qapp):
    app_context = build_app_context()
    project = Project(name="Test Project")
    app_context.app_state.load_project(project)

    import pandas as pd
    dataset = Dataset(name="Test Dataset")
    dataset.set_data(pd.DataFrame({
        "x": [1.0, 2.0, 3.0],
        "y": [2.0, 4.0, 6.0],
    }))
    project.add_item(dataset)

    chart = Chart(name="Test Chart")
    series = DataSeries(
        dataset_id=dataset.id,
        x_column_id=dataset.column_id("x"),
        y_column_id=dataset.column_id("y"),
        label="Series 1",
    )
    chart.data_series.append(series)
    project.add_item(chart)

    return app_context, project, dataset, chart


def test_reset_unwinds_convert_series_to_fit_command(qapp):
    app_context, project, dataset, chart = _setup_app_and_chart(qapp)
    executor = app_context.command_executor

    panel = ChartPropertiesPanel(app_context=app_context)
    panel.set_project(project)
    panel.load_chart_object(chart)

    initial_undo_depth = len(executor.undo_stack)
    assert len(chart.data_series) == 1
    assert len(chart.fit_data) == 0

    # Convert series to fit
    cmd = ConvertSeriesToFitCommand(app_context, chart_id=chart.id, series_index=0)
    assert executor.execute_command(cmd) is True
    assert len(chart.data_series) == 0
    assert len(chart.fit_data) == 1
    assert len(executor.undo_stack) == initial_undo_depth + 1

    # User clicks Reset
    panel._on_reset()

    # Verify chart and undo stack are restored to pre-conversion baseline
    assert len(chart.data_series) == 1
    assert chart.data_series[0].label == "Series 1"
    assert len(chart.fit_data) == 0
    assert len(executor.undo_stack) == initial_undo_depth

    # Subsequent undo should be no-op or undo pre-panel command, not crash or corrupt
    if executor.can_undo():
        executor.undo()
    assert len(chart.data_series) == 1 or len(chart.data_series) == 0


def test_reset_unwinds_add_and_remove_series_commands(qapp):
    app_context, project, dataset, chart = _setup_app_and_chart(qapp)
    executor = app_context.command_executor

    panel = ChartPropertiesPanel(app_context=app_context)
    panel.set_project(project)
    panel.load_chart_object(chart)

    initial_undo_depth = len(executor.undo_stack)

    # Add a second series
    series2 = DataSeries(
        dataset_id=dataset.id,
        x_column_id=dataset.column_id("x"),
        y_column_id=dataset.column_id("y"),
        label="Series 2",
    )
    add_cmd = AddSeriesCommand(app_context, chart_id=chart.id, series=series2)
    assert executor.execute_command(add_cmd) is True
    assert len(chart.data_series) == 2

    # Remove the first series
    rem_cmd = RemoveSeriesCommand(app_context, chart_id=chart.id, series_index=0)
    assert executor.execute_command(rem_cmd) is True
    assert len(chart.data_series) == 1
    assert chart.data_series[0].label == "Series 2"

    assert len(executor.undo_stack) == initial_undo_depth + 2

    # Click Reset
    panel._on_reset()

    # Baseline should be restored: 1 series ("Series 1"), 0 fits, undo stack reset
    assert len(chart.data_series) == 1
    assert chart.data_series[0].label == "Series 1"
    assert len(executor.undo_stack) == initial_undo_depth


def test_apply_and_undo_sequence_with_series_commands(qapp):
    app_context, project, dataset, chart = _setup_app_and_chart(qapp)
    executor = app_context.command_executor

    panel = ChartPropertiesPanel(app_context=app_context)
    panel.set_project(project)
    panel.load_chart_object(chart)

    initial_undo_depth = len(executor.undo_stack)

    # Convert series to fit
    convert_cmd = ConvertSeriesToFitCommand(app_context, chart_id=chart.id, series_index=0)
    assert executor.execute_command(convert_cmd) is True
    assert len(chart.data_series) == 0
    assert len(chart.fit_data) == 1

    # Edit chart title in panel UI and click Apply
    panel.chart_tab.title_edit.setText("Updated Title")
    panel._on_apply()

    assert chart.config.get("title") == "Updated Title"
    assert len(executor.undo_stack) == initial_undo_depth + 2

    # Undo 1: ApplyChartPropertiesCommand undoes panel property changes
    assert executor.undo() is True
    assert len(chart.data_series) == 0
    assert len(chart.fit_data) == 1

    # Undo 2: ConvertSeriesToFitCommand undoes fit conversion cleanly
    assert executor.undo() is True
    assert len(chart.data_series) == 1
    assert chart.data_series[0].label == "Series 1"
    assert len(chart.fit_data) == 0


def test_command_defensive_checks(qapp):
    app_context, project, dataset, chart = _setup_app_and_chart(qapp)

    # Out-of-bounds AddSeriesCommand.undo
    add_cmd = AddSeriesCommand(
        app_context,
        chart_id=chart.id,
        series=DataSeries(
            dataset_id=dataset.id,
            x_column_id=dataset.column_id("x"),
            y_column_id=dataset.column_id("y"),
        ),
    )
    add_cmd.added_index = 99
    assert add_cmd.undo().name == "FAILURE"

    # Out-of-bounds RemoveSeriesCommand.undo
    rem_cmd = RemoveSeriesCommand(app_context, chart_id=chart.id, series_index=99)
    rem_cmd.removed_series_data = chart.data_series[0]
    assert rem_cmd.undo().name == "FAILURE"

    # Out-of-bounds RemoveFitDataCommand.undo
    rem_fit_cmd = RemoveFitDataCommand(app_context, chart_id=chart.id, fit_index=99)
    rem_fit_cmd.removed_fit_data = None
    assert rem_fit_cmd.undo().name == "FAILURE"

    # Out-of-bounds ConvertSeriesToFitCommand.undo
    conv_cmd = ConvertSeriesToFitCommand(app_context, chart_id=chart.id, series_index=0)
    conv_cmd.added_fit_index = 99
    conv_cmd.removed_series = chart.data_series[0]
    assert conv_cmd.undo().name == "FAILURE"
