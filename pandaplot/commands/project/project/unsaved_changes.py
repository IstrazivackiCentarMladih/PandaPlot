"""Shared "may we discard unsaved changes?" guard.

Every path that can end with the current project going away -- explicit
Project > Close, File > Exit, the OS window-close button/Cmd+Q, opening a
different project -- needs the same check so none of them can silently
discard edits. This is the single implementation; callers that need it
(CloseProjectCommand, ExitCommand, PandaMainWindow.closeEvent) all go
through it rather than each re-implementing the confirmation dialog.
"""
from pandaplot.models.state.app_context import AppContext
from pandaplot.services.data_managers.project_manager import ProjectManager


def flush_pending_note_edits(app_context: AppContext) -> bool:
    """Commit any open note tab's debounced, not-yet-saved edit into the
    project model before a lifecycle guard reads/acts on AppState.is_modified.

    NoteEditorWidget.on_content_changed() debounces its EditNoteCommand
    behind a 2-second single-shot timer -- AppState.mark_modified() only
    fires once that timer's auto_save() actually runs the command, not on
    every keystroke (see note_editor.py). A lifecycle transition (Close/New/
    Open/Exit) that races that window would otherwise see is_modified still
    False and silently proceed past a note edit that exists only in the
    tab's QTextEdit, never written to the Note/Project model.

    Returns whether every dirty tab was actually committed. A tab whose
    save() fails (returns False or raises) is left dirty -- reported as a
    failure rather than swallowed, since silently treating it as flushed
    would recreate exactly the silent-data-loss bug this exists to close:
    the caller would read an unchanged is_modified and proceed anyway. A
    missing/unavailable TabContainer (e.g. no GUI yet) is not itself a
    failure -- there's nothing open to lose in that case.
    """
    from pandaplot.gui.components.tabs.tab_container import TabContainer

    try:
        tabs = list(app_context.get_manager(TabContainer).tabs.values())
    except Exception:
        return True

    all_flushed = True
    for tab in tabs:
        has_unsaved_changes = getattr(tab, "has_unsaved_changes", None)
        save = getattr(tab, "save", None)
        if not callable(has_unsaved_changes) or not callable(save):
            continue
        try:
            if has_unsaved_changes() and not save():
                all_flushed = False
        except Exception:
            all_flushed = False
    return all_flushed


def confirm_discard_unsaved_changes(app_context: AppContext, *, will_autosave: bool = False) -> bool:
    """Return True if it's fine to proceed (no project loaded, or no
    unsaved changes, the user confirmed proceeding and (for an autosaving
    caller) the save actually succeeded); False if the caller should
    cancel whatever it was about to do.

    `will_autosave` must be True for a caller whose proceeding is followed
    by `app.launch()`'s unconditional `_flush_save_on_quit` (currently
    ExitCommand and PandaMainWindow.closeEvent, the two paths that end the
    process) -- those never actually discard an *already-saved-once*
    project's edits, so the prompt must not claim they will.
    CloseProjectCommand (the default, project-only close) genuinely
    discards, so it keeps the "will be discarded" wording, as does exiting
    a never-saved project (`_flush_save_on_quit` has no file path to write
    to, so it really is discarded).

    For the autosaving case, this performs that save synchronously, right
    here, once the user confirms -- rather than just trusting
    `_flush_save_on_quit` to make good on the promise later. That deferred
    save runs after the point of no return (mid-`aboutToQuit`) and swallows
    every exception into a log line, so a disk-full/permission/serialization
    failure would otherwise silently exit the app having lost the edits it
    just promised to keep. Doing it here means a failure can still cancel
    the shutdown and leave the project (and its unsaved state) intact.
    """
    if not flush_pending_note_edits(app_context):
        app_context.get_ui_controller().show_error_message(
            "Unsaved Changes",
            "One or more open notes could not be saved. Save them manually before continuing.",
        )
        return False

    app_state = app_context.get_app_state()
    if not app_state.has_project or not app_state.is_modified:
        return True

    project_name = app_state.current_project.name if app_state.current_project else "Unknown"
    ui_controller = app_context.get_ui_controller()
    file_path = app_state.project_file_path
    autosaving = will_autosave and bool(file_path)
    consequence = (
        "They will be saved automatically before exiting."
        if autosaving
        else "Continuing now will discard them."
    )
    proceed = ui_controller.show_question(
        "Unsaved Changes",
        f"Project '{project_name}' has unsaved changes.\n"
        f"{consequence}\n\nDo you want to continue?",
    )
    if not proceed or not autosaving:
        return proceed

    if app_state.is_saving:
        # A SaveProjectCommand (manual or auto-save) is already writing
        # this project's file. ProjectDataManager.save() opens the target
        # in write mode, so writing over it concurrently here could
        # corrupt it. Rather than block the UI waiting for it to finish,
        # just refuse to proceed -- the in-flight save will itself clear
        # is_modified on success, and the user can exit again once it's
        # done (a narrow, easily-retried window, not a silent failure).
        ui_controller.show_info_message(
            "Save In Progress",
            f"A save of project '{project_name}' is already in progress.\n"
            "Please wait for it to finish, then try again.",
        )
        return False

    try:
        project_manager = app_context.get_manager(ProjectManager)
        project_manager.save_project(app_state.current_project, file_path)
    except Exception as e:
        ui_controller.show_error_message(
            "Save Failed",
            f"Project '{project_name}' could not be saved:\n{e}\n\n"
            "The application will stay open so these changes aren't lost.",
        )
        return False

    app_state.mark_saved()
    return True
