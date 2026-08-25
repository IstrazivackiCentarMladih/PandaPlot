"""Tests for AppState's project lifecycle and unsaved-changes (is_modified)
tracking (#209)."""
from pandaplot.models.events import EventBus
from pandaplot.models.events.event_types import ProjectEvents
from pandaplot.models.project.project import Project
from pandaplot.models.state.app_state import AppState


def _make_state():
    return AppState(EventBus())


def test_is_modified_starts_false():
    state = _make_state()
    assert state.is_modified is False


def test_mark_modified_requires_a_loaded_project():
    state = _make_state()
    state.mark_modified()
    assert state.is_modified is False


def test_mark_modified_sets_the_flag_and_emits_once():
    state = _make_state()
    state.load_project(Project(name="P"))

    events = []
    state.event_bus.subscribe(ProjectEvents.PROJECT_MODIFIED_CHANGED, lambda data: events.append(data))

    state.mark_modified()
    state.mark_modified()  # second call is a no-op, must not re-emit

    assert state.is_modified is True
    assert len(events) == 1
    assert events[0]["is_modified"] is True


def test_mark_saved_clears_the_flag_and_emits_once():
    state = _make_state()
    state.load_project(Project(name="P"))
    state.mark_modified()

    events = []
    state.event_bus.subscribe(ProjectEvents.PROJECT_MODIFIED_CHANGED, lambda data: events.append(data))

    state.mark_saved()
    state.mark_saved()  # second call is a no-op, must not re-emit

    assert state.is_modified is False
    assert len(events) == 1
    assert events[0]["is_modified"] is False


def test_load_project_resets_is_modified():
    state = _make_state()
    state.load_project(Project(name="P"))
    state.mark_modified()
    assert state.is_modified is True

    state.load_project(Project(name="Q"))

    assert state.is_modified is False


def test_close_project_resets_is_modified():
    state = _make_state()
    state.load_project(Project(name="P"))
    state.mark_modified()

    state.close_project()

    assert state.is_modified is False
