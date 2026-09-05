"""Tests for the shared unsaved-changes guard and its note-flush helper (#318)."""
from unittest.mock import Mock

from pandaplot.commands.project.project.unsaved_changes import flush_pending_note_edits
from pandaplot.models.state import AppContext


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
