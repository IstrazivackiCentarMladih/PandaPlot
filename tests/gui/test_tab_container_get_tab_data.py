from unittest.mock import Mock

from pandaplot.gui.components.tabs.tab_container import TabContainer
from pandaplot.models.events import UIEvents


def _container():
    container = TabContainer.__new__(TabContainer)
    container.logger = Mock()
    return container


def test_dispatches_to_widget_get_tab_data():
    container = _container()
    widget = Mock()
    widget.get_tab_data.return_value = {"type": "dataset", "id": "ds-1"}

    assert container.get_tab_data(widget) == {"type": "dataset", "id": "ds-1"}


def test_falls_back_to_other_for_widgets_without_get_tab_data():
    container = _container()
    widget = object()  # no get_tab_data attribute

    data = container.get_tab_data(widget)

    assert data["type"] == "other"
    assert data["id"] == id(widget)


def test_emit_tab_changed_publishes_tab_id_without_per_type_keys():
    container = _container()
    container.app_context = Mock()
    container._last_emitted_widget = None
    container._persist_tab_session = Mock()

    widget = Mock()
    widget.get_tab_data.return_value = {"type": "chart", "id": "ch-1"}

    pane = Mock()
    pane.currentWidget.return_value = widget
    pane.currentIndex.return_value = 0
    pane.tabText.return_value = "My Chart"
    container._active_pane = pane
    container.active_tab_changed = Mock()

    published = {}

    def _capture(event_type, data):
        published["event_type"] = event_type
        published["data"] = data

    container.publish_event = _capture

    container._emit_tab_changed_for_active_pane()

    assert published["event_type"] == UIEvents.TAB_CHANGED
    assert published["data"] == {
        "tab_index": 0,
        "tab_type": "chart",
        "tab_id": "ch-1",
        "tab_title": "My Chart",
    }
