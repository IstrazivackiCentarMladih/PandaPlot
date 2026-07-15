from unittest.mock import Mock

import pandas as pd
import pytest

from pandaplot.commands.project.dataset.change_column_dtype_command import ChangeColumnDtypeCommand
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.state import AppContext, AppState


class TestChangeColumnDtypeCommand:
    """Test suite for ChangeColumnDtypeCommand."""

    @pytest.fixture
    def mock_app_context(self):
        app_context = Mock(spec=AppContext)
        app_state = Mock(spec=AppState)
        ui_controller = Mock(spec=UIController)

        app_context.get_app_state.return_value = app_state
        app_context.get_ui_controller.return_value = ui_controller
        app_context.event_bus = Mock()
        app_context.event_bus.emit = Mock()

        return app_context, app_state, ui_controller

    @pytest.fixture
    def sample_project(self):
        project = Mock()
        project.find_item = Mock()
        return project

    def test_int_column_with_only_whole_numbers_converts_to_float64(self, mock_app_context, sample_project):
        """A column of whole-number ints (e.g. 1, 2, 3) must actually become
        float64 when the user picks 'Decimal' -- pd.to_numeric alone keeps
        such a column as int64 since every value downcasts cleanly."""
        app_context, app_state, ui_controller = mock_app_context
        app_state.has_project = True
        app_state.current_project = sample_project

        dataset = Dataset(id="ds-1", name="Test", data=pd.DataFrame({"a": [1, 2, 3]}))
        sample_project.find_item.return_value = dataset

        command = ChangeColumnDtypeCommand(app_context, "ds-1", 0, "float64")
        result = command.execute()

        assert result is True
        assert str(dataset.data["a"].dtype) == "float64"
