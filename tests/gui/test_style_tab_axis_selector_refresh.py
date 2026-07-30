"""Regression test for a stale-selection bug in
StyleTab.refresh_axis_style_selector (style_tab.py): it rebuilds the Axes
selector combo with `blockSignals(True)` around `setCurrentIndex`, so
`_show_axis_style_form` never fires when the selection is forced back to "X"
(e.g. the user had Y2 selected, then the last secondary-axis series is
removed). The combo would show "X" while the Y2 form stayed visible."""
import types

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.project.items.chart import Chart, DataSeries, YAxis


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_app_context():
    return types.SimpleNamespace(app_state=types.SimpleNamespace(current_project=None))


def test_refresh_axis_style_selector_shows_x_form_when_y2_series_removed():
    chart = Chart(name="Test Chart")
    chart.data_series.append(
        DataSeries(dataset_id="ds1", y_axis=YAxis.SECONDARY)
    )

    tab = StyleTab(_make_app_context())
    tab.load_chart_style(chart)

    # Simulate the user selecting Y2 in the Axes selector while it still has
    # a secondary-axis series. `ValueComboBox.setCurrentValue()` is a silent
    # programmatic setter (blocks signals), so drive the combo's native
    # `setCurrentIndex` directly -- like a real click would -- to fire
    # `currentIndexChanged` -> `currentValueChanged` -> `_show_axis_style_form`.
    selector = tab.axes_style_selector
    selector.setCurrentIndex(selector.findData("y2"))
    assert tab.axes_style_forms["y2"]["widget"].isHidden() is False
    assert tab.axes_style_forms["x"]["widget"].isHidden() is True

    # Now the last secondary-axis series is removed and the panel refreshes
    # the selector (chart_properties_panel.py's refresh_axis_selectors path).
    chart.data_series.clear()
    tab.refresh_axis_style_selector(chart)

    assert tab.axes_style_selector.currentValue() == "x"
    assert tab.axes_style_forms["x"]["widget"].isHidden() is False
    assert tab.axes_style_forms["y2"]["widget"].isHidden() is True
