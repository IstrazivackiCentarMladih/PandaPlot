"""
Unit tests for the Chart/DataSeries model extensions backing the
Style/Axes/Legend sidebar tabs (per-axis grid, scale, font size,
axis limits, tick configuration, legend styling, series alpha).
"""

from pandaplot.models.project.items.chart import Chart, DataSeries


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
