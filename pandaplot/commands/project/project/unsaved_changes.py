"""Shared "may we discard unsaved changes?" guard.

Every path that can end with the current project going away -- explicit
Project > Close, File > Exit, the OS window-close button/Cmd+Q, opening a
different project -- needs the same check so none of them can silently
discard edits. This is the single implementation; callers that need it
(CloseProjectCommand, ExitCommand, PandaMainWindow.closeEvent) all go
through it rather than each re-implementing the confirmation dialog.
"""
from pandaplot.models.state.app_context import AppContext


def confirm_discard_unsaved_changes(app_context: AppContext) -> bool:
    """Return True if it's fine to proceed (no project loaded, or no
    unsaved changes, or the user confirmed discarding them); False if the
    caller should cancel whatever it was about to do."""
    app_state = app_context.get_app_state()
    if not app_state.has_project or not app_state.is_modified:
        return True

    project_name = app_state.current_project.name if app_state.current_project else "Unknown"
    ui_controller = app_context.get_ui_controller()
    return ui_controller.show_question(
        "Unsaved Changes",
        f"Project '{project_name}' has unsaved changes.\n"
        "Continuing now will discard them.\n\nDo you want to continue?",
    )
