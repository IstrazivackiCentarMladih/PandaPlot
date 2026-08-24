"""Regression test: editing a series' error columns on the Data tab must
re-emit `seriesSelected` so the Style tab (a different tab, with no other way
to learn about this edit) re-checks whether its Error Bars card should show.
"""
import sys

import pandas as pd
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.tabs.data_tab import DataTab
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _project_with_series():
    project = Project(name="Error Column Sync Project")
    df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 4, 9], "yerr": [0.1, 0.2, 0.3]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)

    chart = Chart(name="Chart", chart_type="line")
    chart.add_data_series(
        dataset.id,
        x_column_id=dataset.column_id("x"),
        y_column_id=dataset.column_id("y"),
        label="Series A",
    )
    project.add_item(chart)
    return project, chart, dataset


def test_selecting_an_error_column_reemits_series_selected():
    _qapp()
    app_context = build_app_context()
    project, chart, dataset = _project_with_series()

    data_tab = DataTab(app_context=app_context)
    data_tab.set_project(project)
    data_tab.load(chart)

    seen = []
    data_tab.seriesSelected.connect(lambda kind, obj: seen.append((kind, obj)))

    yerr_index = data_tab.y_error_column_combo.findData(dataset.column_id("yerr"))
    assert yerr_index >= 0
    data_tab.y_error_column_combo.setCurrentIndex(yerr_index)

    assert seen, "expected seriesSelected to be re-emitted after an error-column edit"
    kind, obj = seen[-1]
    assert kind == "series"
    assert obj is chart.data_series[0]
    assert obj.style.error_bars.y_error_column_id == dataset.column_id("yerr")
