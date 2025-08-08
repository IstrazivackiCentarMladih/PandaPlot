"""
Modern Settings dialog for the pandaplot application.
Provides a user interface for changing application preferences with modern PySide6 styling.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QWidget, QLabel, QGroupBox, QComboBox,
                             QSpinBox, QCheckBox, QFrame, QColorDialog,
                             QMessageBox)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from typing import Dict, Any


class SettingsDialog(QDialog):
    """Modern settings dialog for configuring application preferences."""
    
    settings_changed = Signal(dict)  # Emitted when settings are applied
    
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.original_settings = {}
        self.current_settings = {}
        
        self.setup_ui()
        self.load_current_settings()
        self.setup_connections()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("⚙️ Application Settings")
        self.setModal(True)
        self.resize(700, 500)
        self.setMinimumSize(650, 450)
        
        # Apply modern styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #212529;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
                margin-top: -1px;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: white;
                color: #495057;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        self.create_header(layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_general_tab()
        self.create_appearance_tab()
        self.create_editor_tab()
        
        # Button frame
        self.create_buttons(layout)
    
    def create_header(self, layout):
        """Create the header section."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title_label = QLabel("⚙️ Application Settings")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Customize your CSV Plotter experience")
        subtitle_label.setStyleSheet("font-size: 14px; color: #6c757d;")
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_frame)
    
    def create_general_tab(self):
        """Create the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Application behavior group
        app_group = QGroupBox("🎯 Application Behavior")
        app_layout = QVBoxLayout(app_group)
        
        # Auto-save settings
        self.auto_save_check = QCheckBox("Enable auto-save for notes")
        self.auto_save_check.setChecked(True)
        app_layout.addWidget(self.auto_save_check)
        
        # Auto-save interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Auto-save interval:"))
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setValue(5)
        self.auto_save_interval.setSuffix(" seconds")
        interval_layout.addWidget(self.auto_save_interval)
        interval_layout.addStretch()
        app_layout.addLayout(interval_layout)
        
        layout.addWidget(app_group)
        layout.addStretch()
        self.tab_widget.addTab(tab, "🎯 General")
    
    def create_appearance_tab(self):
        """Create the appearance settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Theme group
        theme_group = QGroupBox("🎨 Theme and Colors")
        theme_layout = QVBoxLayout(theme_group)
        
        # Theme selection
        theme_selection_layout = QHBoxLayout()
        theme_selection_layout.addWidget(QLabel("Application theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Auto (System)"])
        self.theme_combo.setCurrentText("Light")
        theme_selection_layout.addWidget(self.theme_combo)
        theme_selection_layout.addStretch()
        theme_layout.addLayout(theme_selection_layout)
        
        # Accent color
        accent_layout = QHBoxLayout()
        accent_layout.addWidget(QLabel("Accent color:"))
        self.accent_color_btn = QPushButton()
        self.accent_color_btn.setFixedSize(60, 30)
        self.accent_color_btn.setStyleSheet("background-color: #007bff; border-radius: 4px;")
        self.accent_color_btn.clicked.connect(self.choose_accent_color)
        accent_layout.addWidget(self.accent_color_btn)
        accent_layout.addStretch()
        theme_layout.addLayout(accent_layout)
        
        layout.addWidget(theme_group)
        
        # Font group
        font_group = QGroupBox("🔤 Fonts")
        font_layout = QVBoxLayout(font_group)
        
        # Interface font size
        interface_font_layout = QHBoxLayout()
        interface_font_layout.addWidget(QLabel("Interface font size:"))
        self.interface_font_size = QSpinBox()
        self.interface_font_size.setRange(8, 20)
        self.interface_font_size.setValue(10)
        self.interface_font_size.setSuffix(" pt")
        interface_font_layout.addWidget(self.interface_font_size)
        interface_font_layout.addStretch()
        font_layout.addLayout(interface_font_layout)
        
        # Editor font size
        editor_font_layout = QHBoxLayout()
        editor_font_layout.addWidget(QLabel("Editor font size:"))
        self.editor_font_size = QSpinBox()
        self.editor_font_size.setRange(8, 24)
        self.editor_font_size.setValue(11)
        self.editor_font_size.setSuffix(" pt")
        editor_font_layout.addWidget(self.editor_font_size)
        editor_font_layout.addStretch()
        font_layout.addLayout(editor_font_layout)
        
        layout.addWidget(font_group)
        layout.addStretch()
        self.tab_widget.addTab(tab, "🎨 Appearance")
    
    def create_editor_tab(self):
        """Create the editor settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Text editing group
        editing_group = QGroupBox("📝 Text Editing")
        editing_layout = QVBoxLayout(editing_group)
        
        # Word wrap
        self.word_wrap_check = QCheckBox("Enable word wrap in note editor")
        self.word_wrap_check.setChecked(True)
        editing_layout.addWidget(self.word_wrap_check)
        
        # Show line numbers
        self.line_numbers_check = QCheckBox("Show line numbers")
        self.line_numbers_check.setChecked(False)
        editing_layout.addWidget(self.line_numbers_check)
        
        # Tab size
        tab_size_layout = QHBoxLayout()
        tab_size_layout.addWidget(QLabel("Tab size:"))
        self.tab_size_spin = QSpinBox()
        self.tab_size_spin.setRange(2, 8)
        self.tab_size_spin.setValue(4)
        self.tab_size_spin.setSuffix(" spaces")
        tab_size_layout.addWidget(self.tab_size_spin)
        tab_size_layout.addStretch()
        editing_layout.addLayout(tab_size_layout)
        
        layout.addWidget(editing_group)
        layout.addStretch()
        self.tab_widget.addTab(tab, "📝 Editor")
    
    def create_buttons(self, layout):
        """Create the button frame."""
        button_frame = QFrame()
        button_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
            }
        """)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(16, 12, 16, 12)
        
        # Reset button
        self.reset_btn = QPushButton("🔄 Reset to Defaults")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # Apply button
        self.apply_btn = QPushButton("✅ Apply")
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        # OK button
        self.ok_btn = QPushButton("💾 OK")
        self.ok_btn.clicked.connect(self.accept_settings)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)
        
        layout.addWidget(button_frame)
    
    def setup_connections(self):
        """Set up signal connections."""
        # Connect theme change to preview
        self.theme_combo.currentTextChanged.connect(self.preview_theme)
        
        # Connect font size changes to preview
        self.interface_font_size.valueChanged.connect(self.preview_interface_font)
        self.editor_font_size.valueChanged.connect(self.preview_editor_font)
    
    def load_current_settings(self):
        """Load current settings from the application."""
        # TODO: Load from actual settings storage
        self.original_settings = {
            'auto_save': True,
            'auto_save_interval': 5,
            'theme': 'Light',
            'accent_color': '#007bff',
            'interface_font_size': 10,
            'editor_font_size': 11,
            'word_wrap': True,
            'line_numbers': False,
            'tab_size': 4
        }
        
        self.current_settings = self.original_settings.copy()
        self.apply_settings_to_ui()
    
    def apply_settings_to_ui(self):
        """Apply current settings to UI controls."""
        self.auto_save_check.setChecked(self.current_settings['auto_save'])
        self.auto_save_interval.setValue(self.current_settings['auto_save_interval'])
        self.theme_combo.setCurrentText(self.current_settings['theme'])
        self.interface_font_size.setValue(self.current_settings['interface_font_size'])
        self.editor_font_size.setValue(self.current_settings['editor_font_size'])
        self.word_wrap_check.setChecked(self.current_settings['word_wrap'])
        self.line_numbers_check.setChecked(self.current_settings['line_numbers'])
        self.tab_size_spin.setValue(self.current_settings['tab_size'])
        
        # Update accent color button
        color = self.current_settings['accent_color']
        self.accent_color_btn.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
    
    def get_current_settings_from_ui(self) -> Dict[str, Any]:
        """Get current settings from UI controls."""
        return {
            'auto_save': self.auto_save_check.isChecked(),
            'auto_save_interval': self.auto_save_interval.value(),
            'theme': self.theme_combo.currentText(),
            'accent_color': self.current_settings['accent_color'],  # Updated via color picker
            'interface_font_size': self.interface_font_size.value(),
            'editor_font_size': self.editor_font_size.value(),
            'word_wrap': self.word_wrap_check.isChecked(),
            'line_numbers': self.line_numbers_check.isChecked(),
            'tab_size': self.tab_size_spin.value()
        }
    
    def choose_accent_color(self):
        """Open color picker for accent color."""
        current_color = QColor(self.current_settings['accent_color'])
        color = QColorDialog.getColor(current_color, self, "Choose Accent Color")
        
        if color.isValid():
            color_str = color.name()
            self.current_settings['accent_color'] = color_str
            self.accent_color_btn.setStyleSheet(f"background-color: {color_str}; border-radius: 4px;")
    
    def preview_theme(self, theme_name):
        """Preview theme changes."""
        # TODO: Implement theme preview
        pass
    
    def preview_interface_font(self, size):
        """Preview interface font changes."""
        # TODO: Implement font preview
        pass
    
    def preview_editor_font(self, size):
        """Preview editor font changes."""
        # TODO: Implement editor font preview
        pass
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to defaults
            default_settings = {
                'auto_save': True,
                'auto_save_interval': 5,
                'theme': 'Light',
                'accent_color': '#007bff',
                'interface_font_size': 10,
                'editor_font_size': 11,
                'word_wrap': True,
                'line_numbers': False,
                'tab_size': 4
            }
            
            self.current_settings = default_settings.copy()
            self.apply_settings_to_ui()
    
    def apply_settings(self):
        """Apply settings without closing the dialog."""
        self.current_settings = self.get_current_settings_from_ui()
        self.settings_changed.emit(self.current_settings)
        
        # Show confirmation
        QMessageBox.information(
            self,
            "Settings Applied",
            "Settings have been applied successfully."
        )
    
    def accept_settings(self):
        """Apply settings and close the dialog."""
        self.current_settings = self.get_current_settings_from_ui()
        self.settings_changed.emit(self.current_settings)
        self.accept()
    
    def reject(self):
        """Cancel and close the dialog without applying changes."""
        # Check if settings have changed
        current_ui_settings = self.get_current_settings_from_ui()
        
        if current_ui_settings != self.original_settings:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to close without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        super().reject()
    
    @staticmethod
    def show_settings_dialog(app_context, parent=None):
        """Convenient static method to show the settings dialog."""
        dialog = SettingsDialog(app_context, parent)
        return dialog.exec()
