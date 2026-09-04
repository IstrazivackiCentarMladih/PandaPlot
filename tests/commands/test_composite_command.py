from typing import List, Optional
from unittest.mock import Mock

from pandaplot.commands import Command, CommandExecutor, CommandResult, CompositeCommand, MacroCommand


class SimpleCommand(Command):
    """Test command recording each call and returning configurable results."""

    def __init__(
        self,
        name: str,
        *,
        execute_result: CommandResult = CommandResult.SUCCESS,
        undo_result: CommandResult = CommandResult.SUCCESS,
        redo_result: CommandResult = CommandResult.SUCCESS,
        execute_exception: Optional[Exception] = None,
        undo_exception: Optional[Exception] = None,
        redo_exception: Optional[Exception] = None,
        marks_modified: bool = True,
    ):
        super().__init__()
        self.name = name
        self.execute_result = execute_result
        self.undo_result = undo_result
        self.redo_result = redo_result
        self.execute_exception = execute_exception
        self.undo_exception = undo_exception
        self.redo_exception = redo_exception
        self._marks_modified = marks_modified

        self.executed_count = 0
        self.undone_count = 0
        self.redone_count = 0
        self.cleanup_count = 0

    def execute(self) -> CommandResult:
        self.executed_count += 1
        if self.execute_exception:
            raise self.execute_exception
        return self.execute_result

    def undo(self) -> CommandResult:
        self.undone_count += 1
        if self.undo_exception:
            raise self.undo_exception
        return self.undo_result

    def redo(self) -> CommandResult:
        self.redone_count += 1
        if self.redo_exception:
            raise self.redo_exception
        return self.redo_result

    def marks_project_modified(self) -> bool:
        return self._marks_modified

    def cleanup(self) -> None:
        self.cleanup_count += 1

    def __repr__(self):
        return f"SimpleCommand({self.name})"


def test_alias_macro_command():
    assert MacroCommand is CompositeCommand


def test_empty_composite_command_execute():
    cmd = CompositeCommand()
    assert repr(cmd) == "CompositeCommand(count=0)"
    assert cmd.execute() is CommandResult.NOOP
    assert cmd.undo() is CommandResult.NOOP
    assert cmd.redo() is CommandResult.NOOP


def test_composite_command_forward_execution():
    call_order: List[str] = []

    class TrackedCommand(SimpleCommand):
        def execute(self) -> CommandResult:
            call_order.append(f"exec_{self.name}")
            return super().execute()

    cmd1 = TrackedCommand("c1")
    cmd2 = TrackedCommand("c2")
    composite = CompositeCommand([cmd1, cmd2])

    assert composite.execute() is CommandResult.SUCCESS
    assert call_order == ["exec_c1", "exec_c2"]
    assert cmd1.executed_count == 1
    assert cmd2.executed_count == 1


def test_composite_command_add_command():
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2")
    composite = CompositeCommand()
    composite.add_command(cmd1)
    composite.add_command(cmd2)

    assert len(composite.commands) == 2
    assert composite.execute() is CommandResult.SUCCESS
    assert cmd1.executed_count == 1
    assert cmd2.executed_count == 1


def test_composite_command_rollback_on_failure():
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2", execute_result=CommandResult.FAILURE)
    cmd3 = SimpleCommand("c3")

    composite = CompositeCommand([cmd1, cmd2, cmd3])
    result = composite.execute()

    assert result is CommandResult.FAILURE
    assert cmd1.executed_count == 1
    assert cmd1.undone_count == 1  # Rolled back
    assert cmd2.executed_count == 1
    assert cmd2.undone_count == 0  # Failed during execute, not rolled back
    assert cmd3.executed_count == 0  # Never reached


def test_composite_command_rollback_on_exception():
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2", execute_exception=RuntimeError("exec error"))
    cmd3 = SimpleCommand("c3")

    composite = CompositeCommand([cmd1, cmd2, cmd3])
    result = composite.execute()

    assert result is CommandResult.FAILURE
    assert cmd1.executed_count == 1
    assert cmd1.undone_count == 1
    assert cmd2.executed_count == 1
    assert cmd2.undone_count == 0
    assert cmd3.executed_count == 0


def test_composite_command_undo_reverse_order():
    call_order: List[str] = []

    class TrackedCommand(SimpleCommand):
        def undo(self) -> CommandResult:
            call_order.append(f"undo_{self.name}")
            return super().undo()

    cmd1 = TrackedCommand("c1")
    cmd2 = TrackedCommand("c2")
    cmd3 = TrackedCommand("c3")

    composite = CompositeCommand([cmd1, cmd2, cmd3])
    assert composite.execute() is CommandResult.SUCCESS

    call_order.clear()
    assert composite.undo() is CommandResult.SUCCESS
    assert call_order == ["undo_c3", "undo_c2", "undo_c1"]
    assert cmd1.undone_count == 1
    assert cmd2.undone_count == 1
    assert cmd3.undone_count == 1


def test_composite_command_undo_failure_and_exception():
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2", undo_result=CommandResult.FAILURE)
    cmd3 = SimpleCommand("c3", undo_exception=RuntimeError("undo error"))

    composite = CompositeCommand([cmd1, cmd2, cmd3])
    composite.execute()

    assert composite.undo() is CommandResult.FAILURE
    # Should still attempt undo on all subcommands
    assert cmd3.undone_count == 1
    assert cmd2.undone_count == 1
    assert cmd1.undone_count == 1


def test_composite_command_undo_partial_failure_excludes_still_applied_subcommand_from_redo():
    """A sub-command whose undo() fails is left applied (its effect never
    reversed). It must not be replayed by a later redo() -- that would
    double-apply it -- while a sub-command that did undo successfully still
    redoes normally (see PR #333 review)."""
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2", undo_result=CommandResult.FAILURE)

    composite = CompositeCommand([cmd1, cmd2])
    composite.execute()

    assert composite.undo() is CommandResult.FAILURE
    assert cmd1.undone_count == 1
    assert cmd2.undone_count == 1  # attempted, but failed -- still applied

    cmd1.redone_count = 0
    cmd2.redone_count = 0

    assert composite.redo() is CommandResult.SUCCESS
    assert cmd1.redone_count == 1
    assert cmd2.redone_count == 0  # excluded: never actually undone


def test_composite_command_undo_excludes_noop_subcommands_from_replay_set():
    """A sub-command that returns NOOP from undo() reversed no state, so it
    must not be replayed by a later redo() (see PR #333 review)."""
    cmd_noop = SimpleCommand("noop", undo_result=CommandResult.NOOP)
    cmd_real = SimpleCommand("real")

    composite = CompositeCommand([cmd_noop, cmd_real])
    composite.execute()

    assert composite.undo() is CommandResult.SUCCESS  # cmd_real did undo

    cmd_noop.redone_count = 0
    cmd_real.redone_count = 0

    assert composite.redo() is CommandResult.SUCCESS
    assert cmd_noop.redone_count == 0  # excluded: nothing was undone to redo
    assert cmd_real.redone_count == 1


def test_composite_command_redo_failure_leaves_composite_inert_not_re_undoable():
    """After redo() fails partway through, the successfully-redone prefix is
    rolled back to undone -- but CommandExecutor moves the composite to the
    undo stack regardless of redo()'s result (see CommandResult's docstring).
    A later undo() call must not re-undo sub-commands that were already
    rolled back to undone by this failed redo() -- that would double-undo
    them. The composite has no reliable way to know whether the never-
    reached remainder is safe to undo either, so the safest contract is to
    become inert: a further undo()/redo() on it is a no-op (see PR #333
    review)."""
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2", redo_result=CommandResult.FAILURE)

    composite = CompositeCommand([cmd1, cmd2])
    composite.execute()
    composite.undo()

    assert composite.redo() is CommandResult.FAILURE
    assert cmd1.redone_count == 1
    assert cmd1.undone_count == 2  # rolled back after cmd2's redo() failed

    cmd1.undone_count = 0
    cmd2.undone_count = 0

    assert composite.undo() is CommandResult.NOOP
    assert cmd1.undone_count == 0
    assert cmd2.undone_count == 0


def test_composite_command_redo_forward_order():
    call_order: List[str] = []

    class TrackedCommand(SimpleCommand):
        def redo(self) -> CommandResult:
            call_order.append(f"redo_{self.name}")
            return super().redo()

    cmd1 = TrackedCommand("c1")
    cmd2 = TrackedCommand("c2")

    composite = CompositeCommand([cmd1, cmd2])
    composite.execute()
    composite.undo()

    call_order.clear()
    assert composite.redo() is CommandResult.SUCCESS
    assert call_order == ["redo_c1", "redo_c2"]
    assert cmd1.redone_count == 1
    assert cmd2.redone_count == 1


def test_composite_command_redo_rollback_on_failure():
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2", redo_result=CommandResult.FAILURE)

    composite = CompositeCommand([cmd1, cmd2])
    composite.execute()
    composite.undo()

    # Reset undone counters to verify redo rollback
    cmd1.undone_count = 0
    cmd2.undone_count = 0

    assert composite.redo() is CommandResult.FAILURE
    assert cmd1.redone_count == 1
    assert cmd1.undone_count == 1  # Rolled back during redo
    assert cmd2.redone_count == 1


def test_composite_command_redo_excludes_noop_subcommands_from_replay_set():
    """A sub-command that returns NOOP from redo() made no change, so it
    must not be retained in the replay set: composite.undo() must not undo
    it afterwards, and it must not count toward marks_project_modified()
    (see PR #333 review)."""
    cmd_noop = SimpleCommand("noop", redo_result=CommandResult.NOOP, marks_modified=True)
    cmd_real = SimpleCommand("real", marks_modified=False)

    composite = CompositeCommand([cmd_noop, cmd_real])
    composite.execute()
    composite.undo()

    assert composite.redo() is CommandResult.SUCCESS  # cmd_real did redo
    assert composite.marks_project_modified() is False  # only cmd_real is in the replay set

    cmd_noop.undone_count = 0
    cmd_real.undone_count = 0
    composite.undo()
    assert cmd_noop.undone_count == 0
    assert cmd_real.undone_count == 1


def test_composite_command_redo_all_noop_reports_noop():
    cmd1 = SimpleCommand("c1", redo_result=CommandResult.NOOP)
    cmd2 = SimpleCommand("c2", redo_result=CommandResult.NOOP)

    composite = CompositeCommand([cmd1, cmd2])
    composite.execute()
    composite.undo()

    assert composite.redo() is CommandResult.NOOP


def test_composite_command_cleanup():
    cmd1 = SimpleCommand("c1")
    cmd2 = Mock(spec=Command)
    cmd2.cleanup.side_effect = RuntimeError("cleanup error")
    cmd3 = SimpleCommand("c3")

    composite = CompositeCommand([cmd1, cmd2, cmd3])
    composite.cleanup()

    assert cmd1.cleanup_count == 1
    cmd2.cleanup.assert_called_once()
    assert cmd3.cleanup_count == 1


def test_composite_command_marks_project_modified_is_a_method():
    """marks_project_modified is a method on Command, not a property."""
    c_false1 = SimpleCommand("f1", marks_modified=False)
    c_false2 = SimpleCommand("f2", marks_modified=False)
    c_true = SimpleCommand("t1", marks_modified=True)

    comp_all_false = CompositeCommand([c_false1, c_false2])
    comp_all_false.execute()
    assert comp_all_false.marks_project_modified() is False

    comp_mixed = CompositeCommand([c_false1, c_true])
    comp_mixed.execute()
    assert comp_mixed.marks_project_modified() is True


def test_composite_command_marks_project_modified_defaults_true_when_empty():
    assert CompositeCommand().marks_project_modified() is True


def test_composite_command_execute_noop_handling():
    cmd1 = SimpleCommand("c1", execute_result=CommandResult.NOOP)
    cmd2 = SimpleCommand("c2", execute_result=CommandResult.NOOP)

    composite = CompositeCommand([cmd1, cmd2])
    assert composite.execute() is CommandResult.NOOP


def test_composite_command_skips_undo_redo_for_noop_subcommands():
    """A sub-command that returned NOOP during execute() never had a real
    effect, so it must not be undone/redone -- doing so could invoke undo()
    on a command that never captured state to restore (see PR #325 review)."""
    cmd_noop = SimpleCommand("noop", execute_result=CommandResult.NOOP)
    cmd_real = SimpleCommand("real")

    composite = CompositeCommand([cmd_noop, cmd_real])
    assert composite.execute() is CommandResult.SUCCESS  # not all NOOP

    assert composite.undo() is CommandResult.SUCCESS
    assert cmd_noop.undone_count == 0
    assert cmd_real.undone_count == 1

    assert composite.redo() is CommandResult.SUCCESS
    assert cmd_noop.redone_count == 0
    assert cmd_real.redone_count == 1


def test_composite_command_marks_project_modified_ignores_noop_subcommands():
    cmd_noop = SimpleCommand("noop", execute_result=CommandResult.NOOP, marks_modified=True)
    cmd_real = SimpleCommand("real", marks_modified=False)

    composite = CompositeCommand([cmd_noop, cmd_real])
    composite.execute()

    assert composite.marks_project_modified() is False


def test_composite_command_occupies_undo_slot_defaults_true():
    assert CompositeCommand().occupies_undo_slot() is True


def test_command_executor_integration():
    executor = CommandExecutor()
    cmd1 = SimpleCommand("c1")
    cmd2 = SimpleCommand("c2")
    composite = CompositeCommand([cmd1, cmd2])

    # Execute
    assert executor.execute_command(composite) is True
    assert len(executor.undo_stack) == 1
    assert executor.undo_stack[0] is composite
    assert cmd1.executed_count == 1
    assert cmd2.executed_count == 1

    # Undo
    assert executor.undo() is True
    assert len(executor.undo_stack) == 0
    assert len(executor.redo_stack) == 1
    assert cmd1.undone_count == 1
    assert cmd2.undone_count == 1

    # Redo
    assert executor.redo() is True
    assert len(executor.undo_stack) == 1
    assert len(executor.redo_stack) == 0
    assert cmd1.redone_count == 1
    assert cmd2.redone_count == 1
