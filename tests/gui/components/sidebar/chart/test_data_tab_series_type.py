"""Tests for DataTab's per-series Series Type selector (Phase 4c)."""
import sys

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.data_tab import DataTab
from pandaplot.models.chart.error_bar_config import ErrorBarConfig
from pandaplot.models.chart.series_style import LineSeriesStyle
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
    """A Bar chart allows {BAR, SCATTER} (not LINE/HIST/VECTOR).

    LINE/SCATTER/VECTOR now all mutually allow each other (CHART_TYPE_
    SPECS), so a Line chart's combo would no longer demonstrate any
    restriction -- Bar (and Histogram) are the chart types still narrowed
    to a proper subset, so this test uses Bar to keep checking real
    allow-list enforcement rather than becoming vacuous."""
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Bar Chart", chart_type="bar")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"))
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)

    offered = {tab.series_type_combo.itemData(i) for i in range(tab.series_type_combo.count())}
    assert offered == {SeriesType.BAR, SeriesType.SCATTER}


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


def test_add_series_defaults_to_the_chart_type_even_if_a_different_typed_series_is_selected():
    """Regression test: reported live as "chart is Line type, but because
    I have selected a Scatter series, adding a new series defaults to
    Scatter instead of Line." The Series Type combo tracks whichever
    EXISTING series is selected (see _load_series_into_controls) -- a
    brand-new series must always get the chart's own default type
    (CHART_TYPE_SPECS[chart_type].default_series_type) regardless of
    what the combo happens to show from the currently-selected series."""
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Line Chart", chart_type="line")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
                           series_type=SeriesType.SCATTER)
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)
    # Sanity: selecting the existing Scatter series correctly shows
    # "Scatter" in the combo -- this is the surprising value that must
    # NOT leak into a newly-added series.
    assert tab.series_type_combo.currentData() == SeriesType.SCATTER

    tab.x_column_combo.setCurrentIndex(0)
    tab.y_column_combo.setCurrentIndex(0)
    tab._add_series()

    assert chart.data_series[-1].series_type == SeriesType.LINE
    assert isinstance(chart.data_series[-1].style, LineSeriesStyle)


def test_add_series_works_on_a_vector_chart_when_a_line_series_is_selected():
    """Regression test: reported live as "+Add series doesn't work when
    chart is vector and series is line." Root cause: a Line series (which
    Vector's spec allows) doesn't need U/V, so its own U/V combos are
    legitimately hidden and blank (_selected_series_is_vector() is False)
    -- but _add_series used to REQUIRE those same combos to be non-empty
    before creating a new (Vector-typed, chart-default) series, so the
    click silently did nothing. It must create the series anyway, even
    with empty U/V -- the resulting series can be completed afterward by
    selecting it and filling in its own now-visible U/V combos, exactly
    like apply_to's already-established empty-chart bootstrap path."""
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
                           series_type=SeriesType.LINE)
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)
    # Sanity: the Line series is selected, so U/V combos read back empty.
    assert tab.u_column_combo.currentData() in (None, "")
    assert tab.v_column_combo.currentData() in (None, "")

    tab._add_series()

    assert len(chart.data_series) == 2
    assert chart.data_series[-1].series_type == SeriesType.VECTOR


def test_uv_fields_appear_right_after_x_and_y_in_the_form():
    """Reported live: "order of information is wrong so u and v columns
    are after error columns instead after x and y columns." The form is a
    QGridLayout with explicit row numbers -- U/V must sit at the rows
    immediately following X/Y, ahead of every error-bar row."""
    app_context, project, dataset = _app_context_with_project()
    tab = DataTab(app_context=app_context)

    layout = tab._series_form_widget.layout()

    def _row_of(widget):
        index = layout.indexOf(widget)
        row, _col, _rowspan, _colspan = layout.getItemPosition(index)
        return row

    x_row = _row_of(tab.x_column_combo)
    y_row = _row_of(tab.y_column_combo)
    u_row = _row_of(tab.u_column_combo)
    v_row = _row_of(tab.v_column_combo)
    x_error_row = _row_of(tab.x_error_column_combo)

    assert x_row < y_row < u_row < v_row < x_error_row


def test_enabling_asymmetric_error_bars_defaults_minus_columns_to_the_plus_columns():
    """Reported live: "when I turn on asymetric error bars, the minus
    column is set to None, it would make more sense if it was set to the
    same column as the plus column as it reflects what is currently shown
    on the chart." Ticking the checkbox must copy each already-selected
    plus-side column into its still-empty minus-side sibling, so the
    rendered error bars don't silently change the instant asymmetric mode
    is turned on."""
    app_context, project, dataset = _app_context_with_project()
    chart = Chart(name="Line Chart", chart_type="line")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        style=LineSeriesStyle(error_bars=ErrorBarConfig(y_error_column_id=dataset.column_id("y"))),
    )
    project.add_item(chart)

    tab = DataTab(app_context=app_context)
    tab.set_project(project)
    tab.load(chart)
    tab._expand_series(0)

    y_error_index = tab.y_error_column_combo.findData(dataset.column_id("y"))
    tab.y_error_column_combo.setCurrentIndex(y_error_index)
    assert tab.y_error_minus_column_combo.currentData() in (None, "")

    tab.error_asymmetric_check.setChecked(True)

    assert tab.y_error_minus_column_combo.currentData() == dataset.column_id("y")
