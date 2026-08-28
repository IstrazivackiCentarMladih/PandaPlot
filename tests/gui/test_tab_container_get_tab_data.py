from unittest.mock import Mock

from pandaplot.gui.components.tabs.tab_container import TabContainer


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
