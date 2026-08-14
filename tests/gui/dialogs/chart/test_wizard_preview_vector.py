"""Tests for the wizard Labels step's Vector preview."""
import sys

import pandas as pd
from matplotlib.quiver import Quiver
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas
from pandaplot.gui.dialogs.chart.wizard_preview import render_wizard_preview
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def test_vector_preview_with_no_series_falls_back_to_sample_quiver():
    _qapp()
    canvas = ChartCanvas(width=4, height=3, dpi=80)

    render_wizard_preview(canvas, None, "vector", [], "Title", "", "X", "Y", True, True)

    quivers = [c for c in canvas.axes.collections if isinstance(c, Quiver)]
    assert len(quivers) == 1


def test_vector_preview_with_a_configured_series_draws_real_data():
    _qapp()
    canvas = ChartCanvas(width=4, height=3, dpi=80)
    project = Project(name="Preview Project")
    df = pd.DataFrame({"x": [0, 1], "y": [0, 1], "u": [1.0, -1.0], "v": [0.5, 0.5]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)

    series_configs = [{
        "dataset_id": dataset.id,
        "x_column_id": dataset.column_id("x"), "y_column_id": dataset.column_id("y"),
        "u_column_id": dataset.column_id("u"), "v_column_id": dataset.column_id("v"),
    }]

    render_wizard_preview(canvas, project, "vector", series_configs, "Title", "", "X", "Y", True, True)

    quivers = [c for c in canvas.axes.collections if isinstance(c, Quiver)]
    assert len(quivers) == 1
