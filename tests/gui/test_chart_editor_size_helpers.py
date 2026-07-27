from pandaplot.gui.components.tabs.chart.chart_editor import resolve_chart_size


def test_uses_per_chart_values_when_set():
    width, height, dpi = resolve_chart_size(
        chart_width_cm=12.0, chart_height_cm=8.0, chart_dpi=300,
        default_width_cm=20.0, default_height_cm=15.0, default_dpi=100,
    )
    assert (width, height, dpi) == (12.0, 8.0, 300)


def test_falls_back_to_defaults_when_chart_values_are_none():
    width, height, dpi = resolve_chart_size(
        chart_width_cm=None, chart_height_cm=None, chart_dpi=None,
        default_width_cm=20.0, default_height_cm=15.0, default_dpi=100,
    )
    assert (width, height, dpi) == (20.0, 15.0, 100)


def test_mixes_per_chart_and_default_values_independently():
    width, height, dpi = resolve_chart_size(
        chart_width_cm=12.0, chart_height_cm=None, chart_dpi=None,
        default_width_cm=20.0, default_height_cm=15.0, default_dpi=100,
    )
    assert (width, height, dpi) == (12.0, 15.0, 100)
