from PySide6.QtWidgets import (QTabWidget)
from PySide6.QtCore import Signal

from pandaplot.gui.components.tabs.tab_bar import CustomTabBar


class CustomTabWidget(QTabWidget):
    """Custom tab widget with enhanced features."""
    
    tab_close_requested = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set custom tab bar
        self.custom_tab_bar = CustomTabBar()
        self.setTabBar(self.custom_tab_bar)
        
        # Connect signals
        self.custom_tab_bar.tab_close_requested.connect(self.tab_close_requested.emit)
        
        # Apply styling
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C0C0C0;
                background-color: white;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #E1E1E1;
                border: 1px solid #C0C0C0;
                border-bottom: none;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #F0F0F0;
            }
            QTabBar::close-button {
                subcontrol-origin: margin;
                subcontrol-position: center right;
                background-color: #CCCCCC;
                border: 1px solid #999999;
                border-radius: 6px;
                width: 12px;
                height: 12px;
                margin: 2px;
            }
            QTabBar::close-button:hover {
                background-color: #FF6B6B;
                border-color: #FF5252;
            }
            QTabBar::close-button:pressed {
                background-color: #FF5252;
                border-color: #E53935;
            }
            QMenu {
                background-color: white;
                border: 1px solid #C0C0C0;
                color: black;
                margin: 2px;
                border-radius: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 6px 20px;
                margin: 1px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #4A90E2;
                color: white;
            }
            QMenu::item:pressed {
                background-color: #357ABD;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #C0C0C0;
                margin: 2px 10px;
            }
        """)
