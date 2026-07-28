"""Regression test: DataTab.load() must preserve the selected series/fit
entry when reloading the *same* chart object (as happens after every Apply),
rather than always jumping back to index 0.

Before the fix, renaming any series other than the first one and clicking
Apply reset the live form back to series 0, so the very next edit silently
landed on the wrong entry -- a repeated rename of the same series appeared
to "not work".
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


def _project_with_two_series():
    project = Project(name="Selection Persistence Project")
    df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 4, 9]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)

    chart = Chart(name="Chart", chart_type="line")
    chart.add_data_series(dataset.id, "x", "y", label="Series A")
    chart.add_data_series(dataset.id, "x", "y", label="Series B")
    project.add_item(chart)
    return project, chart


def test_reloading_same_chart_preserves_selected_index():
    _qapp()
    app_context = build_app_context()
    project, chart = _project_with_two_series()

    data_tab = DataTab(app_context=app_context)
    data_tab.set_project(project)
    data_tab.load(chart)

    # Select the second series, as if the user expanded/edited it.
    data_tab._expanded_series_index = 1
    data_tab._expanded_card_indices.add(1)

    # Simulate the full-panel reload that follows every Apply: same chart
    # object, called again.
    data_tab.load(chart)

    assert data_tab.selected_index == 1


def test_loading_a_different_chart_resets_to_first_entry():
    _qapp()
    app_context = build_app_context()
    project, chart = _project_with_two_series()

    other_chart = Chart(name="Other Chart", chart_type="line")
    other_chart.add_data_series(chart.data_series[0].dataset_id, "x", "y", label="Only Series")
    project.add_item(other_chart)

    data_tab = DataTab(app_context=app_context)
    data_tab.set_project(project)
    data_tab.load(chart)
    data_tab._expanded_series_index = 1
    data_tab._expanded_card_indices.add(1)

    data_tab.load(other_chart)

    assert data_tab.selected_index == 0


def test_rename_persists_after_apply_reload_for_non_first_series():
    """End-to-end: renaming series B, then simulating the post-Apply reload,
    then renaming it again -- both edits must land on series B, not A."""
    _qapp()
    app_context = build_app_context()
    project, chart = _project_with_two_series()

    data_tab = DataTab(app_context=app_context)
    data_tab.set_project(project)
    data_tab.load(chart)

    # Select series B (index 1) and commit a new label.
    data_tab._expanded_series_index = 1
    data_tab._expanded_card_indices.add(1)
    data_tab._pending_label = "Renamed Once"
    data_tab._on_label_committed()
    assert chart.data_series[1].label == "Renamed Once"
    assert chart.data_series[0].label == "Series A"

    # Simulate the full-panel reload that follows Apply (same chart object).
    data_tab.load(chart)
    assert data_tab.selected_index == 1

    # Rename again -- must still hit series B.
    data_tab._pending_label = "Renamed Twice"
    data_tab._on_label_committed()
    assert chart.data_series[1].label == "Renamed Twice"
    assert chart.data_series[0].label == "Series A"
