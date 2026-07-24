import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.value_combo_box import ValueComboBox


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_defaults_to_first_item():
    combo = ValueComboBox([("Scatter", "scatter"), ("Line", "line")])
    assert combo.currentValue() == "scatter"


def test_set_current_value_selects_matching_item():
    combo = ValueComboBox([("Scatter", "scatter"), ("Line", "line")])
    combo.setCurrentValue("line")
    assert combo.currentValue() == "line"


def test_set_current_value_ignores_unknown_value():
    combo = ValueComboBox([("Scatter", "scatter"), ("Line", "line")])
    combo.setCurrentValue("line")
    combo.setCurrentValue("does-not-exist")
    assert combo.currentValue() == "line"


def test_set_current_value_does_not_emit_current_value_changed():
    combo = ValueComboBox([("Scatter", "scatter"), ("Line", "line")])
    seen = []
    combo.currentValueChanged.connect(seen.append)
    combo.setCurrentValue("line")
    assert seen == []


def test_user_selecting_a_different_index_emits_current_value_changed():
    combo = ValueComboBox([("Scatter", "scatter"), ("Line", "line")])
    seen = []
    combo.currentValueChanged.connect(seen.append)
    combo.setCurrentIndex(1)
    assert seen == ["line"]


def test_items_constructed_with_matching_icons_do_not_raise():
    from PySide6.QtGui import QIcon

    combo = ValueComboBox(
        [("Solid", "solid"), ("Dashed", "dashed")],
        icons=[QIcon(), QIcon()],
    )
    assert combo.currentValue() == "solid"
