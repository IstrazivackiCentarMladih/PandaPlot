"""Logging-only tests for TransformColumnCommand.undo's failure paths.

TransformColumnCommand does not otherwise have a dedicated test file; these
tests cover only the warning logging added for genuine failures in undo()
(see issue-184-audit-command-logging).
"""

import logging
from unittest.mock import Mock

import pandas as pd
import pytest

from pandaplot.commands.project.dataset.transform_column_command import TransformColumnCommand
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.state.app_context import AppContext


def _make_command(app_context=None):
    app_context = app_context or Mock(spec=AppContext)
    return TransformColumnCommand(
        app_context, "ds-1",
        {
            "new_column_name": "result",
            "transform_type": "column",
            "source_columns": ["a"],
            "expression": "value * 2",
        },
    )


def test_undo_logs_a_warning_when_dataset_not_set(caplog):
    command = _make_command()
    # undo() called without a prior successful execute(): self.dataset is None.

    with caplog.at_level(logging.WARNING):
        assert command.undo() is False
    assert "ds-1" in caplog.text


def test_undo_logs_a_warning_when_dataset_has_no_data(caplog):
    command = _make_command()
    dataset = Mock(spec=Dataset)
    dataset.data = None
    command.dataset = dataset

    with caplog.at_level(logging.WARNING):
        assert command.undo() is False
    assert "ds-1" in caplog.text
