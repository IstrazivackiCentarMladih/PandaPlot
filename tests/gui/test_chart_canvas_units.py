"""
Unit tests for the cm<->inches conversion helpers used to let the chart
preview's width/height controls work in centimeters, while matplotlib's
Figure stays in inches internally (a hard API constraint).
"""

import pytest

from pandaplot.gui.components.tabs.chart.chart_canvas import cm_to_inches, inches_to_cm


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
