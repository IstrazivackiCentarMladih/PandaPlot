import os
import subprocess
import sys


def test_background_import_warmup_loads_heavy_deps_off_the_main_thread():
    """scipy/matplotlib/markdown are lazily imported on first real use (a fit,
    a chart tab, a note tab). Without warm-up, that first use blocks the UI
    thread for multiple seconds. After the window is shown, a background
    task should pre-import them so first use finds them already cached."""
    code = (
        "import sys\n"
        "from PySide6.QtWidgets import QApplication\n"
        "app = QApplication(sys.argv)\n"
        "from pandaplot.app import build_app_context, _schedule_import_warmup\n"
        "from pandaplot.services.qtasks import TaskScheduler\n"
        "app_context = build_app_context()\n"
        "task_scheduler = app_context.get_manager(TaskScheduler)\n"
        "_schedule_import_warmup(app_context)\n"
        "task_scheduler.threadpool.waitForDone()\n"
        "assert 'scipy.optimize' in sys.modules, 'scipy.optimize was not warmed up'\n"
        "assert 'matplotlib.backends.backend_qtagg' in sys.modules, 'matplotlib backend was not warmed up'\n"
        "assert 'markdown' in sys.modules, 'markdown was not warmed up'\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=os.environ.copy())
    assert result.returncode == 0, result.stderr


def test_warm_up_heavy_imports_does_not_raise_progress_callback_signature():
    """Worker always injects progress_callback as a kwarg (see Worker.__init__);
    the warm-up function must accept it even though it doesn't use it."""
    from pandaplot.app import _warm_up_heavy_imports

    _warm_up_heavy_imports(progress_callback=lambda pct: None)
