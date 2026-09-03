import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Iterable, List, Optional


class CommandResult(Enum):
    """Outcome of `Command.execute()`/`undo()`/`redo()`.

    For `execute()`: SUCCESS/FAILURE map to `CommandExecutor.execute_command()`'s
    True/False return, same as the old bool contract. NOOP is also a "nothing
    happened" outcome -- the command is not pushed onto the undo stack, same
    as FAILURE -- but signals that this was expected (e.g. re-applying
    settings that already match the current config, or renaming to the same
    name), so the executor logs it quietly instead of as a warning.

    For `undo()`/`redo()`: `CommandExecutor.undo()`/`redo()` still always move
    the command between stacks regardless of the result (undoing/redoing is
    assumed to always be attempted, unlike execute()'s NOOP short-circuit) --
    only the log level changes (a warning for FAILURE, debug for NOOP, info
    otherwise).

    A plain Enum, not IntEnum: every member is truthy, so `if
    command.execute():` would silently pass regardless of outcome. Always
    compare explicitly, e.g. `if command.execute() is CommandResult.SUCCESS:`.
    """
    SUCCESS = "success"
    FAILURE = "failure"
    NOOP = "noop"


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

    def cleanup(self) -> None:
        """Called by CommandExecutor when this command is dropped from a
        stack outside the normal undo/redo lifecycle: eviction past
        max_undo_levels, a redo-stack clear, or clear_history(). Not called
        when the command is merely moved between undo_stack and redo_stack
        by undo()/redo(), since it may still need its state then. Default
        no-op; override to release resources held for undo (e.g. a large
        DataFrame snapshot). (Note: a command whose own `undo()`/`redo()`
        raises is also dropped without a `cleanup()` call -- a pre-existing
        gap in the executor's exception handling, not addressed here.)"""
        return

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class CompositeCommand(Command):
    """A command that composes multiple sub-commands into a single atomic action.

    - Executes sub-commands in order. If any sub-command fails or raises an
      exception during `execute()` or `redo()`, already-executed sub-commands
      are rolled back (`undo()`) in reverse order and `CommandResult.FAILURE`
      is returned.
    - `undo()` undoes all sub-commands in reverse order.
    - `redo()` re-executes all sub-commands in forward order.
    - `cleanup()` invokes `cleanup()` on all sub-commands.
    - Occupies a single slot on the `CommandExecutor` undo/redo stack.
    """

    def __init__(self, commands: Optional[Iterable[Command]] = None):
        super().__init__()
        self.commands: List[Command] = list(commands) if commands is not None else []

    def add_command(self, command: Command) -> None:
        """Add a sub-command to the composite."""
        self.commands.append(command)

    @property
    def marks_project_modified(self) -> bool:
        if not self.commands:
            return True
        return any(getattr(cmd, "marks_project_modified", True) for cmd in self.commands)

    def execute(self) -> CommandResult:
        executed: List[Command] = []
        all_noop = True

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

                executed.append(cmd)
                if res is not CommandResult.NOOP:
                    all_noop = False
            except Exception as e:
                self.logger.error(
                    "Sub-command %s raised exception during execute(): %s; rolling back %d completed sub-commands",
                    cmd.__class__.__name__, e, len(executed), exc_info=True,
                )
                self._rollback(executed)
                return CommandResult.FAILURE

        if not self.commands or all_noop:
            return CommandResult.NOOP
        return CommandResult.SUCCESS

    def undo(self) -> CommandResult:
        has_failure = False
        all_noop = True

        for cmd in reversed(self.commands):
            try:
                res = cmd.undo()
                if res is CommandResult.FAILURE:
                    has_failure = True
                    self.logger.warning("Sub-command %s reported failure during undo()", cmd.__class__.__name__)
                elif res is not CommandResult.NOOP:
                    all_noop = False
            except Exception as e:
                has_failure = True
                self.logger.error(
                    "Sub-command %s raised exception during undo(): %s",
                    cmd.__class__.__name__, e, exc_info=True,
                )

        if has_failure:
            return CommandResult.FAILURE
        if not self.commands or all_noop:
            return CommandResult.NOOP
        return CommandResult.SUCCESS

    def redo(self) -> CommandResult:
        redone: List[Command] = []
        all_noop = True

        for cmd in self.commands:
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
                if res is not CommandResult.NOOP:
                    all_noop = False
            except Exception as e:
                self.logger.error(
                    "Sub-command %s raised exception during redo(): %s; rolling back %d redone sub-commands",
                    cmd.__class__.__name__, e, len(redone), exc_info=True,
                )
                self._rollback(redone)
                return CommandResult.FAILURE

        if not self.commands or all_noop:
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
