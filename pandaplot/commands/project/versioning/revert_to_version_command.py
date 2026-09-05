"""Command to revert a project or item to a previously recorded snapshot."""

import pandas as pd
from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.models.events.event_types import ProjectEvents
from pandaplot.models.project import Project
from pandaplot.models.project.items import Chart, Dataset, ImageGallery, Note
from pandaplot.models.state.app_context import AppContext
from pandaplot.storage.version_manager import VersionManager


class RevertToVersionCommand(Command):
    """Reverts the target project or item to a specific snapshot state."""

    def __init__(self, app_context: AppContext, version_id: str):
        super().__init__()
        self.app_context = app_context
        self.version_id = version_id

    def execute(self) -> CommandResult:
        app_state = self.app_context.get_app_state()
        if not app_state.has_project or app_state.current_project is None:
            self.logger.warning("Cannot revert version without an active project.")
            return CommandResult.FAILURE

        version_manager = self.app_context.get_manager(VersionManager) if hasattr(self.app_context, "get_manager") else None
        if version_manager is None:
            if hasattr(app_state, "_version_manager"):
                version_manager = app_state._version_manager
            else:
                self.logger.warning("VersionManager not available.")
                return CommandResult.FAILURE

        snapshot = version_manager.get_snapshot(self.version_id)
        if snapshot is None:
            self.logger.warning("Version snapshot %s not found.", self.version_id)
            return CommandResult.FAILURE

        if snapshot.version_type == "project":
            restored_project = Project.from_dict(snapshot.data)
            app_state.load_project(restored_project)
            event_bus = self.app_context.get_event_bus()
            event_bus.emit(ProjectEvents.PROJECT_LOADED, {"project": restored_project})
            self.logger.info("Reverted project to version snapshot %s", self.version_id)
            return CommandResult.SUCCESS

        elif snapshot.version_type == "item" and snapshot.item_id:
            current_project = app_state.current_project
            item = current_project.find_item(snapshot.item_id)
            if item is None:
                self.logger.warning("Target item %s not found in project.", snapshot.item_id)
                return CommandResult.FAILURE

            # Restore item fields from serialized dict
            data = snapshot.data
            item.name = data.get("name", item.name)

            if isinstance(item, Dataset):
                if "_df_dict" in data:
                    item.data = pd.DataFrame.from_dict(data["_df_dict"])
            elif isinstance(item, Note):
                if "content" in data:
                    item.content = data["content"]
            elif isinstance(item, Chart):
                if "config" in data:
                    item.config = data["config"]
                if "style" in data:
                    item.style = data["style"]
                if "chart_type" in data:
                    item.chart_type = data["chart_type"]

            event_bus = self.app_context.get_event_bus()
            event_bus.emit(ProjectEvents.PROJECT_STRUCTURE_CHANGED, {"item_id": item.id, "item": item})
            self.logger.info("Reverted item %s to version snapshot %s", item.id, self.version_id)
            return CommandResult.SUCCESS

        return CommandResult.FAILURE

    def undo(self) -> CommandResult:
        return CommandResult.NOOP

    def redo(self) -> CommandResult:
        return CommandResult.NOOP

    def display_name(self) -> str:
        return f"Revert to Version ({self.version_id})"
