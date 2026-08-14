"""Tests for the axis title/tick label rotation controls in StyleTab's
per-axis appearance form (issue #101: adjustable axis and tick label
angles)."""
import types

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.project.items.chart import Chart


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_app_context():
    return types.SimpleNamespace(app_state=types.SimpleNamespace(current_project=None))


def test_load_chart_style_sets_rotation_spinboxes():
    chart = Chart(name="Test Chart")
    chart.update_config({
        "x_label_rotation": 30,
        "x_tick_label_rotation": -45,
    })

    tab = StyleTab(_make_app_context())
    tab.load_chart_style(chart)

    x_form = tab.axes_style_forms["x"]
    assert x_form["rotation_spin"].value() == 30
    assert x_form["tick_rotation_spin"].value() == -45


def test_rotation_spinboxes_default_when_missing_from_config():
    """X title defaults to horizontal (0); Y/Y2 titles default to vertical
    (90), matching matplotlib's own default orientation for those axes so
    existing charts don't visually change just from loading this panel.
    Tick-value rotation always defaults to horizontal (0) for every axis."""
    chart = Chart(name="Test Chart")

    tab = StyleTab(_make_app_context())
    tab.load_chart_style(chart)

    assert tab.axes_style_forms["x"]["rotation_spin"].value() == 0
    assert tab.axes_style_forms["y"]["rotation_spin"].value() == 90
    assert tab.axes_style_forms["y2"]["rotation_spin"].value() == 90
    for prefix in ("x", "y", "y2"):
        assert tab.axes_style_forms[prefix]["tick_rotation_spin"].value() == 0


def test_apply_chart_style_to_saves_rotation_values():
    chart = Chart(name="Test Chart")
    tab = StyleTab(_make_app_context())
    tab.load_chart_style(chart)

    x_form = tab.axes_style_forms["x"]
    x_form["rotation_spin"].setValue(60)
    x_form["tick_rotation_spin"].setValue(-15)

    tab.apply_chart_style_to(chart)

    assert chart.config["x_label_rotation"] == 60
    assert chart.config["x_tick_label_rotation"] == -15


def test_copy_axis_style_copies_rotation_values():
    chart = Chart(name="Test Chart")
    chart.update_config({
        "y2_label_rotation": 45,
        "y2_tick_label_rotation": 90,
    })

    tab = StyleTab(_make_app_context())
    tab.load_chart_style(chart)

    tab._on_copy_axis_style("y2")

    y_form = tab.axes_style_forms["y"]
    assert y_form["rotation_spin"].value() == 45
    assert y_form["tick_rotation_spin"].value() == 90


def test_clear_chart_style_resets_rotation_to_defaults():
    chart = Chart(name="Test Chart")
    chart.update_config({
        "x_label_rotation": 45, "x_tick_label_rotation": 45,
        "y_label_rotation": 45, "y2_label_rotation": 45,
    })

    tab = StyleTab(_make_app_context())
    tab.load_chart_style(chart)
    tab.clear_chart_style()

    assert tab.axes_style_forms["x"]["rotation_spin"].value() == 0
    assert tab.axes_style_forms["y"]["rotation_spin"].value() == 90
    assert tab.axes_style_forms["y2"]["rotation_spin"].value() == 90
    for prefix in ("x", "y", "y2"):
        assert tab.axes_style_forms[prefix]["tick_rotation_spin"].value() == 0
