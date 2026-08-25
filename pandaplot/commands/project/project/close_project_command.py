"""Command to close the current project."""
from typing import override

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.state.app_context import AppContext
from pandaplot.services.session import SessionPersistenceManager


class CloseProjectCommand(Command):
    """Command to close the currently loaded project."""

    # Closing sets AppState's modified flag explicitly (close_project always
    # resets it) -- not a project edit itself.
    marks_project_modified = False

    def __init__(self, app_context: AppContext):
        super().__init__()
        self.app_context = app_context
        self.ui_controller: UIController = app_context.get_ui_controller()

    @override
    def execute(self) -> bool:
        """Close the current project if one is loaded."""
        try:
            app_state = self.app_context.get_app_state()

            if not app_state.has_project:
                self.logger.info("No project is currently loaded")
                return True

            project_name = app_state.current_project.name if app_state.current_project else "Unknown"

            # Give the user a chance to save/cancel if there are unsaved
            # changes -- previously this closed silently and discarded them.
            if app_state.is_modified:
                should_continue = self.ui_controller.show_question(
                    "Close Project",
                    f"Project '{project_name}' has unsaved changes.\n"
                    "Closing now will discard them.\n\nDo you want to continue?",
                )
                if not should_continue:
                    self.logger.info("Close project cancelled by user (unsaved changes)")
                    return False

            self.logger.info(f"Closing project: {project_name}")

            # Close the project - this will emit PROJECT_CLOSED event
            app_state.close_project()

            # Explicit close means don't reopen this project/its tabs next launch
            try:
                session_manager = self.app_context.get_manager(SessionPersistenceManager)
                session_manager.reset()
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Failed to clear session state: %s", e)

            self.logger.info("Project closed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to close project: {e}")
            self.ui_controller.show_error_message("Close Project Error", str(e))
            return False

    @override
    def undo(self):
        """Undo is not supported for project closing."""
        self.logger.warning("Cannot undo project close operation")
        return False

    @override 
    def redo(self):
        """Redo is not supported for project closing."""
        self.logger.warning("Cannot redo project close operation")
        return False