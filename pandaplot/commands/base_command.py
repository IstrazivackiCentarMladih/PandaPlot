import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Iterable, List, Optional


class CommandResult(StrEnum):
    """Outcome of `Command.execute()`/`undo()`/`redo()`.

    SUCCESS/FAILURE/NOOP determine `CommandExecutor`'s log level (info,
    warning, debug respectively) and, for `execute()`, whether the command is
    pushed onto the undo stack (SUCCESS only; FAILURE and NOOP are not).
    `undo()`/`redo()` always move the command between stacks regardless of
    result.

    Always compare explicitly (`if command.execute() is
    CommandResult.SUCCESS:`) -- every member is truthy, so `if
    command.execute():` would silently pass regardless of outcome.
    """
    SUCCESS = "success"
    FAILURE = "failure"
    NOOP = "noop"


class Command(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(self) -> CommandResult:
        pass

    @abstractmethod
    def undo(self) -> CommandResult:
        pass

    @abstractmethod
    def redo(self) -> CommandResult:
        pass

    def occupies_undo_slot(self) -> bool:
        """Whether this command should be pushed onto/moved between the
        undo/redo stacks. Default True; override to False for a command
        whose real effect doesn't happen synchronously inside execute() --
        e.g. one that opens a dialog and does its actual work later, in a
        callback, via its own execute_command() call (see
        CreateChartFromWizardCommand)."""
        return True

    def marks_project_modified(self) -> bool:
        """Whether a successful execute()/undo()/redo() of this command
        should flag the project as having unsaved changes (see
        CommandExecutor.on_project_modified). Default True; override to
        False for project-lifecycle commands (new/open/load/save/close),
        which manage AppState's modified flag explicitly instead."""
        return True

    def cleanup(self) -> None:
        """Called by CommandExecutor when this command is dropped from a
        stack outside the normal undo/redo lifecycle: eviction past
        max_undo_levels, a redo-stack clear, or clear_history(). Not called
        when the command is merely moved between undo_stack and redo_stack
        by undo()/redo(). Default no-op; override to release resources held
        for undo (e.g. a large DataFrame snapshot)."""
        return

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class CompositeCommand(Command):
    """A command that composes multiple sub-commands into a single atomic
    undo/redo unit on the CommandExecutor stack.

    - `execute()` runs sub-commands in order. If one returns FAILURE or
      raises, already-executed sub-commands are undone in reverse order and
      FAILURE is returned. Sub-commands that returned NOOP had no effect, so
      they're excluded from the executed set `undo()`/`redo()` operate on --
      calling undo() on them could fail or undo state they never touched.
    - `undo()` undoes the executed set in reverse order; `redo()` re-executes
      it in forward order, rolling back on FAILURE the same way `execute()`
      does.
    - `cleanup()` invokes `cleanup()` on every configured sub-command.
    """

    def __init__(self, commands: Optional[Iterable[Command]] = None):
        super().__init__()
        self.commands: List[Command] = list(commands) if commands is not None else []
        self._executed: List[Command] = []

    def add_command(self, command: Command) -> None:
        """Add a sub-command to the composite."""
        self.commands.append(command)

    def marks_project_modified(self) -> bool:
        if not self.commands:
            return True
        if not self._executed:
            return True
        return any(cmd.marks_project_modified() for cmd in self._executed)

    def execute(self) -> CommandResult:
        executed: List[Command] = []

        for cmd in self.commands:
            try:
                res = cmd.execute()
                if res is CommandResult.FAILURE:
                    self.logger.warning(
                        "Sub-command %s failed during execute(); rolling back %d completed sub-commands",
                        cmd.__class__.__name__, len(executed),
                    )
                    self._rollback(executed)
                    return CommandResult.FAILURE

                if res is not CommandResult.NOOP:
                    executed.append(cmd)
            except Exception as e:
                self.logger.error(
                    "Sub-command %s raised exception during execute(): %s; rolling back %d completed sub-commands",
                    cmd.__class__.__name__, e, len(executed), exc_info=True,
                )
                self._rollback(executed)
                return CommandResult.FAILURE

        self._executed = executed
        if not self.commands or not executed:
            return CommandResult.NOOP
        return CommandResult.SUCCESS

    def undo(self) -> CommandResult:
        has_failure = False

        for cmd in reversed(self._executed):
            try:
                res = cmd.undo()
                if res is CommandResult.FAILURE:
                    has_failure = True
                    self.logger.warning("Sub-command %s reported failure during undo()", cmd.__class__.__name__)
            except Exception as e:
                has_failure = True
                self.logger.error(
                    "Sub-command %s raised exception during undo(): %s",
                    cmd.__class__.__name__, e, exc_info=True,
                )

        if has_failure:
            return CommandResult.FAILURE
        if not self._executed:
            return CommandResult.NOOP
        return CommandResult.SUCCESS

    def redo(self) -> CommandResult:
        redone: List[Command] = []

        for cmd in self._executed:
            try:
                res = cmd.redo()
                if res is CommandResult.FAILURE:
                    self.logger.warning(
                        "Sub-command %s failed during redo(); rolling back %d redone sub-commands",
                        cmd.__class__.__name__, len(redone),
                    )
                    self._rollback(redone)
                    return CommandResult.FAILURE

                redone.append(cmd)
            except Exception as e:
                self.logger.error(
                    "Sub-command %s raised exception during redo(): %s; rolling back %d redone sub-commands",
                    cmd.__class__.__name__, e, len(redone), exc_info=True,
                )
                self._rollback(redone)
                return CommandResult.FAILURE

        if not self._executed:
            return CommandResult.NOOP
        return CommandResult.SUCCESS

    def cleanup(self) -> None:
        for cmd in self.commands:
            try:
                cmd.cleanup()
            except Exception as e:
                self.logger.error(
                    "Error cleaning up sub-command %s: %s",
                    cmd.__class__.__name__, e, exc_info=True,
                )

    def _rollback(self, executed: List[Command]) -> None:
        for cmd in reversed(executed):
            try:
                cmd.undo()
            except Exception as e:
                self.logger.error(
                    "Error rolling back sub-command %s: %s",
                    cmd.__class__.__name__, e, exc_info=True,
                )

    def __repr__(self):
        return f"{self.__class__.__name__}(count={len(self.commands)})"


MacroCommand = CompositeCommand
