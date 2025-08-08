"""
Tests for ConditionalPanelManager and panel visibility logic.
"""

import pytest
from unittest.mock import Mock
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import QObject

from pandaplot.gui.components.sidebar.conditional_panel_manager import ConditionalPanelManager
from pandaplot.gui.components.sidebar.panel_conditions import (
    is_dataset_tab_active, 
    is_chart_tab_active,
    is_transformable_dataset
)


class MockDatasetTab(QWidget):
    """Mock dataset tab widget for testing."""
    def __init__(self):
        super().__init__()
        self.dataset = Mock()
        # Make it identifiable as a DatasetTab
        self.__class__.__name__ = 'DatasetTab'


class MockChartTab(QWidget):
    """Mock chart tab widget for testing."""
    def __init__(self):
        super().__init__()
        self.chart = Mock()
        # Make it identifiable as a ChartTab
        self.__class__.__name__ = 'ChartTab'


class MockWelcomeTab(QWidget):
    """Mock welcome tab widget for testing."""
    def __init__(self):
        super().__init__()
        self.__class__.__name__ = 'WelcomeTab'


class MockTabContainer(QObject):
    """Mock tab container for testing."""
    def __init__(self):
        super().__init__()
        self.tabs = []
        self.current_index = 0
        # Mock the tab_widget attribute
        self.tab_widget = Mock()
        self.tab_widget.currentChanged = Mock()
    
    def get_current_index(self):
        return self.current_index
    
    def get_tab_widget(self, index):
        if 0 <= index < len(self.tabs):
            return self.tabs[index]
        return None
    
    def set_current_tab(self, index):
        self.current_index = index


class MockSidebar(QObject):
    """Mock sidebar for testing."""
    def __init__(self):
        super().__init__()
        self.panels = {}
        self.visible_panels = set()
    
    def add_panel(self, panel_id, icon, widget):
        self.panels[panel_id] = {'icon': icon, 'widget': widget}
    
    def show_panel(self, panel_id):
        self.visible_panels.add(panel_id)
    
    def hide_panel(self, panel_id):
        self.visible_panels.discard(panel_id)
    
    def is_panel_visible(self, panel_id):
        return panel_id in self.visible_panels


class TestConditionalPanelManager:
    """Test cases for ConditionalPanelManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sidebar = MockSidebar()
        self.tab_container = MockTabContainer()
        # Type ignore for mock objects in tests
        self.manager = ConditionalPanelManager(self.sidebar, self.tab_container)  # type: ignore
    
    def test_register_conditional_panel(self):
        """Test registering a conditional panel."""
        condition_func = Mock(return_value=True)
        
        self.manager.register_conditional_panel(
            "test_panel", condition_func, priority=1
        )
        
        assert "test_panel" in self.manager.registered_panels
        panel_config = self.manager.registered_panels["test_panel"]
        assert panel_config["condition_func"] == condition_func
        assert panel_config["priority"] == 1
    
    def test_panel_visibility_evaluation(self):
        """Test panel visibility evaluation."""
        condition_func = Mock(return_value=True)
        
        # Register panel
        self.manager.register_conditional_panel("test_panel", condition_func)
        
        # Add a dataset tab and set as current
        dataset_tab = MockDatasetTab()
        self.tab_container.tabs.append(dataset_tab)
        self.manager.current_tab_widget = dataset_tab
        
        # Evaluate visibility
        self.manager.evaluate_panel_visibility()
        
        # Condition function should have been called with the tab widget
        condition_func.assert_called_once_with(dataset_tab)
    
    def test_on_tab_changed_updates_current_widget(self):
        """Test that tab change updates current widget."""
        # Add tabs
        dataset_tab = MockDatasetTab()
        welcome_tab = MockWelcomeTab()
        self.tab_container.tabs.append(dataset_tab)
        self.tab_container.tabs.append(welcome_tab)
        
        # Simulate tab change to dataset tab
        self.manager.on_tab_changed(dataset_tab)
        
        # Current widget should be updated
        assert self.manager.current_tab_widget == dataset_tab
    
    def test_get_current_tab_context(self):
        """Test getting current tab context."""
        # Test with no tabs
        context = self.manager.get_current_tab_context()
        assert context["tab_widget"] is None
        
        # Add a tab and set as current
        dataset_tab = MockDatasetTab()
        self.tab_container.tabs.append(dataset_tab)
        self.manager.current_tab_widget = dataset_tab
        
        context = self.manager.get_current_tab_context()
        assert context["tab_widget"] == dataset_tab


class TestPanelConditions:
    """Test cases for panel condition functions."""
    
    def test_is_dataset_tab_active_true(self):
        """Test dataset tab detection when active."""
        dataset_tab = MockDatasetTab()
        assert is_dataset_tab_active(dataset_tab) is True
    
    def test_is_dataset_tab_active_false(self):
        """Test dataset tab detection when not active."""
        welcome_tab = MockWelcomeTab()
        assert is_dataset_tab_active(welcome_tab) is False
    
    def test_is_dataset_tab_active_none(self):
        """Test dataset tab detection with None."""
        assert is_dataset_tab_active(None) is False
    
    def test_is_chart_tab_active_true(self):
        """Test chart tab detection when active."""
        chart_tab = MockChartTab()
        assert is_chart_tab_active(chart_tab) is True
    
    def test_is_chart_tab_active_false(self):
        """Test chart tab detection when not active."""
        dataset_tab = MockDatasetTab()
        assert is_chart_tab_active(dataset_tab) is False
    
    def test_is_transformable_dataset_true(self):
        """Test transformable dataset detection."""
        dataset_tab = MockDatasetTab()
        dataset_tab.dataset.can_transform = Mock(return_value=True)
        
        assert is_transformable_dataset(dataset_tab) is True
    
    def test_is_transformable_dataset_false_no_transform(self):
        """Test transformable dataset when transform not available."""
        dataset_tab = MockDatasetTab()
        dataset_tab.dataset.can_transform = Mock(return_value=False)
        
        assert is_transformable_dataset(dataset_tab) is False
    
    def test_is_transformable_dataset_false_no_dataset(self):
        """Test transformable dataset when no dataset present."""
        welcome_tab = MockWelcomeTab()
        
        assert is_transformable_dataset(welcome_tab) is False


if __name__ == "__main__":
    # Ensure QApplication exists for widget tests
    import sys
    if not QApplication.instance():
        app = QApplication(sys.argv)
    
    pytest.main([__file__])
