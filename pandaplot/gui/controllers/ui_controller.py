from PySide6.QtWidgets import QFileDialog, QWidget, QMessageBox, QInputDialog
from typing import Optional

# TODO: ui controller should be a facade for all UI-related interactions
# This allows us to keep UI logic separate from business logic in the MVC pattern.
# It can handle dialogs, notifications, and other user interactions.


class UIController:
    """
    UI Controller that handles user interface interactions like dialogs.
    This separates UI logic from business logic in the MVC pattern.
    """
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        self.parent_widget = parent_widget
    
    def show_open_project_dialog(self) -> Optional[str]:
        """
        Show file dialog to open a project file.
        
        Returns:
            str: Selected file path, or None if cancelled
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent_widget,
            "Open Project",
            "",
            "Project files (*.pplot);;JSON files (*.json);;All files (*.*)"
        )
        
        return file_path if file_path else None
    
    def show_save_project_dialog(self, default_name: str = "untitled.pplot") -> Optional[str]:
        """
        Show file dialog to save a project file.
        
        Args:
            default_name (str): Default filename
            
        Returns:
            str: Selected file path, or None if cancelled
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent_widget,
            "Save Project",
            default_name,
            "Project files (*.pplot);;JSON files (*.json);;All files (*.*)"
        )
        
        return file_path if file_path else None
    
    def show_import_csv_dialog(self) -> Optional[str]:
        """
        Show file dialog to import a CSV file.
        
        Returns:
            str: Selected file path, or None if cancelled
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent_widget,
            "Import CSV File",
            "",
            "CSV files (*.csv);;Text files (*.txt);;All files (*.*)"
        )
        
        return file_path if file_path else None
    
    def show_error_message(self, title: str, message: str):
        """
        Show an error message dialog.
        
        Args:
            title (str): Dialog title
            message (str): Error message
        """
        QMessageBox.critical(self.parent_widget, title, message)
    
    def show_warning_message(self, title: str, message: str):
        """
        Show a warning message dialog.
        
        Args:
            title (str): Dialog title
            message (str): Warning message
        """
        QMessageBox.warning(self.parent_widget, title, message)
    
    def show_info_message(self, title: str, message: str):
        """
        Show an information message dialog.
        
        Args:
            title (str): Dialog title
            message (str): Information message
        """
        QMessageBox.information(self.parent_widget, title, message)
    
    def show_question(self, title: str, message: str) -> bool:
        """
        Show a yes/no question dialog.
        
        Args:
            title (str): Dialog title
            message (str): Question message
            
        Returns:
            bool: True if user clicked Yes, False if No
        """
        reply = QMessageBox.question(
            self.parent_widget,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def show_confirmation(self, title: str, message: str, details: str|None = None) -> bool:
        """
        Show a confirmation dialog with optional details.
        
        Args:
            title (str): Dialog title
            message (str): Main message
            details (str, optional): Detailed information
            
        Returns:
            bool: True if user confirmed, False otherwise
        """
        msg_box = QMessageBox(self.parent_widget)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
        
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
        
        reply = msg_box.exec()
        return reply == QMessageBox.StandardButton.Ok

    def get_text_input(self, title: str, message: str, default_text: str = "") -> Optional[str]:
        """
        Show a text input dialog.
        
        Args:
            title (str): Dialog title
            message (str): Input prompt message
            default_text (str): Default text to show in input field
            
        Returns:
            str: User input text, or None if cancelled
        """
        text, ok = QInputDialog.getText(self.parent_widget, title, message, text=default_text)
        return text if ok else None
    
    def set_parent_widget(self, parent_widget: QWidget):
        """Set the parent widget for dialogs."""
        self.parent_widget = parent_widget
