"""Tests for the shared unsaved-changes guard and its note-flush helper (#318)."""
from unittest.mock import Mock

from pandaplot.commands.project.project.unsaved_changes import (
    confirm_discard_unsaved_changes,
    flush_pending_note_edits,
)
from pandaplot.models.state import AppContext, AppState


def _tab(*, unsaved: bool) -> Mock:
    tab = Mock()
    tab.has_unsaved_changes.return_value = unsaved
    return tab


def test_flush_pending_note_edits_saves_only_dirty_tabs():
    app_context = Mock(spec=AppContext)
    tab_container = Mock()
    dirty_tab = _tab(unsaved=True)
    clean_tab = _tab(unsaved=False)
    tab_container.tabs = {"n1": dirty_tab, "n2": clean_tab}
    app_context.get_manager.return_value = tab_container

    flush_pending_note_edits(app_context)

    dirty_tab.save.assert_called_once()
    clean_tab.save.assert_not_called()


def test_flush_pending_note_edits_ignores_tabs_without_the_protocol():
    """A dataset/chart tab (no has_unsaved_changes/save) must be skipped,
    not raise."""
    app_context = Mock(spec=AppContext)
    tab_container = Mock()
    other_tab = Mock(spec=[])
    tab_container.tabs = {"c1": other_tab}
    app_context.get_manager.return_value = tab_container

    flush_pending_note_edits(app_context)  # must not raise


def test_flush_pending_note_edits_swallows_tab_container_lookup_failure():
    app_context = Mock(spec=AppContext)
    app_context.get_manager.side_effect = RuntimeError("no manager registered")

    flush_pending_note_edits(app_context)  # must not raise


def test_flush_pending_note_edits_swallows_one_tabs_save_failure():
    """One tab's save() blowing up must not stop other dirty tabs from
    still being flushed, nor propagate to the caller (a lifecycle guard)."""
    app_context = Mock(spec=AppContext)
    tab_container = Mock()
    failing_tab = _tab(unsaved=True)
    failing_tab.save.side_effect = RuntimeError("boom")
    other_dirty_tab = _tab(unsaved=True)
    tab_container.tabs = {"n1": failing_tab, "n2": other_dirty_tab}
    app_context.get_manager.return_value = tab_container

    flush_pending_note_edits(app_context)

    other_dirty_tab.save.assert_called_once()


def _make_app_context(*, has_project=True, is_modified=False):
    app_context = Mock(spec=AppContext)
    app_state = Mock(spec=AppState)
    app_state.has_project = has_project
    app_state.is_modified = is_modified
    app_state.is_saving = False
    app_state.current_project.name = "P"
    app_state.project_file_path = None
    app_context.get_app_state.return_value = app_state
    return app_context, app_state


def test_confirm_discard_flushes_pending_note_edits_before_checking_is_modified(monkeypatch):
    """Regression (#318): a note's debounced edit must land (flipping
    is_modified to True) before this function decides whether there is
    anything to confirm -- otherwise a fast close/exit racing the note's
    2s auto-save timer silently proceeds with no prompt at all."""
    app_context, app_state = _make_app_context(is_modified=False)
    calls = []

    def fake_flush(ctx):
        calls.append(ctx)
        app_state.is_modified = True  # simulates the debounced EditNoteCommand landing

    monkeypatch.setattr(
        "pandaplot.commands.project.project.unsaved_changes.flush_pending_note_edits",
        fake_flush,
    )
    app_context.get_ui_controller.return_value.show_question.return_value = True

    result = confirm_discard_unsaved_changes(app_context)

    assert calls == [app_context]
    assert result is True
    app_context.get_ui_controller.return_value.show_question.assert_called_once()


def test_confirm_discard_still_returns_true_without_asking_when_flush_finds_nothing(monkeypatch):
    """A flush that changes nothing must not turn an already-clean project
    into a spurious confirmation prompt."""
    app_context, _app_state = _make_app_context(is_modified=False)
    calls = []
    monkeypatch.setattr(
        "pandaplot.commands.project.project.unsaved_changes.flush_pending_note_edits",
        lambda ctx: calls.append(ctx),
    )

    result = confirm_discard_unsaved_changes(app_context)

    assert calls == [app_context]
    assert result is True
    app_context.get_ui_controller.return_value.show_question.assert_not_called()
