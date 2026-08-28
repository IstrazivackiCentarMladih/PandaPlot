from unittest.mock import Mock

from pandaplot.gui.components.tabs.chart.chart_tab import ChartTab


def test_get_tab_data_returns_chart_type_and_id():
    tab = ChartTab.__new__(ChartTab)
    tab.chart = Mock(id="ch-1")

    assert tab.get_tab_data() == {"type": "chart", "id": "ch-1"}
