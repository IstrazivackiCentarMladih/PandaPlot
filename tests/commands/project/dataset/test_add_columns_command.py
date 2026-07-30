from unittest.mock import Mock

import pandas as pd
import pytest

from pandaplot.commands.project.dataset.add_columns_command import AddColumnsCommand
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.state import AppContext, AppState


class TestAddColumnsCommandDefaultDtype:
    """Test suite for AddColumnsCommand's default (no default_values) column dtype."""

    @pytest.fixture
    def mock_app_context(self):
        app_context = Mock(spec=AppContext)
        app_state = Mock(spec=AppState)
        ui_controller = Mock(spec=UIController)

        app_context.get_app_state.return_value = app_state
        app_context.get_ui_controller.return_value = ui_controller
        app_state.event_bus = Mock()
        app_state.event_bus.emit = Mock()

        return app_context, app_state, ui_controller

    @pytest.fixture
    def sample_project(self):
        project = Mock()
        project.find_item = Mock()
        return project

    def test_new_column_defaults_to_float64_zero_when_dataset_has_only_strings(
        self, mock_app_context, sample_project
    ):
        """Before this change, a dataset with only string columns made new
        columns default to '' (object dtype). They must now default to
        float64 filled with 0.0 regardless of existing column types."""
        app_context, app_state, ui_controller = mock_app_context
        app_state.has_project = True
        app_state.current_project = sample_project

        dataset = Dataset(id="ds-1", name="Test", data=pd.DataFrame({"a": ["x", "y"]}))
        sample_project.find_item.return_value = dataset

        command = AddColumnsCommand(
            app_context, "ds-1", column_names=["b"], reference_positions=[0], side="right"
        )
        result = command.execute()

        assert result is True
        assert str(dataset.data["b"].dtype) == "float64"
        assert dataset.data["b"].tolist() == [0.0, 0.0]

    def test_new_column_defaults_to_float64_zero_when_dataset_has_numeric_columns(
        self, mock_app_context, sample_project
    ):
        """Before this change, a dataset with an existing numeric column made
        new columns default to int-ish 0. They must now be float64 with 0.0,
        same as the string case -- the heuristic branch is gone entirely."""
        app_context, app_state, ui_controller = mock_app_context
        app_state.has_project = True
        app_state.current_project = sample_project

        dataset = Dataset(id="ds-1", name="Test", data=pd.DataFrame({"a": [1, 2, 3]}))
        sample_project.find_item.return_value = dataset

        command = AddColumnsCommand(
            app_context, "ds-1", column_names=["b"], reference_positions=[0], side="right"
        )
        result = command.execute()

        assert result is True
        assert str(dataset.data["b"].dtype) == "float64"
        assert dataset.data["b"].tolist() == [0.0, 0.0, 0.0]

    def test_explicit_default_value_still_honored(self, mock_app_context, sample_project):
        """Passing an explicit default_values entry must still bypass the
        float64/0.0 default and keep today's type-preserving behavior."""
        app_context, app_state, ui_controller = mock_app_context
        app_state.has_project = True
        app_state.current_project = sample_project

        dataset = Dataset(id="ds-1", name="Test", data=pd.DataFrame({"a": [1, 2, 3]}))
        sample_project.find_item.return_value = dataset

        command = AddColumnsCommand(
            app_context, "ds-1", column_names=["b"], reference_positions=[0], side="right",
            default_values=["hello"]
        )
        result = command.execute()

        assert result is True
        assert dataset.data["b"].tolist() == ["hello", "hello", "hello"]
