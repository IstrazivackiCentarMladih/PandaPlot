"""Unit tests for resolve_scale_kwargs(), the pure helper that decides
whether a log `base` kwarg should be passed to Axes.set_xscale/set_yscale."""
from pandaplot.gui.components.tabs.chart.chart_editor import resolve_scale_kwargs


def test_linear_scale_has_no_base_kwarg():
    assert resolve_scale_kwargs("linear", 10.0) == {}


def test_log_scale_passes_base_kwarg():
    assert resolve_scale_kwargs("log", 2.0) == {"base": 2.0}


def test_log_scale_with_custom_base_between_zero_and_one():
    assert resolve_scale_kwargs("log", 0.5) == {"base": 0.5}
