"""Regression tests for two ordering bugs in AxesTab (axes_tab.py):

1. `_read_axis_config` used to set match-toggle checked state AFTER
   loading swatch colors from `chart.config`. `ToggleSwitch.setChecked`
   emits `toggled` unconditionally, and the toggled handler
   (`_on_match_x_colors_toggled`) pre-fills its swatches from X's
   *current* color whenever the new state is "not matching" -- silently
   clobbering a saved custom color the moment a chart with
   `y_match_x_colors=False` loaded.

2. `_on_copy_axis_settings` had the same ordering bug: it copied the
   source axis's colors into the target BEFORE setting the target's match
   toggles, so if the target's toggle changed state, the toggled handler's
   pre-fill overwrote the just-copied colors with X's instead.
"""
import types

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.axes_tab import AxesTab
from pandaplot.models.project.items.chart import Chart, DataSeries
from pandaplot.models.project.items.dataset import Dataset


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_app_context(project=None):
    """Minimal stand-in exposing the one attribute AxesTab reads:
    `app_context.app_state.current_project` (consulted by
    `_refresh_range_display`). None here means `compute_axis_data_range`
    can't resolve any series and falls back to (0.0, 1.0), which is fine
    since these tests don't assert on the Range card's min/max values."""
    return types.SimpleNamespace(app_state=types.SimpleNamespace(current_project=project))


class _FakeProject:
    """Minimal stand-in for a project, exposing only the `find_item` lookup
    `compute_axis_data_range` -> `resolve_series_data` needs."""

    def __init__(self, datasets):
        self._datasets = {d.id: d for d in datasets}

    def find_item(self, item_id):
        return self._datasets.get(item_id)


def _make_dataset(id_, x, y):
    import pandas as pd
    ds = Dataset(id=id_, name=id_)
    ds.data = pd.DataFrame({"x": x, "y": y})
    return ds


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
        "y_match_x_colors": False,
        "y_spine_color": "#abcdef",
        "y_major_tick_color": "#abcdef",
        "y_minor_tick_color": "#abcdef",
        "y_tick_label_color": "#abcdef",
    })

    tab = AxesTab(_make_app_context())
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    assert y_form["match_x_colors_toggle"].isChecked() is False
    assert y_form["spine_color_row"].currentColor() == "#abcdef"
    assert y_form["major_tick_color_row"].currentColor() == "#abcdef"
    assert y_form["minor_tick_color_row"].currentColor() == "#abcdef"
    assert y_form["tick_label_color_row"].currentColor() == "#abcdef"


def test_copy_axis_settings_copies_source_colors_not_x_colors():
    """Copying Y2 (unmatched, with custom colors) into Y must leave Y with
    Y2's colors -- not X's -- even though copying flips Y's match toggle."""
    chart = Chart(name="Test Chart")
    chart.update_config({
        "x_spine_color": "#111111",
        "x_major_tick_color": "#111111",
        "x_minor_tick_color": "#111111",
        "x_tick_label_color": "#111111",
        "y2_match_x_colors": False,
        "y2_spine_color": "#00ff00",
        "y2_major_tick_color": "#00ff00",
        "y2_minor_tick_color": "#00ff00",
        "y2_tick_label_color": "#00ff00",
        # Y starts out matching X (default), which is the state being
        # flipped away from during the copy.
    })
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y", y_axis="secondary")

    tab = AxesTab(_make_app_context())
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


def test_selecting_custom_log_base_reveals_spin_and_round_trips_into_config():
    """Selecting "Custom..." on the log-base combo reveals the custom spin
    box, and the spin box's value round-trips into
    chart.config[f"{prefix}_log_base"] via the real _on_field_changed ->
    _write_axis_config -> _resolve_log_base path."""
    chart = Chart(name="Test Chart")
    chart.update_config({"y_scale": "log"})

    tab = AxesTab(_make_app_context())
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    custom_index = y_form["log_base_combo"].findData("custom")
    y_form["log_base_combo"].setCurrentIndex(custom_index)

    assert y_form["log_base_custom_spin"].isHidden() is False

    y_form["log_base_custom_spin"].setValue(4.2)

    assert chart.config["y_log_base"] == 4.2


def test_log_base_of_one_falls_back_to_ten():
    """A log base of exactly 1.0 is invalid for matplotlib's LogScale;
    _resolve_log_base (invoked via the custom spin box's valueChanged ->
    _on_field_changed -> _write_axis_config path) must fall back to 10.0."""
    chart = Chart(name="Test Chart")
    chart.update_config({"y_scale": "log"})

    tab = AxesTab(_make_app_context())
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    custom_index = y_form["log_base_combo"].findData("custom")
    y_form["log_base_combo"].setCurrentIndex(custom_index)
    y_form["log_base_custom_spin"].setValue(1.0)

    assert chart.config["y_log_base"] == 10.0


def test_copy_axis_settings_copies_log_base_from_source_y_to_target_y2():
    """_on_copy_axis_settings("y") must copy Y's log-base combo selection
    into Y2, and the copy must be observable in chart.config (not just the
    widget state), since _on_field_changed writes all three axes' config
    at the end of the copy."""
    chart = Chart(name="Test Chart")
    chart.update_config({"y_scale": "log", "y_log_base": 2.0})
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y", y_axis="secondary")

    tab = AxesTab(_make_app_context())
    tab.load(chart)

    y2_form = tab.axes_forms["y2"]
    # Sanity check: Y2 starts out at the default base (10.0), distinct from Y's 2.0.
    assert y2_form["log_base_combo"].currentData() == 10.0

    tab._on_copy_axis_settings("y")

    assert y2_form["log_base_combo"].currentData() == 2.0
    assert chart.config["y2_log_base"] == 2.0


def test_load_selects_custom_for_non_preset_log_base_and_populates_spin():
    """Loading a chart whose config has a non-preset log base (3.5) must
    select "Custom..." in the combo and populate the custom spin box with
    3.5 -- the round-trip of _read_axis_config for a saved custom base."""
    chart = Chart(name="Test Chart")
    chart.update_config({"y_scale": "log", "y_log_base": 3.5})

    tab = AxesTab(_make_app_context())
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    assert y_form["log_base_combo"].currentData() == "custom"
    assert y_form["log_base_custom_spin"].value() == 3.5
    assert y_form["log_base_custom_spin"].isHidden() is False
    assert y_form["log_base_row"].isHidden() is False


def test_load_manual_axis_shows_saved_range_not_recomputed_data_range():
    """A Manual-mode axis's displayed min/max on load must be exactly what
    was saved in chart.config, even when the chart's series data would
    compute to a completely different range. Loading/reopening a chart is
    NOT an Auto->Manual toggle, so it must never recompute-and-overwrite a
    Manual axis's value (the bug this test guards against: `load()` used to
    call `_refresh_range_display` unconditionally for every axis, silently
    clobbering the saved manual range with the live data range)."""
    ds = _make_dataset("ds1", x=[1, 2, 3], y=[100, 200, 300])
    project = _FakeProject([ds])
    chart = Chart(name="Test Chart")
    chart.update_config({
        "y_auto_limits": False,
        "y_min": 5.0,
        "y_max": 50.0,
    })
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y")

    tab = AxesTab(_make_app_context(project))
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    assert y_form["auto_toggle"].isChecked() is False
    assert y_form["min_spin"].value() == 5.0
    assert y_form["max_spin"].value() == 50.0
    assert y_form["min_spin"].isEnabled() is True
    assert y_form["max_spin"].isEnabled() is True


def test_load_auto_axis_shows_recomputed_data_range_disabled():
    """Regression check: an Auto-mode axis must still show the freshly
    recomputed data range on load, disabled -- the Auto path is unaffected
    by the Manual-mode fix above."""
    ds = _make_dataset("ds1", x=[1, 2, 3], y=[100, 200, 300])
    project = _FakeProject([ds])
    chart = Chart(name="Test Chart")
    chart.update_config({"y_auto_limits": True})
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y")

    tab = AxesTab(_make_app_context(project))
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    assert y_form["auto_toggle"].isChecked() is True
    assert y_form["min_spin"].value() == 100.0
    assert y_form["max_spin"].value() == 300.0
    assert y_form["min_spin"].isEnabled() is False
    assert y_form["max_spin"].isEnabled() is False


def test_log_scale_axis_range_display_excludes_non_positive_values():
    """A Log-scaled axis must show Min/Max computed from only the positive
    subset of the data -- matplotlib's log-scale autoscale ignores
    non-positive points entirely, and a raw min <= 0 would later be
    silently rejected by set_ylim() on a log axis."""
    ds = _make_dataset("ds1", x=[1, 2, 3], y=[-5, 10, 20])
    project = _FakeProject([ds])
    chart = Chart(name="Test Chart")
    chart.update_config({"y_auto_limits": True, "y_scale": "log"})
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y")

    tab = AxesTab(_make_app_context(project))
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    assert y_form["min_spin"].value() == 10.0
    assert y_form["max_spin"].value() == 20.0


def test_toggling_auto_to_manual_recomputes_fresh_from_data():
    """Regression check: an explicit Auto->Manual toggle is the one case
    that SHOULD still recompute-and-overwrite -- it must ignore whatever
    stale value happened to be sitting in the spin boxes and show the
    current data range instead."""
    ds = _make_dataset("ds1", x=[1, 2, 3], y=[100, 200, 300])
    project = _FakeProject([ds])
    chart = Chart(name="Test Chart")
    chart.update_config({"y_auto_limits": True})
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y")

    tab = AxesTab(_make_app_context(project))
    tab.load(chart)

    y_form = tab.axes_forms["y"]
    assert y_form["min_spin"].value() == 100.0
    assert y_form["max_spin"].value() == 300.0

    y_form["auto_toggle"].setChecked(False)

    assert y_form["min_spin"].value() == 100.0
    assert y_form["max_spin"].value() == 300.0
    assert y_form["min_spin"].isEnabled() is True
    assert y_form["max_spin"].isEnabled() is True
