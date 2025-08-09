from PySide6.QtWidgets import QMenu, QTabBar
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QAction

class CustomTabBar(QTabBar):
    """Custom tab bar that supports drag and drop reordering and close buttons."""
    
    tab_close_requested = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)  # Enable drag and drop
        self.setTabsClosable(True)  # Enable close buttons
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Connect signals
        self.tabCloseRequested.connect(self.tab_close_requested.emit)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, position: QPoint):
        """Show context menu for tab operations."""
        tab_index = self.tabAt(position)
        if tab_index >= 0:
            menu = QMenu(self)
            
            close_action = QAction("Close Tab", self)
            close_action.triggered.connect(lambda: self.tab_close_requested.emit(tab_index))
            menu.addAction(close_action)
            
            # Show context menu at the cursor position
            menu.exec(self.mapToGlobal(position))


