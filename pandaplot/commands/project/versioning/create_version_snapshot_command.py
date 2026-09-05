"""Command to create a version snapshot for a project or item."""

from typing import Optional

from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.models.state.app_context import AppContext
from pandaplot.storage.version_manager import VersionManager


class CreateVersionSnapshotCommand(Command):
    """Creates a version snapshot of either an individual item or the entire current project."""

    def __init__(
        self,
        app_context: AppContext,
        label: str = "Snapshot",
        item_id: Optional[str] = None,
    ):
        super().__init__()
        self.app_context = app_context
        self.label = label
        self.item_id = item_id
        self.created_version_id: Optional[str] = None

    def execute(self) -> CommandResult:
        app_state = self.app_context.get_app_state()
        if not app_state.has_project or app_state.current_project is None:
            self.logger.warning("Cannot create version snapshot without an active project.")
            return CommandResult.FAILURE

        # Try to retrieve VersionManager from AppContext or AppState
        version_manager = self.app_context.get_manager(VersionManager) if hasattr(self.app_context, "get_manager") else None
        if version_manager is None:
            # Fallback/default instantiation if not registered as manager
            if not hasattr(app_state, "_version_manager"):
                app_state._version_manager = VersionManager()
            version_manager = app_state._version_manager

        if self.item_id is not None:
            item = app_state.current_project.find_item(self.item_id)
            if item is None:
                self.logger.warning("Item %s not found in project.", self.item_id)
                return CommandResult.FAILURE
            snapshot = version_manager.create_item_snapshot(item, label=self.label)
        else:
            snapshot = version_manager.create_project_snapshot(app_state.current_project, label=self.label)

        self.created_version_id = snapshot.version_id
        return CommandResult.SUCCESS

    def undo(self) -> CommandResult:
        return CommandResult.NOOP

    def redo(self) -> CommandResult:
        return CommandResult.NOOP

    def display_name(self) -> str:
        return f"Create Version Snapshot ({self.label})"
