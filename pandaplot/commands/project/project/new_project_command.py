from pandaplot.commands.base_command import Command
from pandaplot.models.project.project import Project
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState
from pandaplot.gui.controllers.ui_controller import UIController


class NewProjectCommand(Command):
    """
    Command to create a new project.
    This will clear the current project (with user confirmation if needed) and create a fresh project.
    """
    
    def __init__(self, app_context: AppContext):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()
        
        # Store previous state for undo
        self.previous_project = None
        self.previous_file_path = None
        
    def execute(self, *args, **kwargs):
        """Execute the new project command."""
        try:
            # Check if there's a current project - for now we'll just create new project
            # TODO: Add unsaved changes tracking and confirmation later
            if self.app_state.has_project:
                response = self.ui_controller.show_question(
                    "Create New Project",
                    "This will replace the current project.\nDo you want to continue?"
                )
                if not response:
                    return  # User cancelled
            
            # Store current state for undo
            if self.app_state.has_project:
                self.previous_project = self.app_state.current_project
                self.previous_file_path = self.app_state.project_file_path
            
            # Create new project
            new_project = Project(name="New Project", description="A new project created with PandaPlot")
            
            # Update app state - use load_project method
            self.app_state.load_project(new_project, None)  # None file path for new project
            
            print(f"NewProjectCommand: Created new project '{new_project.name}'")
            
        except Exception as e:
            error_msg = f"Failed to create new project: {str(e)}"
            print(f"NewProjectCommand Error: {error_msg}")
            self.ui_controller.show_error_message("New Project Error", error_msg)
            raise
    
    def undo(self):
        """Undo the new project command by restoring the previous project."""
        try:
            if self.previous_project:
                # Restore previous project
                self.app_state.load_project(self.previous_project, self.previous_file_path)
                print(f"NewProjectCommand: Restored previous project '{self.previous_project.name}'")
            else:
                # No previous project, close current project
                self.app_state.close_project()
                print("NewProjectCommand: Closed project (no previous project to restore)")
                
        except Exception as e:
            error_msg = f"Failed to undo new project: {str(e)}"
            print(f"NewProjectCommand Undo Error: {error_msg}")
            self.ui_controller.show_error_message("Undo Error", error_msg)
            
    def redo(self):
        """Redo the new project command."""
        self.execute()

