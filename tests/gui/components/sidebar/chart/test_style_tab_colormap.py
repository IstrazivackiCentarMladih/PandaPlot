"""Tests for StyleTab's Color Map card (Colormap/Heatmap chart types).

This is the fix for PR #156's review comments: changing to a Colormap/
Heatmap series must correctly hide the Line/Marker cards (previously
broken) via the same spec-driven mechanism _update_target_cards_visibility
already uses for Vector -- not a new hardcoded chart-type check.
"""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_style import ColormapSeriesStyle, HeatmapSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import DataSeries


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def _tab():
    # Qt only reports isVisible() truthfully for a widget whose top-level
    # ancestor has actually been shown (see test_style_tab_vector.py's same
    # pattern) -- without this, isVisible() is always False regardless of
    # setVisible() calls.
    tab = StyleTab(app_context=None)
    tab.show()
    return tab


def test_colormap_card_shown_for_heatmap_series_with_gridding_visible():
    tab = _tab()
    series = DataSeries(
        dataset_id="ds1", series_type=SeriesType.HEATMAP, style=HeatmapSeriesStyle(),
    )
    tab.set_chart_type(ChartType.HEATMAP)
    tab.set_selected("series", series)

    assert tab.colormap_card.isVisible() is True
    assert tab.heatmap_gridding_control.isVisible() is True
    # Heatmap's marker_mode is "unsupported" -- Marker/Line/Fill all hidden.
    assert tab.marker_card.isVisible() is False
    assert tab.line_card.isVisible() is False
    assert tab.fill_card.isVisible() is False


def test_gridding_controls_hidden_for_colormap_scatter_series():
    tab = _tab()
    series = DataSeries(
        dataset_id="ds1", series_type=SeriesType.COLORMAP, style=ColormapSeriesStyle(),
    )
    tab.set_chart_type(ChartType.COLORMAP)
    tab.set_selected("series", series)

    assert tab.colormap_card.isVisible() is True
    assert tab.heatmap_gridding_control.isVisible() is False
    assert tab.heatmap_resolution_spin.isVisible() is False
    # Marker card stays visible (marker_mode == "required" for Colormap);
    # line/fill cards stay hidden -- this is the fix for PR #156's review
    # comments about broken line/marker controls on these series types.
    assert tab.marker_card.isVisible() is True
    assert tab.line_card.isVisible() is False
    assert tab.fill_card.isVisible() is False
    # Colormap has supports_color=False (same as Scatter) -- there is no
    # drawn line to match, so the "Match line" toggle must be hidden too.
    # Regression check for _is_scatter_series_target previously hardcoding
    # SeriesType.SCATTER and missing Colormap: leaving this toggle visible
    # let it silently blank marker_edge_color/swatch_color when checked.
    assert tab.marker_match_line_toggle.isVisible() is False


def test_marker_fill_color_hidden_for_colormap_series_edge_color_stays_visible():
    """render_colormap_series always drives fill color from z_data through
    the colormap (c=series_data.z_data) -- style.marker.marker_color is
    never read, so the "Color:" row must be hidden outright rather than
    shown as a control that silently does nothing. Edge color/width and
    shape/size DO apply (read by the renderer) and must stay visible."""
    tab = _tab()
    series = DataSeries(
        dataset_id="ds1", series_type=SeriesType.COLORMAP, style=ColormapSeriesStyle(),
    )
    tab.set_chart_type(ChartType.COLORMAP)
    tab.set_selected("series", series)

    assert tab.marker_card.isVisible() is True
    assert tab.marker_color_row.isVisible() is False
    assert tab.marker_color_label.isVisible() is False
    assert tab.marker_edge_color_row.isVisible() is True
    assert tab.marker_edge_color_label.isVisible() is True
    assert tab.marker_shape_control.isVisible() is True
    assert tab.marker_size_slider.isVisible() is True


def test_marker_fill_color_visible_for_a_plain_line_series_target():
    """Sanity check that the new hide-for-z-driven-series behavior doesn't
    regress the ordinary case: a Line series' marker fill color must still
    be shown once markers are enabled."""
    tab = _tab()
    series = DataSeries(dataset_id="ds1", series_type=SeriesType.LINE)
    tab.set_chart_type(ChartType.LINE)
    tab.set_selected("series", series)
    tab.markers_enabled_toggle.setChecked(True)
    tab.marker_match_line_toggle.setChecked(False)
    tab._update_marker_controls_enabled()

    assert tab.marker_color_row.isVisible() is True
    assert tab.marker_color_label.isVisible() is True


def test_colormap_card_hidden_for_a_line_series_target():
    tab = _tab()
    series = DataSeries(dataset_id="ds1")
    tab.set_chart_type(ChartType.LINE)
    tab.set_selected("series", series)

    assert tab.colormap_card.isVisible() is False


def test_resolution_hidden_for_exact_grid_mode_shown_for_binned():
    tab = _tab()
    series = DataSeries(
        dataset_id="ds1", series_type=SeriesType.HEATMAP,
        style=HeatmapSeriesStyle(heatmap_gridding="grid"),
    )
    tab.set_chart_type(ChartType.HEATMAP)
    tab.set_selected("series", series)

    assert tab.heatmap_resolution_spin.isVisible() is False

    # setCurrentValue() blocks signals (see ValueComboBox), so use
    # setCurrentIndex() directly to exercise the real
    # currentValueChanged -> _on_heatmap_gridding_changed wiring.
    tab.heatmap_gridding_control.setCurrentIndex(tab.heatmap_gridding_control.findData("binned"))

    assert tab.heatmap_resolution_spin.isVisible() is True


def test_apply_and_load_series_style_round_trip_heatmap():
    tab = _tab()
    series = DataSeries(
        dataset_id="ds1", series_type=SeriesType.HEATMAP, style=HeatmapSeriesStyle(),
    )
    tab.set_chart_type(ChartType.HEATMAP)
    tab.set_selected("series", series)

    tab.colormap_control.setCurrentValue("plasma")
    tab.colorbar_show_toggle.setChecked(False)
    tab.colorbar_label_edit.setText("Temp (C)")
    tab.color_scale_auto_toggle.setChecked(False)
    tab.color_vmin_spin.setValue(-5.0)
    tab.color_vmax_spin.setValue(42.0)
    tab.heatmap_gridding_control.setCurrentValue("binned")
    tab.heatmap_resolution_spin.setValue(80)

    tab.apply_series_style_to(series)

    assert series.style.colormap == "plasma"
    assert series.style.colorbar_show is False
    assert series.style.colorbar_label == "Temp (C)"
    assert series.style.color_scale_auto is False
    assert series.style.color_vmin == -5.0
    assert series.style.color_vmax == 42.0
    assert series.style.heatmap_gridding == "binned"
    assert series.style.heatmap_resolution == 80

    # Round trip through a fresh tab: load must reproduce all of the above.
    tab2 = _tab()
    tab2.set_chart_type(ChartType.HEATMAP)
    tab2.load_series_style(series)

    assert tab2.colormap_control.currentValue() == "plasma"
    assert tab2.colorbar_show_toggle.isChecked() is False
    assert tab2.colorbar_label_edit.text() == "Temp (C)"
    assert tab2.color_scale_auto_toggle.isChecked() is False
    assert tab2.color_vmin_spin.value() == -5.0
    assert tab2.color_vmax_spin.value() == 42.0
    assert tab2.heatmap_gridding_control.currentValue() == "binned"
    assert tab2.heatmap_resolution_spin.value() == 80


def test_apply_and_load_series_style_round_trip_colormap_marker_fields():
    """Colormap keeps its Marker card populated/applied (marker_mode ==
    "required") in addition to the Color Map fields."""
    tab = _tab()
    series = DataSeries(
        dataset_id="ds1", series_type=SeriesType.COLORMAP, style=ColormapSeriesStyle(),
    )
    tab.set_chart_type(ChartType.COLORMAP)
    tab.set_selected("series", series)

    tab.colormap_control.setCurrentValue("cool")
    tab.color_scale_auto_toggle.setChecked(False)
    tab.color_vmin_spin.setValue(0.5)
    tab.color_vmax_spin.setValue(9.5)
    tab.marker_size_slider.setValue(12.0)

    tab.apply_series_style_to(series)

    assert series.style.colormap == "cool"
    assert series.style.color_scale_auto is False
    assert series.style.color_vmin == 0.5
    assert series.style.color_vmax == 9.5
    assert series.style.marker.marker_size == 12.0
    # ColormapSeriesStyle has no color/line-style fields -- must not be
    # spuriously created as a dynamic attribute by the fallthrough.
    assert not hasattr(series.style, "line_style")
