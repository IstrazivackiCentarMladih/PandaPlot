"""Regression tests for `ChartPropertiesPanel._on_project_item_renamed`.

The rename payload (`RenameItemCommand`) doesn't carry an item type, so this
handler must look the renamed item up in the project and only rebuild the
Data tab's dataset combo when the renamed item is actually a Dataset --
otherwise it does a full combo rebuild on every chart/note/folder rename too.
"""
import sys

import pandas as pd
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.chart_properties_panel import ChartPropertiesPanel
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _make_project():
    project = Project(name="Rename Filter Project")
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    dataset = Dataset(name="ds", data=df)
    project.add_item(dataset)
    chart = Chart(name="Chart", chart_type="line")
    project.add_item(chart)
    return project, dataset, chart


def test_dataset_rename_rebuilds_dataset_combo():
    _qapp()
    app_context = build_app_context()
    project, dataset, chart = _make_project()

    panel = ChartPropertiesPanel(app_context=app_context)
    panel.set_project(project)

    dataset.update_name("ds renamed")
    panel._on_project_item_renamed({"item_id": dataset.id, "new_name": "ds renamed"})

    assert panel.data_tab.dataset_combo.itemText(0) == "ds renamed"


def test_unrelated_item_rename_does_not_touch_dataset_combo(monkeypatch):
    _qapp()
    app_context = build_app_context()
    project, dataset, chart = _make_project()

    panel = ChartPropertiesPanel(app_context=app_context)
    panel.set_project(project)

    monkeypatch.setattr(panel.data_tab, "set_project", lambda *_a, **_kw: (_ for _ in ()).throw(
        AssertionError("set_project should not be called for a non-dataset rename")
    ))

    chart.update_name("Chart renamed")
    panel._on_project_item_renamed({"item_id": chart.id, "new_name": "Chart renamed"})
