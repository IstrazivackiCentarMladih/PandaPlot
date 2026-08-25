"""Tests for the Style tab Size card honoring the app's configured
measurement unit (cm default; mm/in also supported)."""
import sys

from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.state.config import LengthUnit
from pandaplot.services.config.config_manager import ConfigManager


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _style_tab_with_unit(unit: LengthUnit) -> StyleTab:
    _qapp()
    app_context = build_app_context()
    app_context.get_manager(ConfigManager).config.chart_display.measurement_unit = unit
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    return style_tab


def test_default_unit_is_cm():
    style_tab = _style_tab_with_unit(LengthUnit.CM)
    assert style_tab._chart_size_unit == LengthUnit.CM
    assert style_tab.chart_width_spin.suffix() == " cm"
    assert style_tab.chart_size_combo.itemText(0) == "15.0 × 8.0 cm"


def test_mm_unit_converts_preset_labels_and_custom_spin_suffix():
    style_tab = _style_tab_with_unit(LengthUnit.MM)
    assert style_tab.chart_size_combo.itemText(0) == "150 × 80 mm"
    assert style_tab.chart_size_combo.itemText(1) == "200 × 150 mm"
    assert style_tab.chart_width_spin.suffix() == " mm"
    assert style_tab.chart_width_spin.decimals() == 0
    # Preset itemData stays canonical centimeters regardless of display unit.
    assert style_tab.chart_size_combo.itemData(0) == (15.0, 8.0)


def test_loading_custom_chart_size_displays_in_configured_unit():
    style_tab = _style_tab_with_unit(LengthUnit.MM)
    chart = Chart(name="c")
    chart.config["width_cm"] = 12.0
    chart.config["height_cm"] = 9.0

    style_tab.load_chart_style(chart)

    assert style_tab.chart_size_combo.currentData() == "custom"
    assert style_tab.chart_width_spin.value() == 120
    assert style_tab.chart_height_spin.value() == 90


def test_applying_custom_chart_size_converts_back_to_centimeters():
    style_tab = _style_tab_with_unit(LengthUnit.MM)
    chart = Chart(name="c")
    chart.config["width_cm"] = 12.0
    chart.config["height_cm"] = 9.0
    style_tab.load_chart_style(chart)

    style_tab.chart_width_spin.setValue(150)
    style_tab.chart_height_spin.setValue(100)
    style_tab.apply_chart_style_to(chart)

    assert chart.config["width_cm"] == 15.0
    assert chart.config["height_cm"] == 10.0


def test_clear_chart_style_default_fallback_shown_in_configured_unit():
    style_tab = _style_tab_with_unit(LengthUnit.MM)
    style_tab.clear_chart_style()
    assert style_tab.chart_width_spin.value() == 200
    assert style_tab.chart_height_spin.value() == 150
