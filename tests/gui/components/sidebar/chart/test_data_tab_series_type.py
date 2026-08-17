"""Tests for DataTab's per-series Series Type selector (Phase 4c)."""
import sys

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.data_tab import DataTab
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def _app_context_with_project():
    from pandaplot.app import build_app_context
    app_context = build_app_context()
    project = Project(name="Test Project")
    df = pd.DataFrame({"x": [0, 1], "y": [0, 1], "u": [1.0, -1.0], "v": [0.5, 0.5]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    app_context.app_state.load_project(project)
    return app_context, project, dataset


def test_series_type_combo_offers_only_the_chart_types_allowed_series_types():
    """A Line chart allows {LINE, SCATTER} (not BAR/HIST/VECTOR)."""
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Line Chart", chart_type="line")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"))
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    offered = {tab.series_type_combo.itemData(i) for i in range(tab.series_type_combo.count())}
    assert offered == {SeriesType.LINE, SeriesType.SCATTER}


def test_series_type_combo_selects_the_current_series_own_type():
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
                           series_type=SeriesType.LINE)
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    assert tab.series_type_combo.currentData() == SeriesType.LINE


def test_changing_the_combo_retypes_the_selected_series():
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Line Chart", chart_type="line")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"))
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    scatter_index = tab.series_type_combo.findData(SeriesType.SCATTER)
    tab.series_type_combo.setCurrentIndex(scatter_index)

    assert chart.data_series[0].series_type == SeriesType.SCATTER


def test_series_type_combo_defaults_to_the_chart_types_own_default_series_type():
    """Regression test: an untouched combo on a Vector chart must default
    to VECTOR (CHART_TYPE_SPECS["vector"].default_series_type), not
    whatever sorts alphabetically first among allowed_series_types
    ({LINE, VECTOR} -- "line" sorts before "vector"). A user who never
    touches this combo before creating a series on an empty Vector chart
    must still get a Vector series, not a Line one missing its U/V
    columns."""
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Vector Chart", chart_type="vector")
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    assert tab.series_type_combo.currentData() == SeriesType.VECTOR


def test_changing_the_combo_to_vector_shows_the_uv_fields_for_that_series():
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
                           series_type=SeriesType.LINE)
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.show()
    tab.set_project(project)
    tab.load(chart)
    QApplication.processEvents()
    assert tab.u_column_combo.isVisible() is False

    vector_index = tab.series_type_combo.findData(SeriesType.VECTOR)
    tab.series_type_combo.setCurrentIndex(vector_index)
    QApplication.processEvents()

    assert tab.u_column_combo.isVisible() is True
