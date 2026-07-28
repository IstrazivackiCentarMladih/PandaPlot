import logging
import os
import sys

from PySide6.QtWidgets import QApplication

from pandaplot.commands.command_executor import CommandExecutor
from pandaplot.commands.project.project import LoadProjectCommand
from pandaplot.gui.controllers import UIController
from pandaplot.gui.main_window import PandaMainWindow
from pandaplot.models.events import EventBus
from pandaplot.models.project.items import Chart, Dataset, Folder, Note
from pandaplot.models.state import AppContext, AppState
from pandaplot.services.config import ConfigManager
from pandaplot.services.qtasks import TaskScheduler
from pandaplot.services.session import SessionPersistenceManager
from pandaplot.services.theme import ThemeManager
from pandaplot.storage.chart_data_manager import ChartDataManager
from pandaplot.storage.dataset_data_manager import DatasetDataManager
from pandaplot.storage.folder_data_manager import FolderDataManager
from pandaplot.storage.item_data_manager_factory import ItemDataManagerFactory
from pandaplot.storage.note_data_manager import NoteDataManager
from pandaplot.storage.project_data_manager import ProjectDataManager
from pandaplot.utils.log import setup_logging


def create_project_data_manager() -> ProjectDataManager:
    """Register item data managers and build the project data manager."""
    factory = ItemDataManagerFactory()
    # TODO: verify extension usage
    factory.register("note", Note, NoteDataManager(), "note")
    factory.register("folder", Folder, FolderDataManager(), "folder")
    factory.register("chart", Chart, ChartDataManager(), "chart")
    factory.register("dataset", Dataset, DatasetDataManager(), "dataset")
    return ProjectDataManager(factory)


def build_app_context() -> AppContext:
    """Create and return a fully initialized AppContext (no Qt widgets yet)."""
    event_bus = EventBus()
    project_data_manager = create_project_data_manager()
    app_state = AppState(event_bus)
    config_manager = ConfigManager(event_bus)
    config_manager.load()
    theme_manager = ThemeManager(event_bus, config_manager)
    session_manager = SessionPersistenceManager(config_manager)
    ui_controller = UIController()
    command_executor = CommandExecutor()
    task_scheduler = TaskScheduler()

    # Create list of managers to pass to AppContext
    managers = [command_executor, ui_controller, config_manager, theme_manager, session_manager, task_scheduler, project_data_manager]

    return AppContext(app_state=app_state, event_bus=event_bus, managers=managers)


def create_qt_application(app_context: AppContext, argv: list[str] | None = None) -> tuple[QApplication, PandaMainWindow]:
    """Instantiate QApplication and the main window.

    Returns (app, main_window)
    """
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)

    # Kick off the background import warm-up right after QApplication exists
    # (QObject-based signals -- which the worker uses to report completion --
    # are not safe to use before an application instance exists) and before
    # building the window, so it overlaps with theme application and widget
    # construction instead of waiting for all of that to finish first.
    _schedule_import_warmup(app_context)

    # Apply the theme (QApplication-wide palette/stylesheet/font) before any
    # widgets exist. Setting these on a QApplication forces Qt to re-polish
    # every already-constructed widget -- doing it first means new widgets
    # simply inherit the theme instead of paying that repolish cost after
    # the whole window (menu/sidebar/panels/tabs) has already been built.
    theme_mgr = app_context.get_manager(ThemeManager)
    theme_mgr.set_qt_app(app)
    try:
        theme_mgr.apply_current()
    except Exception:
        logging.getLogger(__name__).exception("Failed applying initial theme")

    main_window = PandaMainWindow(app_context)
    app_context.ui_controller.set_parent_widget(main_window)
    return app, main_window


def _warm_up_heavy_imports(progress_callback=None) -> None:
    """Pre-import dependencies that are otherwise lazily loaded on first use
    (running a fit, opening a chart tab, opening a note tab). Each of those
    imports costs 1+ seconds; without warm-up, that cost is paid synchronously
    on the UI thread the first time the user triggers the feature, which
    looks like a freeze. Runs on a background thread, so import errors here
    must never propagate to the caller -- the feature will just import (and
    freeze, or fail) normally on first real use instead.
    """
    try:
        from markdown import markdown  # noqa: F401
        from matplotlib.backends.backend_qt import NavigationToolbar2QT  # noqa: F401
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: F401
        from matplotlib.figure import Figure  # noqa: F401
        from scipy.optimize import curve_fit  # noqa: F401
    except Exception:
        logging.getLogger(__name__).exception("Background import warm-up failed (non-fatal)")


def _schedule_import_warmup(app_context: AppContext) -> None:
    """Kick off _warm_up_heavy_imports on a background thread."""
    task_scheduler = app_context.get_manager(TaskScheduler)
    task_scheduler.run_task(_warm_up_heavy_imports)


def restore_last_session(app_context: AppContext, main_window: PandaMainWindow) -> None:
    """Reopen the project (and tabs) that were open at the end of the previous session.

    No-op if no project was remembered, or the remembered file no longer exists.
    """
    session_manager = app_context.get_manager(SessionPersistenceManager)
    last_path = session_manager.last_project_path
    if not last_path or not os.path.isfile(last_path):
        return

    panes_data = session_manager.last_tab_panes
    active_tab_id = session_manager.last_active_tab_id
    splitter_sizes = session_manager.last_splitter_sizes

    def _on_loaded(project) -> None:  # noqa: ANN001 - Project, avoiding import cycle concerns
        main_window.tab_container.restore_tab_session(panes_data, active_tab_id, splitter_sizes)

    command = LoadProjectCommand(app_context, last_path, on_loaded=_on_loaded)
    app_context.get_command_executor().execute_command(command)


def launch(app_context: AppContext) -> int:
    """Launch the GUI event loop.

    Returns the Qt application's exit code.
    """
    if app_context is None:
        raise RuntimeError("AppContext must be provided to launch the application")

    app, main_window = create_qt_application(app_context)
    main_window.show()
    restore_last_session(app_context, main_window)

    # If the app quits while the background import warm-up task is still
    # running, interpreter teardown can race the worker thread's signal
    # emission ("RuntimeError: Signal source has been deleted", printed by
    # Qt but non-fatal). Give it a bounded window to finish before the app
    # actually exits -- a no-op once warm-up has already completed, which is
    # true for the vast majority of real sessions. This is a mitigation, not
    # a guarantee: on a slow/cold-cache import, waitForDone(2000) can still
    # time out and shutdown proceeds regardless, leaving the same race (and
    # its harmless stderr noise) possible -- just less likely.
    task_scheduler = app_context.get_manager(TaskScheduler)
    app.aboutToQuit.connect(lambda: task_scheduler.threadpool.waitForDone(2000))

    return app.exec()


def main() -> None:
    """CLI entry point for `python -m pandaplot.app`."""
    debug = os.environ.get("PANDAPLOT_DEBUG", "").lower() in ("1", "true", "yes")
    logger = setup_logging(level=logging.DEBUG if debug else logging.INFO)
    logger.info("--------------Starting PandaPlot application--------------")
    app_context = build_app_context()
    sys.exit(launch(app_context))


if __name__ == "__main__":
    main()
    # TODO: fix add (load damped pendulum project, try to add series to energy graph)
    # TODO: fix remove series
    # TODO: log error messages to the user
    # TODO: fix how we treat transformed columns, they aren't saved correctly
    # TODO: consider creating project creation dialog
    # TODO: improve view of project name
    # TODO: when opening a project which is already open, we should just switch to it instead of reloading it
    # TODO: create process for multi-threaded operations
    # TODO: use mm instead of cm or make it configurable
    # TODO: improve initial loading of the app
    # TODO: clean state on opening new project or add support for multiple projects
    # TODO: list and implement copy paste capabilities we want to support
    # TODO: improve how we handle styles and themes
    # TODO: ask whether open project needs to be saved before closing - either a new project or open documents that have been modified. We can track modifications somewhere if needed.
    # TODO: save on an existing project is acting as save as, we need to fix this behavior.
    # TODO: enable chart creation without opening a dataset
    # TODO: remove dialog on project open success
    # TODO: improve project info display in sidebar
    # TODO: fix saved state tracking - when opening a project it should say it's saved until modified
    # TODO: disable chart properties and curve fitting sidepanels on dataset view
    # TODO: close open tabs related to a project when closing project
    # TODO: in chart properties panel, fix tab display, ensure buttons are visible
    # TODO: fix how we use font size across the app.
    # TODO: fix dark theme colors
    # TODO: make chart area scrollable
    # TODO: in dataset tab we show all of the data lazily, but we should load it lazily also from the disk if it's too big
    # TODO: add support for sorting and filtering of the data
    # TODO: add export options for dataset tab
    # TODO: add support for formulas in dataset tab
    # TODO: encapsulate project data manager inside project manager
