"""Tests for SignalAnalysisCommand: preview (run_analysis_async) and
commit (execute -> ApplySignalAnalysisResultCommand) paths."""

import logging
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from pandaplot.analysis import SignalAnalysisType
from pandaplot.commands.base_command import CommandResult
from pandaplot.commands.command_executor import CommandExecutor
from pandaplot.commands.project.dataset.apply_signal_analysis_result_command import (
    ApplySignalAnalysisResultCommand,
)
from pandaplot.commands.project.dataset.signal_analysis_command import SignalAnalysisCommand
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project
from pandaplot.models.state import AppContext, AppState

from tests.commands.project.conftest import SyncTaskScheduler


@pytest.fixture
def app_context_with_project():
    fs = 1000
    t = np.linspace(0, 1, fs, endpoint=False)
    signal = np.sin(2 * np.pi * 50 * t)

    project = Project(name="P")
    dataset = Dataset(id="ds-1", name="Signal Data", data=pd.DataFrame({"signal": signal}))
    project.add_item(dataset)

    app_context = Mock(spec=AppContext)
    app_state = Mock(spec=AppState)
    app_state.has_project = True
    app_state.current_project = project
    app_state.event_bus = Mock()

    app_context.get_app_state.return_value = app_state
    app_context.get_task_scheduler.return_value = SyncTaskScheduler()
    app_context.get_command_executor.return_value = CommandExecutor()

    return app_context, project


class TestSignalAnalysisCommandCommitPath:
    def test_execute_adds_fft_results_dataset(self, app_context_with_project):
        app_context, project = app_context_with_project
        command = SignalAnalysisCommand(
            app_context, "ds-1", SignalAnalysisType.FFT, "signal", sampling_rate=1000,
        )
        assert command.execute() is CommandResult.SUCCESS

        results = project.find_item(command.result_dataset_id)
        assert results is not None
        assert "Frequency (Hz)" in results.data.columns
        assert "Amplitude" in results.data.columns

    def test_occupies_no_undo_slot(self, app_context_with_project):
        app_context, _ = app_context_with_project
        command = SignalAnalysisCommand(app_context, "ds-1", SignalAnalysisType.PEAKS, "signal")
        assert command.occupies_undo_slot() is False

    def test_undo_via_executor_removes_results_dataset(self, app_context_with_project):
        app_context, project = app_context_with_project
        executor: CommandExecutor = app_context.get_command_executor()
        command = SignalAnalysisCommand(app_context, "ds-1", SignalAnalysisType.PEAKS, "signal")

        assert executor.execute_command(command) is True
        assert isinstance(executor.undo_stack[-1], ApplySignalAnalysisResultCommand)

        new_id = command.result_dataset_id
        assert project.find_item(new_id) is not None

        assert executor.undo() is True
        assert project.find_item(new_id) is None

    def test_missing_column_fails_gracefully(self, app_context_with_project):
        app_context, _ = app_context_with_project
        command = SignalAnalysisCommand(
            app_context, "ds-1", SignalAnalysisType.FFT, "missing", sampling_rate=1000,
        )
        assert command.execute() is CommandResult.FAILURE
        assert command.result_dataset_id is None
        app_context.get_ui_controller.return_value.show_error_message.assert_called_once()

    def test_execute_surfaces_no_project_loaded_to_the_user(self):
        app_context = Mock(spec=AppContext)
        app_state = Mock(spec=AppState)
        app_state.has_project = False
        app_state.current_project = None
        app_context.get_app_state.return_value = app_state
        app_context.get_task_scheduler.return_value = SyncTaskScheduler()

        command = SignalAnalysisCommand(
            app_context, "ds-1", SignalAnalysisType.FFT, "signal", sampling_rate=1000,
        )
        assert command.execute() is CommandResult.FAILURE
        app_context.get_ui_controller.return_value.show_error_message.assert_called_once()

    def test_execute_fails_fast_when_already_running(self, app_context_with_project, caplog):
        app_context, _ = app_context_with_project
        command = SignalAnalysisCommand(app_context, "ds-1", SignalAnalysisType.FFT, "signal", sampling_rate=1000)
        command._is_running = True

        with caplog.at_level(logging.WARNING):
            assert command.execute() is CommandResult.FAILURE
        assert "already in progress" in caplog.text

    def test_on_complete_reports_success(self, app_context_with_project):
        app_context, _ = app_context_with_project
        outcomes = []
        command = SignalAnalysisCommand(
            app_context, "ds-1", SignalAnalysisType.FFT, "signal", sampling_rate=1000,
            on_complete=outcomes.append,
        )
        assert command.execute() is CommandResult.SUCCESS
        assert outcomes == [CommandResult.SUCCESS]

    def test_cleanup_releases_the_result_dataset_id_and_result(self, app_context_with_project):
        app_context, _ = app_context_with_project
        command = SignalAnalysisCommand(app_context, "ds-1", SignalAnalysisType.FFT, "signal", sampling_rate=1000)
        assert command.execute() is CommandResult.SUCCESS
        assert command.result_dataset_id is not None
        assert command.result is not None

        command.cleanup()

        assert command.result_dataset_id is None
        assert command.result is None


class TestSignalAnalysisCommandPreviewPath:
    def test_run_analysis_async_reports_result(self, app_context_with_project):
        app_context, _ = app_context_with_project
        command = SignalAnalysisCommand(app_context, "ds-1", SignalAnalysisType.FFT, "signal", sampling_rate=1000)

        results = []
        errors = []
        command.run_analysis_async(lambda result, error: (results.append(result), errors.append(error)))

        assert errors == [None]
        assert results[0] is not None
        assert "Frequency (Hz)" in results[0].data.columns

    def test_run_analysis_async_reports_missing_column(self, app_context_with_project):
        app_context, _ = app_context_with_project
        command = SignalAnalysisCommand(app_context, "ds-1", SignalAnalysisType.FFT, "missing", sampling_rate=1000)

        results = []
        errors = []
        command.run_analysis_async(lambda result, error: (results.append(result), errors.append(error)))

        assert results == [None]
        assert "missing" in errors[0]

    def test_run_analysis_async_does_not_touch_the_project(self, app_context_with_project):
        app_context, project = app_context_with_project
        before = len(project.get_all_items())

        command = SignalAnalysisCommand(app_context, "ds-1", SignalAnalysisType.FFT, "signal", sampling_rate=1000)
        command.run_analysis_async(lambda result, error: None)

        assert len(project.get_all_items()) == before
