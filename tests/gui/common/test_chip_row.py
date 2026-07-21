import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.chip_row import ChipRow


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_empty_row_has_no_current_value():
    row = ChipRow()
    assert row.currentValue() is None


def test_set_items_selects_first_item_by_default():
    row = ChipRow()
    row.setItems([("Series 1", "s1"), ("Series 2", "s2")])
    assert row.currentValue() == "s1"


def test_set_current_value_selects_matching_chip():
    row = ChipRow()
    row.setItems([("Series 1", "s1"), ("Series 2", "s2")])
    row.setCurrentValue("s2")
    assert row.currentValue() == "s2"


def test_set_items_preserves_current_value_if_still_present():
    row = ChipRow()
    row.setItems([("Series 1", "s1"), ("Series 2", "s2")])
    row.setCurrentValue("s2")
    row.setItems([("Series 1", "s1"), ("Series 2", "s2"), ("Series 3", "s3")])
    assert row.currentValue() == "s2"


def test_set_items_resets_to_first_if_current_value_removed():
    row = ChipRow()
    row.setItems([("Series 1", "s1"), ("Series 2", "s2")])
    row.setCurrentValue("s2")
    row.setItems([("Series 1", "s1"), ("Series 3", "s3")])
    assert row.currentValue() == "s1"


def test_clicking_a_chip_emits_current_value_changed():
    row = ChipRow()
    row.setItems([("Series 1", "s1"), ("Series 2", "s2")])
    seen = []
    row.currentValueChanged.connect(seen.append)
    row._buttons[1].click()
    assert seen == ["s2"]
