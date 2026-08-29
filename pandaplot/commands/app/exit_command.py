# exit_command.py
# Command to handle application exit in PandaPlot.

from typing import override

from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.commands.project.project.unsaved_changes import confirm_discard_unsaved_changes
from pandaplot.models.events import AppEvents
from pandaplot.models.state.app_context import AppContext


class ExitCommand(Command):
    """
    Command to exit the application.
    """

    # Exiting (or cancelling an exit) isn't itself a project edit.
    marks_project_modified = False

    def __init__(self, app_context: AppContext):
        super().__init__()
        self.app_context = app_context

    @override
    def execute(self) -> CommandResult:
        """
        Execute the exit command. Returns CommandResult.NOOP (without closing
        anything) if the user cancels on an unsaved-changes prompt --
        previously this path had no such check at all, so File > Exit could
        silently discard edits.
        """
        self.logger.info("Executing ExitCommand")
        if not confirm_discard_unsaved_changes(self.app_context):
            self.logger.info("Exit cancelled by user (unsaved changes)")
            return CommandResult.NOOP
        self.app_context.event_bus.emit(AppEvents.APP_CLOSING)
        return CommandResult.SUCCESS

    @override
    def undo(self):
        """
        This is not applicable for exit command.
        """
        self.logger.error("ExitCommand cannot be undone.")
        raise NotImplementedError("Exit command cannot be undone.")

    @override
    def redo(self):
        """
        This is not applicable for exit command.
        """
        self.logger.error("ExitCommand cannot be redone.")
        raise NotImplementedError("Exit command cannot be redone.")

    @override
    def cleanup(self) -> None:
        """No undo state to release -- this command is not undoable."""
        return