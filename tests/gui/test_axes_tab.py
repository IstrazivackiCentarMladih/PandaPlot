"""Regression tests for two ordering bugs in AxesTab (axes_tab.py):

1. `_read_axis_config` used to set match-toggle checked state AFTER
   loading swatch colors from `chart.config`. `ToggleSwitch.setChecked`
   emits `toggled` unconditionally, and the toggled handlers
   (`_on_match_x_label_toggled`/`_on_match_x_colors_toggled`) pre-fill
   their swatches from X's *current* color whenever the new state is "not
   matching" -- silently clobbering a saved custom color the moment a
   chart with `y_match_x_colors=False` loaded.

2. `_on_copy_axis_settings` had the same ordering bug: it copied the
   source axis's colors into the target BEFORE setting the target's match
   toggles, so if the target's toggle changed state, the toggled handler's
   pre-fill overwrote the just-copied colors with X's instead.
"""
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.axes_tab import AxesTab
from pandaplot.models.project.items.chart import Chart


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_load_preserves_custom_y_colors_when_not_matching_x():
    """Loading a chart where Y opted out of matching X's colors, with its
    own custom spine/tick colors saved, must NOT have those colors
    replaced by X's colors just because the chart loaded."""
    chart = Chart(name="Test Chart")
    chart.update_config({
        "x_spine_color": "#111111",
        "x_major_tick_color": "#111111",
        "x_minor_tick_color": "#111111",
        "x_tick_label_color": "#111111",
        "x_label_color": "#111111",
        "y_match_x_colors": False,
        "y_spine_color": "#abcdef",
        "y_major_tick_color": "#abcdef",
        "y_minor_tick_color": "#abcdef",
        "y_tick_label_color": "#abcdef",
        "y_match_x_label_color": False,
        "y_label_color": "#fedcba",
    })

    tab = AxesTab()
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    assert y_form["match_x_colors_toggle"].isChecked() is False
    assert y_form["spine_color_row"].currentColor() == "#abcdef"
    assert y_form["major_tick_color_row"].currentColor() == "#abcdef"
    assert y_form["minor_tick_color_row"].currentColor() == "#abcdef"
    assert y_form["tick_label_color_row"].currentColor() == "#abcdef"
    assert y_form["match_x_label_toggle"].isChecked() is False
    assert y_form["label_color_row"].currentColor() == "#fedcba"


def test_copy_axis_settings_copies_source_colors_not_x_colors():
    """Copying Y2 (unmatched, with custom colors) into Y must leave Y with
    Y2's colors -- not X's -- even though copying flips Y's match toggle."""
    chart = Chart(name="Test Chart")
    chart.update_config({
        "x_spine_color": "#111111",
        "x_major_tick_color": "#111111",
        "x_minor_tick_color": "#111111",
        "x_tick_label_color": "#111111",
        "x_label_color": "#111111",
        "y2_match_x_colors": False,
        "y2_spine_color": "#00ff00",
        "y2_major_tick_color": "#00ff00",
        "y2_minor_tick_color": "#00ff00",
        "y2_tick_label_color": "#00ff00",
        "y2_match_x_label_color": False,
        "y2_label_color": "#00aa00",
        # Y starts out matching X (default), which is the state being
        # flipped away from during the copy.
    })
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y", y_axis="secondary")

    tab = AxesTab()
    tab.load(chart)

    # Sanity check: Y starts out matching X, as loaded.
    y_form = tab.axes_forms["y"]
    assert y_form["match_x_colors_toggle"].isChecked() is True

    tab._on_copy_axis_settings("y2")

    assert y_form["match_x_colors_toggle"].isChecked() is False
    assert y_form["spine_color_row"].currentColor() == "#00ff00"
    assert y_form["major_tick_color_row"].currentColor() == "#00ff00"
    assert y_form["minor_tick_color_row"].currentColor() == "#00ff00"
    assert y_form["tick_label_color_row"].currentColor() == "#00ff00"
    assert y_form["match_x_label_toggle"].isChecked() is False
    assert y_form["label_color_row"].currentColor() == "#00aa00"
