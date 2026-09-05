"""Tests for NoteEditorWidget.save_content()'s success/failure contract
(PR #352 review): a caller (NoteTab.save(), flush_pending_note_edits) must be
able to tell a save that actually committed apart from one that ran but was
rejected, or the note's dirty state gets silently forgotten."""
from unittest.mock import Mock

from pandaplot.gui.components.tabs.note.note_editor import NoteEditorWidget


def _widget(*, execute_command_result):
    widget = NoteEditorWidget.__new__(NoteEditorWidget)
    widget.text_edit = Mock()
    widget.text_edit.toPlainText.return_value = "new content"
    widget.app_context = Mock()
    widget.note = Mock(id="note-1")
    widget.update_status = Mock()
    widget.is_modified = True
    executor = widget.app_context.get_command_executor.return_value
    if isinstance(execute_command_result, Exception):
        executor.execute_command.side_effect = execute_command_result
    else:
        executor.execute_command.return_value = execute_command_result
    return widget


def test_save_content_returns_true_and_clears_modified_on_success():
    widget = _widget(execute_command_result=True)

    assert widget.save_content() is True
    assert widget.is_modified is False


def test_save_content_returns_false_and_keeps_modified_when_command_fails():
    """execute_command() returning False (EditNoteCommand rejected -- no
    project, note not found, etc.) must not be reported as a successful
    save, and must not clear is_modified -- the edit is still only in the
    QTextEdit, not committed to the Note model."""
    widget = _widget(execute_command_result=False)

    assert widget.save_content() is False
    assert widget.is_modified is True


def test_save_content_returns_false_and_keeps_modified_on_exception():
    widget = _widget(execute_command_result=RuntimeError("boom"))

    assert widget.save_content() is False
    assert widget.is_modified is True
