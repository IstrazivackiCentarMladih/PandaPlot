"""Tests for DataTab's Vector chart-type support (U/V/magnitude columns)."""
import sys

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.data_tab import DataTab
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


def test_vector_fields_hidden_for_a_line_chart():
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Line Chart", chart_type="line")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"))
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    assert tab.u_column_combo.isVisible() is False
    assert tab.v_column_combo.isVisible() is False
    assert tab.magnitude_column_combo.isVisible() is False


def test_vector_fields_shown_and_populated_for_a_vector_chart():
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v"),
    )
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.show()
    tab.set_project(project)
    tab.load(chart)
    # The persistent series-config form is reparented into whichever card is
    # selected (see _rebuild_series_cards) -- Qt only flips the resulting
    # widgets' shown-state once the event loop processes that reparenting.
    QApplication.processEvents()

    assert tab.u_column_combo.isVisible() is True
    assert tab.v_column_combo.isVisible() is True
    assert tab.u_column_combo.currentData() == dataset.column_id("u")
    assert tab.v_column_combo.currentData() == dataset.column_id("v")


def test_editing_u_column_updates_the_series():
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v"),
    )
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    v_index = tab.v_column_combo.findData(dataset.column_id("u"))
    tab.v_column_combo.setCurrentIndex(v_index)

    assert chart.data_series[0].v_column_id == dataset.column_id("u")


def test_refresh_vector_fields_shows_combos_after_a_live_type_switch():
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Chart", chart_type="line")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"))
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.show()
    tab.set_project(project)
    tab.load(chart)
    QApplication.processEvents()
    assert tab.u_column_combo.isVisible() is False

    chart.chart_type = "vector"  # simulates the Chart tab combo writing directly to chart_type
    tab.refresh_vector_fields()
    QApplication.processEvents()

    assert tab.u_column_combo.isVisible() is True


def test_refresh_vector_fields_preserves_the_selected_series_u_v_magnitude():
    """Regression test: repopulating the U/V/magnitude combos (which clears
    them back to their first entry) must not desync from the still-selected
    series' actual column ids -- otherwise the next unrelated edit
    (_on_series_config_changed writes every combo's current value back to
    the series) silently overwrites a correctly-configured vector series."""
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v"),
        magnitude_column_id=dataset.column_id("x"), label="v1",
    )
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    tab.refresh_vector_fields()

    assert tab.u_column_combo.currentData() == dataset.column_id("u")
    assert tab.v_column_combo.currentData() == dataset.column_id("v")
    assert tab.magnitude_column_combo.currentData() == dataset.column_id("x")

    # An unrelated edit (e.g. toggling the Y axis) re-reads every combo's
    # current value via _on_series_config_changed -- it must not clobber
    # u/v/magnitude via now-desynced combos.
    tab._on_series_config_changed()

    series = chart.data_series[0]
    assert series.u_column_id == dataset.column_id("u")
    assert series.v_column_id == dataset.column_id("v")
    assert series.magnitude_column_id == dataset.column_id("x")
