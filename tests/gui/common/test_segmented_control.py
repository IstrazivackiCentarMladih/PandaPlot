import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.segmented_control import SegmentedControl


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_defaults_to_first_item():
    control = SegmentedControl([("Linear", "linear"), ("Log", "log")])
    assert control.currentValue() == "linear"


def test_set_current_value_selects_matching_item():
    control = SegmentedControl([("Linear", "linear"), ("Log", "log")])
    control.setCurrentValue("log")
    assert control.currentValue() == "log"


def test_set_current_value_ignores_unknown_value():
    control = SegmentedControl([("Linear", "linear"), ("Log", "log")])
    control.setCurrentValue("log")
    control.setCurrentValue("does-not-exist")
    assert control.currentValue() == "log"


def test_clicking_a_segment_emits_current_value_changed():
    control = SegmentedControl([("Linear", "linear"), ("Log", "log")])
    seen = []
    control.currentValueChanged.connect(seen.append)
    control._buttons[1].click()
    assert seen == ["log"]


def test_clicking_selected_segment_marks_it_selected_property():
    control = SegmentedControl([("Linear", "linear"), ("Log", "log")])
    control.setCurrentValue("log")
    assert control._buttons[1].property("selected") is True
    assert control._buttons[0].property("selected") is False
