"""GUI wiring tests for Chart Bundle Export."""

from unittest.mock import MagicMock, patch

from pandaplot.gui.controllers.ui_controller import UIController


def test_ui_controller_export_chart_bundle_dialog(qapp):
    ui = UIController()

    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName") as mock_save:
        mock_save.return_value = ("/path/to/my_chart", "Zip Archives (*.zip)")
        res = ui.show_export_chart_bundle_dialog("My Chart")
        assert res == "/path/to/my_chart.zip"
        mock_save.assert_called_once()

    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName") as mock_save:
        mock_save.return_value = ("", "")
        res = ui.show_export_chart_bundle_dialog("My Chart")
        assert res is None


def test_project_panel_command_manager_export_chart_bundle():
    app_context = MagicMock()
    app_state = MagicMock()
    cmd_executor = MagicMock()

    app_context.get_app_state.return_value = app_state
    app_context.get_command_executor.return_value = cmd_executor

    from pandaplot.gui.components.sidebar.project.project_command_manager import ProjectPanelCommandManager

    get_selected_info = MagicMock(return_value={"type": "chart", "id": "chart_123"})
    mgr = ProjectPanelCommandManager(
        app_context=app_context,
        get_target_folder_id=MagicMock(),
        get_current_item=MagicMock(),
        get_selected_item_info=get_selected_info,
        edit_item=MagicMock(),
    )

    mgr.export_chart_bundle()

    cmd_executor.execute_command.assert_called_once()
    executed_cmd = cmd_executor.execute_command.call_args[0][0]
    assert executed_cmd.chart_id == "chart_123"
