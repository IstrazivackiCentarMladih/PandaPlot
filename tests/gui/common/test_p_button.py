import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.p_button import PButton


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_default_role_is_secondary():
    button = PButton("Cancel")
    assert button.property("secondary") is True
    assert button.property("primary") is False
    assert button.property("destructive") is False


def test_primary_role_sets_primary_property_only():
    button = PButton("Apply", role="primary")
    assert button.property("primary") is True
    assert button.property("secondary") is False
    assert button.property("destructive") is False


def test_destructive_role_sets_destructive_property_only():
    button = PButton("Remove", role="destructive")
    assert button.property("destructive") is True
    assert button.property("primary") is False
    assert button.property("secondary") is False


def test_icon_flag_sets_icon_property_and_defaults_role_to_secondary():
    button = PButton("\U0001f5d1", icon=True)
    assert button.property("iconButton") is True
    assert button.property("secondary") is True


def test_icon_flag_combines_with_destructive_role():
    button = PButton("\U0001f5d1", role="destructive", icon=True)
    assert button.property("iconButton") is True
    assert button.property("destructive") is True


def test_set_role_changes_role_at_runtime():
    button = PButton("Apply", role="primary")
    button.set_role("secondary")
    assert button.property("primary") is False
    assert button.property("secondary") is True


def test_button_text_is_preserved():
    button = PButton("Apply", role="primary")
    assert button.text() == "Apply"
