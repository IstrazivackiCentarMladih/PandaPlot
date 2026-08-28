from unittest.mock import Mock

from pandaplot.gui.components.tabs.dataset.dataset_tab import DatasetTab


def test_get_tab_data_returns_dataset_type_and_id():
    tab = DatasetTab.__new__(DatasetTab)
    tab.dataset = Mock(id="ds-1")

    assert tab.get_tab_data() == {"type": "dataset", "id": "ds-1"}
