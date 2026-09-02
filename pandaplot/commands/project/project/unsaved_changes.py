"""Shared "may we discard unsaved changes?" guard.

Every path that can end with the current project going away -- explicit
Project > Close, File > Exit, the OS window-close button/Cmd+Q, opening a
different project -- needs the same check so none of them can silently
discard edits. This is the single implementation; callers that need it
(CloseProjectCommand, ExitCommand, PandaMainWindow.closeEvent) all go
through it rather than each re-implementing the confirmation dialog.
"""
from pandaplot.models.state.app_context import AppContext


def confirm_discard_unsaved_changes(app_context: AppContext, *, will_autosave: bool = False) -> bool:
    """Return True if it's fine to proceed (no project loaded, or no
    unsaved changes, or the user confirmed proceeding); False if the
    caller should cancel whatever it was about to do.

    `will_autosave` must be True for a caller whose proceeding is followed
    by `app.launch()`'s unconditional `_flush_save_on_quit` (currently
    ExitCommand and PandaMainWindow.closeEvent, the two paths that end the
    process) -- those never actually discard an *already-saved-once*
    project's edits, so the prompt must not claim they will.
    CloseProjectCommand (the default, project-only close) genuinely
    discards, so it keeps the "will be discarded" wording, as does exiting
    a never-saved project (`_flush_save_on_quit` has no file path to write
    to, so it really is discarded).
    """
    app_state = app_context.get_app_state()
    if not app_state.has_project or not app_state.is_modified:
        return True

    project_name = app_state.current_project.name if app_state.current_project else "Unknown"
    ui_controller = app_context.get_ui_controller()
    consequence = (
        "They will be saved automatically before exiting."
        if will_autosave and app_state.project_file_path
        else "Continuing now will discard them."
    )
    return ui_controller.show_question(
        "Unsaved Changes",
        f"Project '{project_name}' has unsaved changes.\n"
        f"{consequence}\n\nDo you want to continue?",
    )
