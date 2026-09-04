from typing import Iterable, List, Optional

from pandaplot.commands.base_command import Command, CommandResult


class CompositeCommand(Command):
    """A command that composes multiple sub-commands into a single atomic
    undo/redo unit on the CommandExecutor stack.

    `execute()`, `undo()`, and `redo()` all share the same all-or-nothing
    contract: each stops at the first sub-command that returns FAILURE or
    raises, rolls back whatever it already did *this call* (undoing a
    partial execute()/redo(), or re-applying a partial undo()), and reports
    FAILURE. So FAILURE always means nothing net changed -- never a silent
    partial mutation left for the next save to miss. A sub-command that
    returned NOOP made no change either, so it's excluded from the set the
    next call operates on, same as one rolled back after a failure.

    Because CommandExecutor moves a command between the undo/redo stacks
    regardless of what undo()/redo() returns, a FAILURE here still gets
    followed by an executor-driven call in the opposite direction that the
    composite has no way to decline. Since nothing net changed, that call
    would be operating on a composite already back in its pre-call state --
    so a FAILURE from undo() or redo() also empties the replay set, making
    the composite inert (a no-op) for that unavoidable next call and beyond,
    rather than risk it re-applying or re-reversing something that was
    never actually touched.

    `cleanup()` invokes `cleanup()` on every configured sub-command.
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
        undone: List[Command] = []

        for cmd in reversed(self._executed):
            try:
                res = cmd.undo()
                if res is CommandResult.FAILURE:
                    self.logger.warning(
                        "Sub-command %s failed during undo(); rolling back %d undone sub-commands",
                        cmd.__class__.__name__, len(undone),
                    )
                    self._rollback_undo(undone)
                    # Nothing net changed (still fully applied), but
                    # CommandExecutor moves this composite to the redo stack
                    # regardless of this FAILURE. Go inert rather than risk a
                    # later redo() re-applying sub-commands that were never
                    # actually undone.
                    self._executed = []
                    return CommandResult.FAILURE

                if res is not CommandResult.NOOP:
                    undone.append(cmd)
            except Exception as e:
                self.logger.error(
                    "Sub-command %s raised exception during undo(): %s; rolling back %d undone sub-commands",
                    cmd.__class__.__name__, e, len(undone), exc_info=True,
                )
                self._rollback_undo(undone)
                self._executed = []
                return CommandResult.FAILURE

        self._executed = list(reversed(undone))
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
                    # The rolled-back prefix is undone again and the
                    # never-reached remainder was already undone, but
                    # CommandExecutor.redo() moves this composite to the
                    # undo stack regardless of this FAILURE. Go inert rather
                    # than risk a later undo() re-undoing sub-commands that
                    # are already back in their undone state.
                    self._executed = []
                    return CommandResult.FAILURE

                if res is not CommandResult.NOOP:
                    redone.append(cmd)
            except Exception as e:
                self.logger.error(
                    "Sub-command %s raised exception during redo(): %s; rolling back %d redone sub-commands",
                    cmd.__class__.__name__, e, len(redone), exc_info=True,
                )
                self._rollback(redone)
                self._executed = []
                return CommandResult.FAILURE

        self._executed = redone
        if not redone:
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

    def _rollback_undo(self, undone: List[Command]) -> None:
        """Re-apply sub-commands already undone earlier in this same undo()
        call, so a failure partway through never leaves a partial mutation
        in place. Mirrors _rollback(), but redo()es instead of undo()ing
        since it's reversing an undo rather than an execute()/redo()."""
        for cmd in reversed(undone):
            try:
                cmd.redo()
            except Exception as e:
                self.logger.error(
                    "Error rolling back (re-applying) sub-command %s: %s",
                    cmd.__class__.__name__, e, exc_info=True,
                )

    def __repr__(self):
        return f"{self.__class__.__name__}(count={len(self.commands)})"


MacroCommand = CompositeCommand
