from PySide6.QtWidgets import QStackedWidget


class PanelArea(QStackedWidget):
    """Panel area component that holds and manages panel content."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.panels = {}  # Store panel names and their widgets
        self.setStyleSheet("background-color: #ffffff;")

    def add_panel(self, name, content_widget):
        """Add a new panel to the area."""
        content_widget.setStyleSheet("background-color: #ffffff;")
        self.addWidget(content_widget)
        self.panels[name] = content_widget

    def remove_panel(self, name):
        """Remove a panel from the area."""
        if name in self.panels:
            widget = self.panels[name]
            self.removeWidget(widget)
            widget.deleteLater()
            del self.panels[name]

    def show_panel(self, name):
        """Show a specific panel."""
        if name in self.panels:
            self.setCurrentWidget(self.panels[name])
            return True
        return False

    def get_current_panel_name(self):
        """Get the name of the currently visible panel."""
        current_widget = self.currentWidget()
        for name, widget in self.panels.items():
            if widget == current_widget:
                return name
        return None
