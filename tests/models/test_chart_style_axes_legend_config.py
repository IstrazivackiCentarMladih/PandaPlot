"""
Unit tests for the Chart/DataSeries model extensions backing the
Style/Axes/Legend sidebar tabs (per-axis grid, scale, font size,
axis limits, tick configuration, legend styling, series alpha).
"""

import pytest
from matplotlib.figure import Figure
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.color_swatch_row import ColorSwatchRow
from pandaplot.gui.components.sidebar.chart.tabs.axes_tab import AXES_SWATCH_PALETTE
from pandaplot.gui.components.tabs.chart.chart_editor import apply_axis_ticks, apply_spine_colors
from pandaplot.models.project.items.chart import Chart, DataSeries


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_data_series_alpha_defaults_to_fully_opaque():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y")
    assert series.alpha == 1.0


def test_data_series_alpha_round_trips_through_serialization():
    chart = Chart(name="Test Chart", chart_type="line")
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y", alpha=0.4)

    data = chart.to_dict()
    assert data["data_series"][0]["alpha"] == 0.4

    restored = Chart.from_dict(data)
    assert restored.data_series[0].alpha == 0.4


def test_data_series_alpha_defaults_when_missing_from_saved_data():
    # Simulates loading a project saved before the alpha field existed.
    data = {
        "id": "chart1",
        "name": "Test Chart",
        "chart_type": "line",
        "data_series": [{
            "dataset_id": "ds1", "x_column": "x", "y_column": "y", "label": "",
            "color": "#1f77b4", "marker_color": "", "marker_edge_color": "#000000",
            "line_style": "solid", "marker_style": "circle", "line_width": 2.0,
            "marker_size": 6.0, "visible": True,
        }],
        "fit_data": [],
        "config": {},
        "style": {},
    }

    restored = Chart.from_dict(data)
    assert restored.data_series[0].alpha == 1.0


def test_default_config_has_independent_per_axis_grid_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["show_grid_x"] is True
    assert chart.config["show_grid_y"] is True
    assert "show_grid" not in chart.config


def test_default_config_has_scale_font_and_limit_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["x_scale"] == "linear"
    assert chart.config["y_scale"] == "linear"
    assert chart.config["x_font_size"] == 12
    assert chart.config["y_font_size"] == 12
    assert chart.config["x_auto_limits"] is True
    assert chart.config["y_auto_limits"] is True
    assert chart.config["x_min"] == 0.0
    assert chart.config["x_max"] == 1.0


def test_default_config_has_tick_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["x_tick_mode"] == "auto"
    assert chart.config["x_tick_count"] == 5
    assert chart.config["x_tick_step"] == 1.0
    assert chart.config["x_tick_format"] == "auto"
    assert chart.config["x_tick_format_custom"] == ""
    assert chart.config["y_tick_mode"] == "auto"


def test_default_config_has_legend_style_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["legend_show_frame"] is True
    assert chart.config["legend_font_size"] == 10
    assert chart.config["legend_bg_color"] == "#ffffff"


def test_get_config_summary_has_grid_true_when_either_axis_enabled():
    chart = Chart(name="Test Chart")
    chart.config["show_grid_x"] = False
    chart.config["show_grid_y"] = True
    assert chart.get_config_summary()["has_grid"] is True


def test_get_config_summary_has_grid_false_when_both_axes_disabled():
    chart = Chart(name="Test Chart")
    chart.config["show_grid_x"] = False
    chart.config["show_grid_y"] = False
    assert chart.get_config_summary()["has_grid"] is False


def test_chart_config_has_hist_bins_default():
    chart = Chart(name="c")
    assert chart.config["hist_bins"] == 20


def test_hist_bins_round_trips_through_serialization():
    chart = Chart(name="c")
    chart.config["hist_bins"] = 42
    restored = Chart.from_dict(chart.to_dict())
    assert restored.config["hist_bins"] == 42


def test_default_config_has_chart_tab_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["subtitle"] == ""
    assert chart.config["title_font_size"] == 14
    assert chart.config["width_cm"] is None
    assert chart.config["height_cm"] is None
    assert chart.config["dpi"] is None


def test_default_config_has_legend_columns_and_opacity_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["legend_columns"] == 1
    assert chart.config["legend_bg_alpha"] == 1.0


def test_new_chart_tab_and_legend_keys_round_trip_through_serialization():
    chart = Chart(name="Test Chart")
    chart.config["subtitle"] = "n = 42"
    chart.config["title_font_size"] = 18
    chart.config["width_cm"] = 12.5
    chart.config["height_cm"] = 9.0
    chart.config["dpi"] = 300
    chart.config["legend_columns"] = 2
    chart.config["legend_bg_alpha"] = 0.8

    restored = Chart.from_dict(chart.to_dict())
    assert restored.config["subtitle"] == "n = 42"
    assert restored.config["title_font_size"] == 18
    assert restored.config["width_cm"] == 12.5
    assert restored.config["height_cm"] == 9.0
    assert restored.config["dpi"] == 300
    assert restored.config["legend_columns"] == 2
    assert restored.config["legend_bg_alpha"] == 0.8


def test_new_keys_default_when_missing_from_saved_data():
    # Simulates loading a project saved before these keys existed.
    data = {
        "id": "chart1", "name": "Test Chart", "chart_type": "line",
        "data_series": [], "fit_data": [],
        "config": {"title": "Test Chart"},  # non-empty, so _init_default_config is NOT re-run
        "style": {},
    }
    restored = Chart.from_dict(data)
    assert restored.config.get("subtitle", "") == ""
    assert restored.config.get("title_font_size", 14) == 14
    assert restored.config.get("width_cm") is None
    assert restored.config.get("legend_columns", 1) == 1
    assert restored.config.get("legend_bg_alpha", 1.0) == 1.0


def test_default_config_has_y_and_y2_side_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["y_side"] == "left"
    assert chart.config["y2_side"] == "right"


def test_default_config_has_y2_scale_font_and_limit_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["y2_scale"] == "linear"
    assert chart.config["y2_font_size"] == 12
    assert chart.config["y2_auto_limits"] is True
    assert chart.config["y2_min"] == 0.0
    assert chart.config["y2_max"] == 1.0


def test_default_config_has_y2_tick_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["y2_tick_mode"] == "auto"
    assert chart.config["y2_tick_count"] == 5
    assert chart.config["y2_tick_step"] == 1.0
    assert chart.config["y2_tick_format"] == "auto"
    assert chart.config["y2_tick_format_custom"] == ""


def test_default_config_has_y2_grid_key():
    chart = Chart(name="Test Chart")
    assert chart.config["show_grid_y2"] is True
    assert "y2_show_grid" not in chart.config


def test_y2_and_side_keys_round_trip_through_serialization():
    chart = Chart(name="Test Chart")
    chart.config["y_side"] = "right"
    chart.config["y2_side"] = "left"
    chart.config["y2_scale"] = "log"
    chart.config["y2_font_size"] = 16
    chart.config["y2_auto_limits"] = False
    chart.config["y2_min"] = -5.0
    chart.config["y2_max"] = 5.0
    chart.config["y2_tick_mode"] = "count"
    chart.config["y2_tick_count"] = 8
    chart.config["y2_tick_step"] = 0.5
    chart.config["y2_tick_format"] = "2decimal"
    chart.config["y2_tick_format_custom"] = "{:.3f}"
    chart.config["show_grid_y2"] = False

    restored = Chart.from_dict(chart.to_dict())
    assert restored.config["y_side"] == "right"
    assert restored.config["y2_side"] == "left"
    assert restored.config["y2_scale"] == "log"
    assert restored.config["y2_font_size"] == 16
    assert restored.config["y2_auto_limits"] is False
    assert restored.config["y2_min"] == -5.0
    assert restored.config["y2_max"] == 5.0
    assert restored.config["y2_tick_mode"] == "count"
    assert restored.config["y2_tick_count"] == 8
    assert restored.config["y2_tick_step"] == 0.5
    assert restored.config["y2_tick_format"] == "2decimal"
    assert restored.config["y2_tick_format_custom"] == "{:.3f}"
    assert restored.config["show_grid_y2"] is False


def test_y2_and_side_keys_default_when_missing_from_saved_data():
    # Simulates loading a project saved before Y2 scale/limits/ticks/grid existed.
    data = {
        "id": "chart1", "name": "Test Chart", "chart_type": "line",
        "data_series": [], "fit_data": [],
        "config": {"title": "Test Chart"},  # non-empty, so _init_default_config is NOT re-run
        "style": {},
    }
    restored = Chart.from_dict(data)
    assert restored.config.get("y_side", "left") == "left"
    assert restored.config.get("y2_side", "right") == "right"
    assert restored.config.get("y2_scale", "linear") == "linear"
    assert restored.config.get("y2_font_size", 12) == 12
    assert restored.config.get("y2_auto_limits", True) is True
    assert restored.config.get("y2_min", 0.0) == 0.0
    assert restored.config.get("y2_max", 1.0) == 1.0
    assert restored.config.get("y2_tick_mode", "auto") == "auto"
    assert restored.config.get("y2_tick_count", 5) == 5
    assert restored.config.get("y2_tick_step", 1.0) == 1.0
    assert restored.config.get("y2_tick_format", "auto") == "auto"
    assert restored.config.get("y2_tick_format_custom", "") == ""
    assert restored.config.get("show_grid_y2", True) is True


def test_default_config_has_subtitle_font_size_key():
    chart = Chart(name="Test Chart")
    assert chart.config["subtitle_font_size"] == 12


def test_subtitle_font_size_round_trips_through_serialization():
    chart = Chart(name="Test Chart")
    chart.config["subtitle_font_size"] = 16
    restored = Chart.from_dict(chart.to_dict())
    assert restored.config["subtitle_font_size"] == 16


def test_subtitle_font_size_defaults_when_missing_from_saved_data():
    # Simulates loading a project saved before this key existed.
    data = {
        "id": "chart1", "name": "Test Chart", "chart_type": "line",
        "data_series": [], "fit_data": [],
        "config": {"title": "Test Chart"},  # non-empty, so _init_default_config is NOT re-run
        "style": {},
    }
    restored = Chart.from_dict(data)
    assert restored.config.get("subtitle_font_size", 12) == 12


def test_chart_style_background_colors_default_to_opaque_white():
    chart = Chart(name="Test Chart", chart_type="line")
    assert chart.style["figure_background_color"] == "#ffffff"
    assert chart.style["axes_background_color"] == "#ffffff"


def test_chart_style_background_colors_round_trip_through_serialization():
    chart = Chart(name="Test Chart", chart_type="line")
    chart.update_style({
        "figure_background_color": None,
        "axes_background_color": "#123456",
    })

    data = chart.to_dict()
    assert data["style"]["figure_background_color"] is None
    assert data["style"]["axes_background_color"] == "#123456"

    restored = Chart.from_dict(data)
    assert restored.style["figure_background_color"] is None
    assert restored.style["axes_background_color"] == "#123456"


def test_axis_spine_and_tick_colors_default_to_black():
    # The sidebar's color swatch widget for spine/tick colors must itself
    # default to black, since that's what a fresh chart (with no
    # x/y/y2_*_color keys in its config) will render with.
    assert ColorSwatchRow(AXES_SWATCH_PALETTE).currentColor() == "#000000"

    chart = Chart(name="Test Chart")
    for p in ("x", "y", "y2"):
        assert f"{p}_spine_color" not in chart.config
        assert f"{p}_major_tick_color" not in chart.config
        assert f"{p}_minor_tick_color" not in chart.config

    # And the rendering code must actually apply black when these keys are
    # absent from a chart's config, mirroring how chart_editor.py calls
    # apply_spine_colors/apply_axis_ticks with a "#000000" fallback.
    fig = Figure()
    axes = fig.add_subplot(111)
    axes2 = axes.twinx()
    apply_spine_colors(
        axes, axes2,
        chart.config.get("x_spine_color", "#000000"),
        chart.config.get("y_spine_color", "#000000"),
        chart.config.get("y2_spine_color", "#000000"))
    assert axes.spines["bottom"].get_edgecolor() == (0.0, 0.0, 0.0, 1.0)
    assert axes.spines["left"].get_edgecolor() == (0.0, 0.0, 0.0, 1.0)
    assert axes2.spines["right"].get_edgecolor() == (0.0, 0.0, 0.0, 1.0)

    apply_axis_ticks(
        axes.xaxis, "auto", 5, 1.0, "auto", "",
        minor_enabled=True,
        major_color=chart.config.get("x_major_tick_color", "#000000"),
        minor_color=chart.config.get("x_minor_tick_color", "#000000"))
    major_params = axes.xaxis.get_tick_params(which="major")
    minor_params = axes.xaxis.get_tick_params(which="minor")
    assert major_params["color"] == "#000000"
    assert minor_params["color"] == "#000000"


def test_axis_spine_and_tick_colors_round_trip_through_serialization():
    chart = Chart(name="Test Chart")
    chart.update_config({"x_spine_color": "#123456", "y_major_tick_color": "#654321"})
    data = chart.to_dict()
    restored = Chart.from_dict(data)
    assert restored.config["x_spine_color"] == "#123456"
    assert restored.config["y_major_tick_color"] == "#654321"


def test_chart_style_background_colors_default_when_missing_from_saved_data():
    # Simulates loading a project saved before these fields existed.
    data = {
        "id": "chart1",
        "name": "Test Chart",
        "chart_type": "line",
        "data_series": [],
        "fit_data": [],
        "config": {},
        "style": {},
    }

    restored = Chart.from_dict(data)
    assert restored.style["figure_background_color"] == "#ffffff"


def test_default_config_has_title_and_subtitle_color_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["title_color"] == "#000000"
    assert chart.config["subtitle_color"] == "#000000"
    assert chart.config["subtitle_match_title_color"] is True


def test_title_and_subtitle_color_round_trip_through_serialization():
    chart = Chart(name="Test Chart")
    chart.config["title_color"] = "#123456"
    chart.config["subtitle_color"] = "#654321"
    chart.config["subtitle_match_title_color"] = False

    restored = Chart.from_dict(chart.to_dict())
    assert restored.config["title_color"] == "#123456"
    assert restored.config["subtitle_color"] == "#654321"
    assert restored.config["subtitle_match_title_color"] is False


def test_title_and_subtitle_color_default_when_missing_from_saved_data():
    # Simulates loading a project saved before these fields existed.
    data = {
        "id": "chart1",
        "name": "Test Chart",
        "chart_type": "line",
        "data_series": [],
        "fit_data": [],
        "config": {"title": "Test Chart"},  # non-empty, so _init_default_config is NOT re-run
        "style": {},
    }

    restored = Chart.from_dict(data)
    assert restored.config.get("title_color", "#000000") == "#000000"
    assert restored.config.get("subtitle_color", "#000000") == "#000000"
    assert restored.config.get("subtitle_match_title_color", True) is True
    assert restored.style["axes_background_color"] == "#ffffff"
