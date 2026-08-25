import logging
from typing import Optional

from pandaplot.models.events import EventBus
from pandaplot.models.events.event_types import ProjectEvents
from pandaplot.models.project import Project


class AppState:
    """
    Central application state that manages the current project and emits events
    when state changes occur.
    """

    def __init__(self, event_bus: EventBus):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_bus = event_bus

        self._current_project: Optional[Project] = None
        self._is_modified: bool = False

    @property
    def current_project(self) -> Optional[Project]:
        """Get the currently loaded project."""
        return self._current_project

    @property
    def project_file_path(self) -> Optional[str]:
        """Get the file path of the currently loaded project."""
        return self._current_project.project_file_path if self._current_project else None

    @property
    def has_project(self) -> bool:
        """Check if a project is currently loaded."""
        return self._current_project is not None

    @property
    def is_modified(self) -> bool:
        """Whether the current project has unsaved changes.

        Always False when no project is loaded. Set via `mark_modified()`
        (called by CommandExecutor after any command whose
        `marks_project_modified` is True) and cleared via `mark_saved()`
        (called on a successful save) or implicitly by `load_project`/
        `close_project`, since a freshly (re)loaded or absent project has
        nothing unsaved yet.
        """
        return self._is_modified

    def mark_modified(self) -> None:
        """Flag the current project as having unsaved changes."""
        if not self.has_project or self._is_modified:
            return
        self._is_modified = True
        self.event_bus.emit(ProjectEvents.PROJECT_MODIFIED_CHANGED, {"is_modified": True})

    def mark_saved(self) -> None:
        """Flag the current project as having no unsaved changes."""
        if not self._is_modified:
            return
        self._is_modified = False
        self.event_bus.emit(ProjectEvents.PROJECT_MODIFIED_CHANGED, {"is_modified": False})

    def load_project(self, project: Project):
        """
        Load a project into the application state.

        Args:
            project (Project): The project to load.
        """
        self.logger.info("Loading project: %s", project.name)
        old_project = self._current_project
        self._current_project = project
        # A just-(re)loaded project -- new, opened from disk, or reloaded
        # after a save -- has no changes relative to what's on disk yet.
        self._is_modified = False

        # Emit events
        self.event_bus.emit(ProjectEvents.PROJECT_LOADED, {
            "project": project,
            "previous_project": old_project
        })

        if old_project is None:
            # TODO(#210): this should be removed
            self.event_bus.emit(ProjectEvents.FIRST_PROJECT_LOADED, {
                "project": project
            })

    def close_project(self):
        """Close the currently loaded project."""
        self.logger.info("Closing project")
        if self._current_project is not None:
            # TODO(#210): add support for multiple projects
            old_project = self._current_project

            self._current_project = None
            self._is_modified = False

            self.event_bus.emit(ProjectEvents.PROJECT_CLOSED, {
                "project": old_project
            })
