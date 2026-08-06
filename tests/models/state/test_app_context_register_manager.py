"""Tests for AppContext.register_manager."""
from pandaplot.models.state.app_context import AppContext


def _bare_app_context() -> AppContext:
    app_context = AppContext.__new__(AppContext)
    app_context._managers = {}
    return app_context


class _FakeLateManager:
    pass


def test_register_manager_makes_it_retrievable():
    app_context = _bare_app_context()
    late_manager = _FakeLateManager()

    app_context.register_manager(late_manager)

    assert app_context.get_manager(_FakeLateManager) is late_manager


def test_register_manager_overwrites_existing_entry_of_same_type():
    app_context = _bare_app_context()
    first = _FakeLateManager()
    second = _FakeLateManager()
    app_context.register_manager(first)

    app_context.register_manager(second)

    assert app_context.get_manager(_FakeLateManager) is second
