from unittest.mock import Mock

from pandaplot.gui.components.tabs.note.note_tab import NoteTab


def test_get_tab_data_returns_note_type_and_id():
    tab = NoteTab.__new__(NoteTab)
    tab.note = Mock(id="note-1")

    assert tab.get_tab_data() == {"type": "note", "id": "note-1"}


def test_on_note_renamed_event_refreshes_title_for_matching_note():
    tab = NoteTab.__new__(NoteTab)
    tab.note = Mock(id="note-1")
    tab.refresh_tab_title = Mock()

    tab.on_note_renamed_event({"item_id": "note-1", "new_name": "Renamed"})

    tab.refresh_tab_title.assert_called_once()


def test_on_note_renamed_event_ignores_other_items():
    tab = NoteTab.__new__(NoteTab)
    tab.note = Mock(id="note-1")
    tab.refresh_tab_title = Mock()

    tab.on_note_renamed_event({"item_id": "other-id", "new_name": "Renamed"})

    tab.refresh_tab_title.assert_not_called()


def test_has_unsaved_changes_delegates_to_note_editor():
    tab = NoteTab.__new__(NoteTab)
    tab.note_editor = Mock()

    tab.note_editor.has_unsaved_changes.return_value = True
    assert tab.has_unsaved_changes() is True

    tab.note_editor.has_unsaved_changes.return_value = False
    assert tab.has_unsaved_changes() is False
