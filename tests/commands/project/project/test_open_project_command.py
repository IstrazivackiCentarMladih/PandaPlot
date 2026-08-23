"""Tests for OpenProjectCommand logging behavior."""

import logging
from unittest.mock import Mock, patch

from pandaplot.commands.project.project.open_project_command import OpenProjectCommand


def test_invalid_project_file_logs_a_warning(caplog):
    app_context = Mock()
    app_context.ui_controller.show_open_project_dialog.return_value = "bad_path.pplot"

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=False):
        with caplog.at_level(logging.WARNING):
            command.execute()

    assert command.was_executed is False
    assert "bad_path.pplot" in caplog.text
