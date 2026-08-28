"""Regression test for the "closed chart tab still reacts to theme changes"
bug: a tab like ChartTab embeds its own independently-subscribed child
widget (ChartEditorWidget), each a PWidget with its own event-bus
subscriptions. Closing the tab only ever unsubscribed the top-level widget,
leaving the nested child's subscription live until Qt got around to the
deferred deleteLater() destruction -- a window in which a theme change (or
any other event that child listens for) invoked its handler on a widget
whose C++ object could already be partially torn down.
"""
import sys

import pytest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pandaplot.gui.core.widget_extension import PWidget, unsubscribe_widget_tree
from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.events.event_types import ThemeEvents


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


class _FakeAppContext:
    def __init__(self):
        self.event_bus = EventBus()

    def get_app_state(self):
        return None


class _Leaf(PWidget):
    """Stands in for ChartEditorWidget: a nested PWidget with its own
    independent subscription."""

    def _init_ui(self):
        pass

    def _apply_theme(self):
        pass


class _Parent(PWidget):
    """Stands in for ChartTab: a PWidget that embeds a child PWidget."""

    def __init__(self, app_context, parent=None):
        super().__init__(app_context=app_context, parent=parent)
        self._initialize()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.child = _Leaf(app_context=self.app_context, parent=self)
        self.child._initialize()
        layout.addWidget(self.child)

    def _apply_theme(self):
        pass


def test_unsubscribe_widget_tree_covers_nested_pwidget_children():
    app_context = _FakeAppContext()
    parent = _Parent(app_context=app_context)

    theme_subscribers = app_context.event_bus._subscribers[ThemeEvents.THEME_CHANGED]
    assert parent._on_theme_changed in theme_subscribers
    assert parent.child._on_theme_changed in theme_subscribers

    unsubscribe_widget_tree(parent)

    theme_subscribers = app_context.event_bus._subscribers[ThemeEvents.THEME_CHANGED]
    assert parent._on_theme_changed not in theme_subscribers
    assert parent.child._on_theme_changed not in theme_subscribers


def test_unsubscribe_widget_tree_tolerates_plain_qwidget():
    """A widget with no WidgetExtension mixin at all must not raise."""
    widget = QWidget()
    unsubscribe_widget_tree(widget)  # no-op, must not raise
