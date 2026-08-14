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


def test_vector_requires_x_y_u_v():
    spec = get_chart_role_spec("vector")
    assert spec.roles == ("x", "y", "u", "v", "magnitude")
    assert spec.required_roles == ("x", "y", "u", "v")
    assert spec.supports_error_bars is False


def test_unknown_chart_type_raises_key_error():
    with pytest.raises(KeyError):
        get_chart_role_spec("violin")


def test_exactly_five_chart_types_are_registered():
    assert set(CHART_ROLE_SPECS.keys()) == {"line", "scatter", "bar", "hist", "vector"}
