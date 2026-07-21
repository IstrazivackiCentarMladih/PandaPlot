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
