"""
Unit tests for the cm<->inches conversion helpers used to let the chart
preview's width/height controls work in centimeters, while matplotlib's
Figure stays in inches internally (a hard API constraint).
"""

import pytest

from pandaplot.gui.components.tabs.chart.chart_canvas import cm_to_inches, fit_size_cm, inches_to_cm


def test_cm_to_inches_known_value():
    assert cm_to_inches(2.54) == pytest.approx(1.0)


def test_inches_to_cm_known_value():
    assert inches_to_cm(1.0) == pytest.approx(2.54)


def test_cm_to_inches_round_trips_with_inches_to_cm():
    assert inches_to_cm(cm_to_inches(20.0)) == pytest.approx(20.0)


def test_default_width_cm_converts_to_expected_inches():
    assert cm_to_inches(20.0) == pytest.approx(7.874, abs=1e-3)


def test_default_height_cm_converts_to_expected_inches():
    assert cm_to_inches(15.0) == pytest.approx(5.906, abs=1e-3)


def test_fit_size_cm_converts_pixels_to_cm_via_dpi():
    # 100 dpi, 393.7 px wide/tall ~= 3.937 in ~= 10.0 cm
    width_cm, height_cm = fit_size_cm(394, 394, dpi=100)
    assert width_cm == pytest.approx(10, abs=1)
    assert height_cm == pytest.approx(10, abs=1)


def test_fit_size_cm_clamps_to_minimums():
    width_cm, height_cm = fit_size_cm(10, 10, dpi=100)
    assert width_cm == 2
    assert height_cm == 2


def test_fit_size_cm_clamps_to_maximums():
    width_cm, height_cm = fit_size_cm(100000, 100000, dpi=100)
    assert width_cm == 50
    assert height_cm == 40


def test_fit_size_cm_returns_floats_rounded_to_one_decimal():
    width_cm, height_cm = fit_size_cm(500, 400, dpi=100)
    assert isinstance(width_cm, float)
    assert isinstance(height_cm, float)
    assert width_cm == round(width_cm, 1)
    assert height_cm == round(height_cm, 1)


def test_fit_size_cm_respects_custom_bounds():
    width_cm, height_cm = fit_size_cm(10, 10, dpi=100, min_width_cm=5, min_height_cm=6)
    assert width_cm == 5
    assert height_cm == 6
