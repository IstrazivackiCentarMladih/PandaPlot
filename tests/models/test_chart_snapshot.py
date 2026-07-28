"""Tests for model-level chart state snapshot/restore helpers."""

import numpy as np

from pandaplot.models.project.items.chart import (
    Chart,
    restore_chart_state,
    snapshot_chart_state,
)


def _make_chart():
    chart = Chart(name="My Chart")
    chart.add_data_series("ds1", "x", "y", label="s1", color="#112233")
    return chart


def test_restore_reverts_config_type_name_and_series():
    chart = _make_chart()
    snap = snapshot_chart_state(chart)

    chart.config["x_label"] = "changed"
    chart.chart_type = "scatter"
    chart.name = "Renamed"
    chart.data_series[0].color = "#ffffff"

    restore_chart_state(chart, snap)

    assert chart.config["x_label"] == ""
    assert chart.chart_type == "line"
    assert chart.name == "My Chart"
    assert chart.data_series[0].color == "#112233"


def test_snapshot_is_a_deep_copy_of_config():
    chart = _make_chart()
    snap = snapshot_chart_state(chart)
    chart.config["title"] = "mutated after snapshot"
    assert snap["config"]["title"] == "My Chart"


def test_restore_recreates_removed_series():
    chart = _make_chart()
    snap = snapshot_chart_state(chart)
    chart.data_series.clear()
    restore_chart_state(chart, snap)
    assert len(chart.data_series) == 1
    assert chart.data_series[0].label == "s1"


def test_restore_reverts_background_style_fields():
    chart = _make_chart()
    snap = snapshot_chart_state(chart)

    chart.style["figure_background_color"] = "#000000"
    chart.style["axes_background_color"] = "#111111"

    restore_chart_state(chart, snap)

    assert chart.style["figure_background_color"] == "#ffffff"
    assert chart.style["axes_background_color"] == "#ffffff"


def test_restore_only_touches_fit_style_fields():
    chart = _make_chart()
    chart.add_fit_data(
        "ds1", "x", "y", "Linear",
        np.array([1.0]), np.array([2.0]),
        color="#ff0000", line_width=2.0,
    )
    snap = snapshot_chart_state(chart)

    chart.fit_data[0].color = "#00ff00"
    chart.fit_data[0].line_width = 5.0

    restore_chart_state(chart, snap)

    assert chart.fit_data[0].color == "#ff0000"
    assert chart.fit_data[0].line_width == 2.0
