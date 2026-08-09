import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.models.state.config import Theme
from pandaplot.services.theme.theme_manager import ThemeContext, ThemeManager


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _manager_with_context(theme: Theme) -> ThemeManager:
    manager = ThemeManager.__new__(ThemeManager)
    manager._current = ThemeContext(theme=theme, accent="#4A56C6", interface_font_size=10)
    return manager


def test_get_design_tokens_light_has_status_danger():
    manager = _manager_with_context(Theme.LIGHT)
    tokens = manager.get_design_tokens()
    assert "status_danger" in tokens
    assert tokens["status_danger"] == "#DC3545"


def test_get_design_tokens_dark_has_status_danger():
    manager = _manager_with_context(Theme.DARK)
    tokens = manager.get_design_tokens()
    assert "status_danger" in tokens
    assert tokens["status_danger"] == "#C24141"


def test_build_stylesheet_includes_secondary_destructive_icon_selectors():
    manager = _manager_with_context(Theme.LIGHT)
    ctx = manager._current
    qss = manager.build_stylesheet(ctx)
    assert 'QPushButton[secondary="true"]' in qss
    assert 'QPushButton[destructive="true"]' in qss
    assert 'QPushButton[icon="true"]' in qss
    assert 'QPushButton[icon="true"][destructive="true"]:hover' in qss


def test_build_stylesheet_primary_uses_shared_shape():
    manager = _manager_with_context(Theme.LIGHT)
    ctx = manager._current
    qss = manager.build_stylesheet(ctx)
    primary_rule = qss.split('QPushButton[primary="true"] {')[1].split("}")[0]
    assert "border-radius: 5px" in primary_rule
    assert "padding: 6px 14px" in primary_rule
    assert "font-weight: 600" in primary_rule
