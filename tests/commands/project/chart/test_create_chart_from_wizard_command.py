"""Tests for CreateChartFromWizardCommand.

The wizard is opened non-blocking (`show()` + `finished` signal), so
`execute()` only opens it; the chart is built later in `_on_wizard_finished`.
These unit tests therefore drive that slot directly instead of relying on a
return value from `dialog.exec()`.
"""
import gc
from types import MethodType
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QDialog

from pandaplot.commands.project.chart import CreateChartFromWizardCommand
from pandaplot.models.project.items import Dataset


@pytest.fixture
def app_context_with_project():
    dataset = Mock(spec=Dataset)
    dataset.id = "ds-1"
    dataset.name = "ds"
    dataset.parent_id = None
    dataset.data = None

    project = Mock()
    project.find_item.return_value = dataset
    project.get_all_items.return_value = [dataset]

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    app_context.event_bus = Mock()
    return app_context, project


def _fake_wizard(chart_type="line", is_empty=False, series_configs=None):
    """A stand-in for `ChartWizard` with a mockable `finished` signal."""
    wizard = Mock()
    wizard.finished = Mock()
    wizard.get_chart_type.return_value = chart_type
    wizard.is_empty.return_value = is_empty
    wizard.get_series_configs.return_value = series_configs or []
    return wizard


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_execute_shows_the_wizard_without_blocking(mock_wizard_cls, app_context_with_project):
    """`execute()` must `show()` the wizard, never `exec()` it.

    A blocking `exec()` loop is what made the pick-from-dataset modality
    handoff impossible (the wizard can't be hidden/re-shown without killing
    the loop), so this is a regression guard on the core fix.
    """
    app_context, _ = app_context_with_project
    wizard = _fake_wizard()
    mock_wizard_cls.return_value = wizard

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    wizard.show.assert_called_once_with()
    wizard.exec.assert_not_called()
    wizard.finished.connect.assert_called_once()
    # `exec()` made the wizard application-modal implicitly; `show()` does not,
    # so the command must ask for it explicitly.
    wizard.setModal.assert_called_once_with(True)


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_finished_is_connected_to_a_closure_not_a_bound_method(mock_wizard_cls, app_context_with_project):
    """The connection must keep the command alive while the wizard is open.

    PySide gives bound-method connections weak-reference-like treatment for the
    receiver, so `connect(self._on_wizard_finished)` does *not* keep the command
    alive. Nothing else holds a lasting reference to it either -- the
    CommandExecutor's undo stack drops entries past `max_undo_levels` (10) --
    so with a bound method, 10 unrelated commands run while the wizard sits open
    would collect the command and silently break Finish. A lambda closure holds
    a real strong reference instead.
    """
    app_context, _ = app_context_with_project
    wizard = _fake_wizard()
    mock_wizard_cls.return_value = wizard

    command = CreateChartFromWizardCommand(app_context)
    assert command.execute() is True

    callback = wizard.finished.connect.call_args[0][0]
    assert not isinstance(callback, MethodType), (
        "`finished` must not be connected to a bound method -- PySide would then "
        "hold the command only weakly"
    )
    assert callback is not command._on_wizard_finished


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_the_connected_callback_still_works_after_the_command_is_dropped(
        mock_wizard_cls, app_context_with_project):
    """Maximum-fidelity version of the lifetime guard.

    Drop every local reference to the command, force a full collection, then
    fire the callable the command handed to `finished.connect`: it must still
    create the chart, proving the connection itself keeps the command alive.
    """
    app_context, project = app_context_with_project
    wizard = _fake_wizard(chart_type="line", is_empty=True)
    mock_wizard_cls.return_value = wizard

    command = CreateChartFromWizardCommand(app_context)
    assert command.execute() is True
    callback = wizard.finished.connect.call_args[0][0]

    del command
    gc.collect()

    callback(QDialog.DialogCode.Accepted)

    project.add_item.assert_called_once()
    assert project.add_item.call_args[0][0].chart_type == "line"


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_the_connected_callback_uses_its_own_wizard(mock_wizard_cls, app_context_with_project):
    """A finishing wizard must build from *its* state, not `self._dialog`'s.

    Belt-and-braces against any future path that replaces `self._dialog` while
    an older wizard is still pending.
    """
    app_context, project = app_context_with_project
    first = _fake_wizard(chart_type="line", is_empty=True)
    mock_wizard_cls.return_value = first

    command = CreateChartFromWizardCommand(app_context)
    assert command.execute() is True
    first_callback = first.finished.connect.call_args[0][0]

    # Simulate `self._dialog` having been replaced by a newer wizard.
    command._dialog = _fake_wizard(chart_type="scatter", is_empty=True)

    first_callback(QDialog.DialogCode.Accepted)

    assert project.add_item.call_args[0][0].chart_type == "line"


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_execute_succeeds_before_the_wizard_has_finished(mock_wizard_cls, app_context_with_project):
    """Opening the wizard is itself success, whatever the user does next."""
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard()

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    project.add_item.assert_not_called()
    assert command.created_chart_id is None
    assert command.created_chart is None


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_execute_fails_without_a_loaded_project(mock_wizard_cls, app_context_with_project):
    app_context, _ = app_context_with_project
    app_context.get_app_state.return_value.has_project = False
    mock_wizard_cls.return_value = _fake_wizard()

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is False
    mock_wizard_cls.assert_not_called()


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_cancelled_wizard_creates_nothing(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard()

    command = CreateChartFromWizardCommand(app_context)

    # Opening the wizard succeeded even though the user then cancelled it.
    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Rejected)

    project.add_item.assert_not_called()
    assert command.created_chart_id is None


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_empty_path_creates_a_line_chart_with_no_series(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Accepted)

    created_chart = project.add_item.call_args[0][0]
    assert created_chart.chart_type == "line"
    assert created_chart.data_series == []


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_series_configs_become_data_series(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    series_configs = [{
        "dataset_id": "ds-1",
        "x_column_id": "col-date",
        "y_column_id": "col-rev",
        "x_error_column_id": "",
        "y_error_column_id": "",
        "error_symmetric": True,
    }]
    mock_wizard_cls.return_value = _fake_wizard(chart_type="hist", series_configs=series_configs)

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Accepted)

    created_chart = project.add_item.call_args[0][0]
    assert created_chart.chart_type == "hist"
    assert len(created_chart.data_series) == 1
    assert created_chart.data_series[0].dataset_id == "ds-1"
    assert created_chart.data_series[0].x_column_id == "col-date"
    assert created_chart.data_series[0].y_column_id == "col-rev"


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_chart_is_named_after_its_dataset_at_construction_time(mock_wizard_cls, app_context_with_project):
    """The name must be passed to `Chart(...)`, not patched on afterwards.

    `Chart.__init__` snapshots `config["title"] = self.name`, so a name set
    after construction leaves the rendered title permanently empty.
    """
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)

    command = CreateChartFromWizardCommand(app_context, dataset_id="ds-1")

    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Accepted)

    created_chart = project.add_item.call_args[0][0]
    assert created_chart.name == "Chart from ds"
    assert created_chart.config["title"] == "Chart from ds"


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_chart_without_an_originating_dataset_falls_back_to_new_chart(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Accepted)

    created_chart = project.add_item.call_args[0][0]
    assert created_chart.name == "New Chart"
    assert created_chart.config["title"] == "New Chart"


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_an_exception_is_reported_and_does_not_propagate(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    wizard = _fake_wizard(chart_type="line")
    wizard.get_series_configs.side_effect = KeyError("y_column_id")
    mock_wizard_cls.return_value = wizard

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Accepted)  # must not raise

    project.add_item.assert_not_called()
    app_context.get_ui_controller.return_value.show_error_message.assert_called_once()


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_a_failure_to_open_the_wizard_is_reported(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.side_effect = RuntimeError("boom")

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is False
    project.add_item.assert_not_called()
    app_context.get_ui_controller.return_value.show_error_message.assert_called_once()


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_undo_swallows_and_logs_exceptions(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)
    command = CreateChartFromWizardCommand(app_context)
    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Accepted)

    project.remove_item_by_id.side_effect = RuntimeError("boom")

    command.undo()  # must not raise


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_undo_of_a_never_finished_wizard_is_a_no_op(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)
    command = CreateChartFromWizardCommand(app_context)
    assert command.execute() is True

    command.undo()

    project.remove_item_by_id.assert_not_called()


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_redo_readds_the_same_chart_instance(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)
    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    command._on_wizard_finished(QDialog.DialogCode.Accepted)
    first_id = command.created_chart_id
    first_chart = project.add_item.call_args[0][0]

    command.undo()
    project.remove_item_by_id.assert_called_once_with(first_id)

    command.redo()
    redo_chart = project.add_item.call_args[0][0]
    assert redo_chart is first_chart
    assert command.created_chart_id == first_id


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_redo_does_not_open_a_second_wizard_while_one_is_pending(
        mock_wizard_cls, app_context_with_project):
    """Undo-then-Redo with the wizard still open must not re-open it.

    `created_chart is None` is the normal state while the wizard is open, so the
    old `redo()` treated it as "execute failed, retry" and opened a *second*
    wizard, overwriting `self._dialog` -- finishing the first, now-orphaned
    wizard then built a chart from the second wizard's state.
    """
    app_context, project = app_context_with_project
    wizard = _fake_wizard(chart_type="line", is_empty=True)
    mock_wizard_cls.return_value = wizard

    command = CreateChartFromWizardCommand(app_context)
    assert command.execute() is True
    assert command._dialog is wizard
    assert command.created_chart is None

    command.undo()  # no-op, nothing was created yet
    command.redo()

    assert mock_wizard_cls.call_count == 1
    assert command._dialog is wizard
    project.add_item.assert_not_called()

    # The still-pending wizard remains fully functional afterwards.
    wizard.finished.connect.call_args[0][0](QDialog.DialogCode.Accepted)
    project.add_item.assert_called_once()


@patch("pandaplot.gui.dialogs.chart.chart_wizard.ChartWizard")
def test_redo_retries_when_the_wizard_never_opened(mock_wizard_cls, app_context_with_project):
    """The case the original `redo()` branch existed for still works.

    `execute()` failed outright (no project), so no wizard was ever opened and
    `redo()` must retry it.
    """
    app_context, _ = app_context_with_project
    app_state = app_context.get_app_state.return_value
    app_state.has_project = False
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is False
    assert command._dialog is None
    mock_wizard_cls.assert_not_called()

    app_state.has_project = True
    command.redo()

    mock_wizard_cls.assert_called_once()
    assert command._dialog is not None
