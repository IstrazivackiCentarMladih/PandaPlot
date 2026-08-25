import logging
from abc import ABC, abstractmethod


class Command(ABC):
    # Whether a successful execute()/undo()/redo() of this command should
    # flag the project as having unsaved changes (see
    # CommandExecutor.on_project_modified). False for the project-lifecycle
    # commands themselves (new/open/load/save/close), which manage
    # AppState's modified flag explicitly instead.
    marks_project_modified: bool = True

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(self) -> bool:
        pass

    @abstractmethod
    def undo(self):
        pass

    @abstractmethod
    def redo(self):
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}()"
