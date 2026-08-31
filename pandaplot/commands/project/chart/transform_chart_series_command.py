"""Command to transform a chart series' x or y values into a new dataset.

Chart series come in two flavours (see series_xy.resolve_series_xy): data
series (a live dataset column reference) and fit series (resampled arrays).
This command evaluates a transform expression -- the same expression syntax
the dataset Transform panel uses -- against one of a series' resolved axes,
and writes the result, alongside the untouched axis, to a new Dataset
project item, the same way AnalyzeChartSeriesCommand does for analysis
results (#268). Once created, the new dataset is an ordinary dataset: the
user points a chart series at it via the Data tab, like any other series.
"""

import uuid
from typing import Literal, Optional, override

import pandas as pd

from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.commands.project.chart.series_xy import SourceKind, resolve_series_xy
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events.event_types import DatasetEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.state import AppContext, AppState
from pandaplot.services.transform import expression_engine

Target = Literal["x", "y"]


class TransformChartSeriesCommand(Command):
    """Transform a chart series' x or y values via an expression, into a new dataset."""

    def __init__(
        self,
        app_context: AppContext,
        chart_id: str,
        source_kind: SourceKind,
        source_index: int,
        target: Target,
        expression: str,
        result_name: Optional[str] = None,
        folder_id: Optional[str] = None,
    ):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()

        self.chart_id = chart_id
        self.source_kind = source_kind
        self.source_index = source_index
        self.target = target
        self.expression = expression
        self.result_name = result_name
        self.folder_id = folder_id

        # State for undo/redo.
        self.result_dataset_id: Optional[str] = None

    def _get_chart(self) -> Optional[Chart]:
        project = self.app_state.current_project
        if not project:
            return None
        item = project.find_item(self.chart_id)
        return item if isinstance(item, Chart) else None

    def run_transform(self) -> tuple[pd.DataFrame, str]:
        """Compute the transform and return (result dataframe, default name).

        Raises ValueError if the chart/series/expression is unavailable or
        invalid. Does not touch the project, so the UI can call it for a
        preview.
        """
        chart = self._get_chart()
        if chart is None:
            raise ValueError("Chart is not available.")

        x, y, x_label, y_label = resolve_series_xy(self.app_state, chart, self.source_kind, self.source_index)
        if len(x) < 1:
            raise ValueError("Series has no points to transform.")

        is_valid, error_msg = expression_engine.validate_expression(self.expression)
        if not is_valid:
            raise ValueError(error_msg)

        target_series = x if self.target == "x" else y
        local_vars = {
            "x": x, "y": y,
            "value": target_series, "column": target_series, "data": target_series,
        }
        try:
            result = expression_engine.evaluate_expression(self.expression, local_vars)
        except Exception as e:
            raise ValueError(f"Expression failed: {e}") from e

        if not isinstance(result, pd.Series):
            if pd.api.types.is_scalar(result):
                result = pd.Series([result] * len(target_series), index=target_series.index)
            else:
                result = pd.Series(result, index=target_series.index)

        transformed_label = f"{x_label if self.target == 'x' else y_label} (transformed)"
        if self.target == "x":
            results_df = pd.DataFrame({
                transformed_label: result.reset_index(drop=True),
                y_label: y.reset_index(drop=True),
            })
        else:
            results_df = pd.DataFrame({
                x_label: x.reset_index(drop=True),
                transformed_label: result.reset_index(drop=True),
            })
        default_name = f"{y_label} ({self.target} transformed)"
        return results_df, default_name

    @override
    def execute(self) -> CommandResult:
        try:
            if not self.app_state.has_project or not self.app_state.current_project:
                message = "No project loaded; cannot transform chart series."
                self.logger.warning(message)
                self.ui_controller.show_error_message("Chart Transform Error", message)
                return CommandResult.FAILURE

            project = self.app_state.current_project
            results_df, default_name = self.run_transform()
            name = self.result_name or default_name

            self.result_dataset_id = str(uuid.uuid4())
            dataset = Dataset(
                id=self.result_dataset_id,
                name=name,
                data=results_df,
                source_file=None,
            )
            project.add_item(dataset, parent_id=self.folder_id)

            self.app_state.event_bus.emit(DatasetEvents.DATASET_CREATED, {
                "project": project,
                "dataset_id": self.result_dataset_id,
                "dataset_name": name,
                "folder_id": self.folder_id,
                "dataset_data": dataset.data,
            })
            self.logger.info("Created chart-transform dataset '%s' (%s)", name, self.result_dataset_id)
            return CommandResult.SUCCESS

        except ValueError as e:
            self.logger.warning("Transform-chart-series failed: %s", e)
            self.ui_controller.show_error_message("Chart Transform Error", str(e))
            return CommandResult.FAILURE
        except Exception as e:
            self.logger.error("Transform-chart-series failed: %s", e, exc_info=True)
            self.ui_controller.show_error_message("Chart Transform Error", str(e))
            return CommandResult.FAILURE

    @override
    def undo(self) -> CommandResult:
        try:
            if not self.result_dataset_id or not self.app_state.current_project:
                return CommandResult.FAILURE
            project = self.app_state.current_project
            dataset = project.find_item(self.result_dataset_id)
            if dataset:
                project.remove_item(dataset)
                self.app_state.event_bus.emit(DatasetEvents.DATASET_DELETED, {
                    "project": project,
                    "dataset_id": self.result_dataset_id,
                    "dataset_name": dataset.name,
                })
            return CommandResult.SUCCESS
        except Exception as e:
            self.logger.error("Failed to undo transform-chart-series: %s", e, exc_info=True)
            return CommandResult.FAILURE

    @override
    def redo(self) -> CommandResult:
        return self.execute()
