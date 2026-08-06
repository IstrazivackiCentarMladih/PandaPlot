"""Tests for the wizard's per-chart-type column-role requirements."""
import pytest

from pandaplot.gui.dialogs.chart.chart_role_spec import CHART_ROLE_SPECS, get_chart_role_spec


def test_line_requires_only_y():
    spec = get_chart_role_spec("line")
    assert spec.roles == ("x", "y")
    assert spec.required_roles == ("y",)
    assert spec.supports_error_bars is True


def test_scatter_requires_only_y():
    spec = get_chart_role_spec("scatter")
    assert spec.required_roles == ("y",)
    assert spec.supports_error_bars is True


def test_bar_requires_only_y():
    spec = get_chart_role_spec("bar")
    assert spec.roles == ("x", "y")
    assert spec.required_roles == ("y",)
    assert spec.supports_error_bars is True


def test_histogram_requires_values_and_has_no_error_bars():
    spec = get_chart_role_spec("hist")
    assert spec.roles == ("values",)
    assert spec.required_roles == ("values",)
    assert spec.supports_error_bars is False


def test_unknown_chart_type_raises_key_error():
    with pytest.raises(KeyError):
        get_chart_role_spec("violin")


def test_colormap_and_heatmap_require_x_y_z_and_have_no_error_bars():
    for chart_type in ("colormap", "heatmap"):
        spec = get_chart_role_spec(chart_type)
        assert spec.roles == ("x", "y", "z")
        assert spec.required_roles == ("x", "y", "z")
        assert spec.supports_error_bars is False


def test_registered_chart_types():
    assert set(CHART_ROLE_SPECS.keys()) == {
        "line", "scatter", "bar", "hist", "colormap", "heatmap"
    }
