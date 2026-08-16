"""
Shared fixtures for image command tests.

Mirrors the mock_app_context/sample_project construction pattern used in
tests/commands/project/folder/test_create_folder_command.py, but collapses
it into a single app_context_with_project fixture (with a project already
attached and has_project=True) since every test in this package needs a
usable project.
"""

from unittest.mock import Mock

import pytest

from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.project import Project
from pandaplot.models.state import AppContext, AppState


@pytest.fixture
def app_context_with_project():
    """Create a mock AppContext wired to a real Project, ready to use."""
    app_context = Mock(spec=AppContext)
    app_state = Mock(spec=AppState)
    ui_controller = Mock(spec=UIController)

    event_bus = Mock()
    app_state.event_bus = event_bus
    app_state.has_project = True
    app_state.current_project = Project(name="Test Project")

    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = ui_controller

    return app_context
