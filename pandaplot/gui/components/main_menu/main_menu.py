from typing import override

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget

from pandaplot.commands.app.exit_command import ExitCommand
from pandaplot.commands.project.chart import CreateChartFromWizardCommand
from pandaplot.commands.project.dataset import ImportDataCommand
from pandaplot.commands.project.dataset.create_empty_dataset_command import (
    CreateEmptyDatasetCommand,
)
from pandaplot.commands.project.note import CreateNoteCommand
from pandaplot.commands.project.project import (
    CloseProjectCommand,
    NewProjectCommand,
    OpenProjectCommand,
    SaveProjectAsCommand,
    SaveProjectCommand,
)
from pandaplot.gui.core.widget_extension import PMenuBar
from pandaplot.models.project.items import Dataset
from pandaplot.models.state.app_context import AppContext
from pandaplot.services.theme.theme_manager import ThemeManager


class MainMenu(PMenuBar):
    def __init__(self, parent: QWidget, app_context: AppContext):
        super().__init__(app_context=app_context, parent=parent)
        self._initialize()

    @override
    def _apply_theme(self):
        """Apply theme-specific styling to the main menu based on current theme."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        
        # Get theme-appropriate colors
        card_bg = palette.get("card_bg", "#F0F0F0")
        base_fg = palette.get("base_fg", "#000000")
        card_border = palette.get("card_border", "#D0D0D0")
        accent = palette.get("accent", "#4A90E2")
        card_pressed = palette.get("card_pressed", "#dee2e6")
        
        # Apply dynamic theme-based styling
        self.setStyleSheet(f"""
            QMenuBar {{
                background-color: {card_bg};
                color: {base_fg};
                border-bottom: 1px solid {card_border};
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 4px 8px;
                margin: 2px;
                border-radius: 3px;
            }}
            QMenuBar::item:selected {{
                background-color: {accent};
                color: white;
            }}
            QMenuBar::item:pressed {{
                background-color: {card_pressed};
                color: white;
            }}
            QMenu {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                color: {base_fg};
                margin: 2px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 6px 20px;
                margin: 1px;
            }}
            QMenu::item:selected {{
                background-color: {accent};
                color: white;
            }}
            QMenu::item:pressed {{
                background-color: {card_pressed};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {card_border};
                margin: 2px 10px;
            }}
        """)
        
        self.logger.debug("Applied theme.")
    
    @override
    def _init_ui(self):
        self.logger.debug("Creating main menu")
        
        # File menu
        file_menu = self._create_file_menu()
        self.addMenu(file_menu)

        # Edit menu
        edit_menu = self._create_edit_menu()
        self.addMenu(edit_menu)

        # Data menu
        data_menu = self._create_data_menu()
        self.addMenu(data_menu)

        # Chart menu
        chart_menu = self._create_chart_menu()
        self.addMenu(chart_menu)

        # Settings menu
        settings_menu = QMenu("Settings", self)
        self.addMenu(settings_menu)

        preferences_action = QAction("⚙️ Preferences...", self)
        # TODO: consider showing settings dialog by triggering event which invokes a command
        preferences_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(preferences_action)

        # Help menu
        help_menu = QMenu("Help", self)
        self.addMenu(help_menu)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def _create_file_menu(self) -> QMenu:
        file_menu = QMenu("Project", self)
        new_action = QAction("New", self)
        new_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(NewProjectCommand(self.app_context)))
        file_menu.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(OpenProjectCommand(self.app_context)))
        file_menu.addAction(open_action)

        close_action = QAction("Close", self)
        close_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(CloseProjectCommand(self.app_context)))
        file_menu.addAction(close_action)

        file_menu.addSeparator()

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(SaveProjectCommand(self.app_context)))
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(SaveProjectAsCommand(self.app_context)))
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(ExitCommand(self.app_context)))
        file_menu.addAction(exit_action)

        return file_menu
    
    def _create_edit_menu(self) -> QMenu:
        edit_menu = QMenu("Edit", self)

        # TODO: disable undo/redo when there are no actions to undo/redo
        # self.undo_button.setEnabled(False)  # start disabled
        # we need to listen to app event based on command executor
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(
            lambda: self.app_context.get_command_executor().undo())
        edit_menu.addAction(undo_action)

        

        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(
            lambda: self.app_context.get_command_executor().redo())
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        return edit_menu

    def _create_data_menu(self) -> QMenu:
        data_menu = QMenu("Data", self)

        import_data_action = QAction("Import Data...", self)
        import_data_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(ImportDataCommand(self.app_context)))
        data_menu.addAction(import_data_action)

        create_empty_dataset_action = QAction("Create Empty Dataset", self)
        create_empty_dataset_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(CreateEmptyDatasetCommand(self.app_context)))
        data_menu.addAction(create_empty_dataset_action)

        data_menu.addSeparator()

        new_note_action = QAction("New Note", self)
        new_note_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(CreateNoteCommand(self.app_context)))
        data_menu.addAction(new_note_action)
        return data_menu

    def _create_chart_menu(self) -> QMenu:
        chart_menu = QMenu("Chart", self)

        self.create_chart_action = QAction("Create New", self)
        self.create_chart_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(CreateChartFromWizardCommand(self.app_context)))
        chart_menu.addAction(self.create_chart_action)

        self._update_create_chart_action_enabled()
        return chart_menu

    def _update_create_chart_action_enabled(self):
        app_state = self.app_context.get_app_state()
        has_datasets = False
        if app_state.has_project and app_state.current_project:
            has_datasets = any(
                isinstance(item, Dataset) for item in app_state.current_project.get_all_items()
            )
        self.create_chart_action.setEnabled(has_datasets)

    @override
    def setup_event_subscriptions(self):
        from pandaplot.models.events import ProjectEvents
        self.subscribe_to_event(ProjectEvents.PROJECT_ITEM_ADDED, lambda _data: self._update_create_chart_action_enabled())
        self.subscribe_to_event(ProjectEvents.PROJECT_ITEM_REMOVED, lambda _data: self._update_create_chart_action_enabled())
        self.subscribe_to_event(ProjectEvents.PROJECT_LOADED, lambda _data: self._update_create_chart_action_enabled())
        self.subscribe_to_event(ProjectEvents.PROJECT_CLOSED, lambda _data: self._update_create_chart_action_enabled())

    def show_settings_dialog(self):
        """Show the settings dialog."""
        from pandaplot.gui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.app_context, self.parent())
        dialog.exec()

    def show_about_dialog(self):
        """Show the about dialog."""
        from pandaplot.gui.dialogs.about_dialog import AboutDialog
        dialog = AboutDialog(self.app_context, self.parent())
        dialog.exec()
