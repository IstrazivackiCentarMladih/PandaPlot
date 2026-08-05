"""Tests for render_wizard_preview."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.wizard_preview import render_wizard_preview


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _canvas():
    from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas
    return ChartCanvas(width=3, height=2, dpi=60)


def _project_with_dataset(dataset_id="ds-1"):
    import pandas as pd

    from pandaplot.models.project.items import Dataset

    dataset = Mock(spec=Dataset)
    dataset.id = dataset_id
    dataset.data = pd.DataFrame({"Date": [1, 2, 3], "Revenue": [10, 20, 15]})
    dataset.column_id.side_effect = lambda name: {"Date": "col-date", "Revenue": "col-rev"}.get(name)
    dataset.column_name.side_effect = lambda cid: {"col-date": "Date", "col-rev": "Revenue"}.get(cid)

    project = Mock()
    project.find_item.return_value = dataset
    return project


def test_renders_without_error_when_project_is_none():
    canvas = _canvas()

    render_wizard_preview(
        canvas, project=None, chart_type="line", series_configs=[],
        title="My Chart", subtitle="", x_label="X", y_label="Y",
        show_legend=True, show_grid=True,
    )

    assert canvas.axes.get_title() == "My Chart"


def test_sets_title_and_axis_labels():
    canvas = _canvas()

    render_wizard_preview(
        canvas, project=None, chart_type="line", series_configs=[],
        title="Voltage vs time", subtitle="", x_label="t (s)", y_label="V (mV)",
        show_legend=True, show_grid=True,
    )

    assert canvas.axes.get_title() == "Voltage vs time"
    assert canvas.axes.get_xlabel() == "t (s)"
    assert canvas.axes.get_ylabel() == "V (mV)"


def test_plots_a_real_series_when_project_resolves_it():
    canvas = _canvas()
    project = _project_with_dataset()
    series_configs = [{
        "dataset_id": "ds-1", "x_column_id": "col-date", "y_column_id": "col-rev",
        "x_error_column_id": "", "y_error_column_id": "", "error_symmetric": True,
    }]

    render_wizard_preview(
        canvas, project=project, chart_type="line", series_configs=series_configs,
        title="", subtitle="", x_label="", y_label="", show_legend=True, show_grid=True,
    )

    assert len(canvas.axes.get_lines()) == 1


def test_grid_off_disables_gridlines():
    canvas = _canvas()

    render_wizard_preview(
        canvas, project=None, chart_type="line", series_configs=[],
        title="", subtitle="", x_label="", y_label="", show_legend=True, show_grid=False,
    )

    assert not canvas.axes.xaxis.get_gridlines()[0].get_visible()
