# High #8 — Undo/Redo State Corruption on Exception

**Severity:** High  
**File:** `pandaplot/commands/command_executor.py`  
**Lines:** 65–84, 93–112

---

## Problem

Both `undo()` and `redo()` follow a peek-then-pop pattern:

```python
# command_executor.py:69-84
def undo(self) -> bool:
    if not self.undo_stack:
        return False

    command = self.undo_stack[-1]       # 1. Peek
    command_name = command.__class__.__name__
    ...
    try:
        command = self.undo_stack.pop() # 2. Pop (overwrites peek variable)
        command.undo()                  # 3. Execute undo
        self.redo_stack.append(command) # 4. Move to redo stack
        ...
        return True
    except Exception as e:
        self.logger.error(...)
        return False                    # 5. Return False — command is LOST
```

The same pattern exists in `redo()` (lines 97–112).

When `command.undo()` raises an exception:
- The command has already been **popped** from `undo_stack` (step 2).
- The command is NOT added to `redo_stack` (step 4 is skipped).
- The command object is referenced only by the local variable `command`, which goes out of scope when the function returns.
- **The command is silently dropped**: it cannot be undone again, and it cannot be redone.

The user's application state after the failed `undo()` is now:
- The model was partially mutated (some of `command.undo()` may have run before the exception).
- The undo/redo stacks no longer reflect reality.
- The user has no way to recover because neither undo nor redo contains the command.

### Secondary issue — confusing variable shadowing

The `command` variable is first assigned from the peek (`self.undo_stack[-1]`) and then immediately reassigned from the pop (`self.undo_stack.pop()`). This makes the code harder to reason about and the error message on line 82 references `command` after the pop, which may print an unexpected value.

---

## Impact

- **Data loss**: a failed undo leaves the application in a partially-reverted state with no recovery path.
- **Undo/redo stack desync**: subsequent undo/redo operations act on the wrong commands.
- **User confusion**: the undo menu item may remain enabled (because `undo_stack` is now shorter) but pressing it will undo a different command than expected.

---

## Fix

The key principle: **only remove a command from its source stack after the operation succeeds**. Use a try/except that restores the command to the stack on failure.

```python
def undo(self) -> bool:
    if not self.undo_stack:
        self.logger.debug("Undo requested but no commands in undo stack")
        return False

    command = self.undo_stack.pop()
    command_name = command.__class__.__name__
    self.logger.debug("Undoing command: %s", command_name)

    try:
        command.undo()
    except Exception as e:
        # Restore the command — state is unknown, but at least the stack is consistent
        self.undo_stack.append(command)
        self.logger.error(
            "Error undoing command '%s': %s — command restored to undo stack",
            command_name, str(e), exc_info=True
        )
        return False

    self.redo_stack.append(command)
    self.logger.info("Successfully undid command: %s", command_name)
    return True
```

Apply the same pattern to `redo()`:

```python
def redo(self) -> bool:
    if not self.redo_stack:
        return False

    command = self.redo_stack.pop()
    command_name = command.__class__.__name__

    try:
        command.redo()
    except Exception as e:
        self.redo_stack.append(command)
        self.logger.error(
            "Error redoing command '%s': %s — command restored to redo stack",
            command_name, str(e), exc_info=True
        )
        return False

    self.undo_stack.append(command)
    self.logger.info("Successfully redid command: %s", command_name)
    return True
```

**Why this is safe:** After `command.undo()` fails, the application state is uncertain — partial undo may have occurred. Restoring the command to the undo stack means the user can try again (or the developer can investigate). The alternative — dropping the command — is strictly worse because it makes recovery impossible.

---

## Optional Enhancement — Distinguish recoverable from fatal failures

Some undo failures are recoverable (e.g., a transient I/O error) and some are not (e.g., the undo method made changes that cannot be reversed). Consider adding a `UndoError` exception class that commands can raise to signal an irrecoverable state:

```python
class IrrecoverableUndoError(Exception):
    """Raised when an undo operation leaves the model in an unknown state."""
```

In `CommandExecutor.undo()`:

```python
except IrrecoverableUndoError:
    # Don't restore — state is corrupt; clear history to avoid further damage
    self.undo_stack.clear()
    self.redo_stack.clear()
    self.logger.critical("Irrecoverable undo failure — history cleared")
    return False
except Exception:
    # Recoverable — restore the command
    self.undo_stack.append(command)
    ...
```

---

## Notes

- The redundant peek at `undo_stack[-1]` before the pop (lines 69 vs 74) was likely introduced to capture `command_name` before the pop. This can be simplified: pop first, capture the name, then proceed.
- `execute_command()` (lines 34–56) does NOT have this problem: if `command.execute()` raises, the command is never added to the stack. The undo/redo methods need the same discipline.
- Add tests that exercise commands whose `undo()` method raises and assert that the undo stack is unchanged after the failure.
