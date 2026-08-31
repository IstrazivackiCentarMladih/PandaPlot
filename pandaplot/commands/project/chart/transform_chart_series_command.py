"""Command to transform a chart series' x or y values into a new dataset.

Chart series come in two flavours (see series_xy.resolve_series_xy): data
series (a live dataset column reference) and fit series (resampled arrays).
This command evaluates a transform expression -- the same expression syntax
the dataset Transform panel uses -- against one of a series' resolved axes,
and writes the result, alongside the untouched axis, to a new Dataset
project item, the same way AnalyzeChartSeriesCommand does for analysis
results (#268). It then also adds a new data series to the chart pointing at
that dataset, so the transform's effect is visible on the chart immediately
-- from there it's an ordinary series like any other (restylable, removable,
independently re-pointed at a different column via the Data tab).
"""

import uuid
from typing import Literal, Optional, override

import pandas as pd

from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.commands.project.chart.series_xy import SourceKind, resolve_series_xy
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events import ChartEvents
from pandaplot.models.events.event_types import ProjectEvents
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
        self.added_series_index: Optional[int] = None

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
        local_vars = {"x": x, "y": y}
        try:
            result = expression_engine.evaluate_expression(self.expression, local_vars)
        except Exception as e:
            raise ValueError(f"Expression failed: {e}") from e

        if not isinstance(result, pd.Series):
            if pd.api.types.is_scalar(result):
                result = pd.Series([result] * len(target_series), index=target_series.index)
            else:
                result = pd.Series(result, index=target_series.index)

        if len(result) != len(target_series):
            raise ValueError(
                f"Expression returned {len(result)} values but the series has {len(target_series)} points."
            )

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

    def _unique_dataset_name(self, project, name: str) -> str:
        """Return `name`, or `name (N)` for the smallest N >= 2 not already
        used by a sibling in the target folder -- so re-running the same
        transform (or two transforms that land on the same default name)
        doesn't produce two indistinguishable "Y (y transformed)" datasets
        sitting side by side in the project explorer."""
        parent = project.find_item(self.folder_id) if self.folder_id else None
        siblings = parent.get_items() if parent is not None else project.get_root_items()
        existing_names = {item.name for item in siblings}
        if name not in existing_names:
            return name
        counter = 2
        candidate = f"{name} ({counter})"
        while candidate in existing_names:
            counter += 1
            candidate = f"{name} ({counter})"
        return candidate

    @override
    def execute(self) -> CommandResult:
        try:
            if not self.app_state.has_project or not self.app_state.current_project:
                message = "No project loaded; cannot transform chart series."
                self.logger.warning(message)
                self.ui_controller.show_error_message("Chart Transform Error", message)
                return CommandResult.FAILURE

            chart = self._get_chart()
            if chart is None:
                message = "Chart is not available."
                self.logger.warning(message)
                self.ui_controller.show_error_message("Chart Transform Error", message)
                return CommandResult.FAILURE

            project = self.app_state.current_project
            results_df, default_name = self.run_transform()
            name = self._unique_dataset_name(project, self.result_name or default_name)

            self.result_dataset_id = str(uuid.uuid4())
            dataset = Dataset(
                id=self.result_dataset_id,
                name=name,
                data=results_df,
                source_file=None,
            )
            project.add_item(dataset, parent_id=self.folder_id)

            # The generic item-added/item-removed events (not the narrower,
            # legacy DatasetEvents.DATASET_CREATED/DELETED -- see
            # import_data_command.py's TODO(#219)) are what the project
            # explorer tree and other item-type-agnostic listeners actually
            # refresh on.
            self.app_state.event_bus.emit(ProjectEvents.PROJECT_ITEM_ADDED, {
                "project": project,
                "item_id": self.result_dataset_id,
                "item_type": "dataset",
                "item_name": name,
                "item": dataset,
                "folder_id": self.folder_id,
            })

            # The result dataframe's columns are always (x column, y column),
            # in that order, regardless of which one was the transform target
            # -- see run_transform()'s two branches.
            x_column, y_column = results_df.columns[0], results_df.columns[1]
            chart.add_data_series(
                dataset_id=self.result_dataset_id,
                x_column_id=dataset.column_id(x_column) or "",
                y_column_id=dataset.column_id(y_column) or "",
                x_column=x_column,
                y_column=y_column,
                label=name,
            )
            # add_data_series() always appends, so the new series is the last
            # element -- found this way (not list.index(new_series)) since
            # DataSeries is a plain dataclass: two field-identical series
            # (possible if this command runs twice with the same inputs)
            # would make index() return the earlier, wrong one.
            self.added_series_index = len(chart.data_series) - 1

            self.app_state.event_bus.emit(ChartEvents.CHART_UPDATED, {
                "chart_id": self.chart_id,
                "update_type": "series_added",
                "chart": chart,
            })

            self.logger.info(
                "Created chart-transform dataset '%s' (%s) and added it as a series to chart '%s'",
                name, self.result_dataset_id, self.chart_id,
            )
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

            chart = self._get_chart()
            if chart is not None and self.added_series_index is not None:
                chart.remove_data_series(self.added_series_index)
                self.app_state.event_bus.emit(ChartEvents.CHART_UPDATED, {
                    "chart_id": self.chart_id,
                    "update_type": "series_removed",
                    "chart": chart,
                })

            dataset = project.find_item(self.result_dataset_id)
            if dataset:
                dataset_name = dataset.name
                project.remove_item(dataset)
                self.app_state.event_bus.emit(ProjectEvents.PROJECT_ITEM_REMOVED, {
                    "project": project,
                    "item_id": self.result_dataset_id,
                    "item_type": "dataset",
                    "item_name": dataset_name,
                })
            return CommandResult.SUCCESS
        except Exception as e:
            self.logger.error("Failed to undo transform-chart-series: %s", e, exc_info=True)
            return CommandResult.FAILURE

    @override
    def redo(self) -> CommandResult:
        return self.execute()
