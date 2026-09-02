"""Command for converting a data series into a fit-data entry on a chart."""

import copy
from typing import Optional, override

import numpy as np

from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.chart.fit_style import FitStyle
from pandaplot.models.events import ChartEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart, DataSeries, FitData, resolve_series_column
from pandaplot.models.state import AppContext


class ConvertSeriesToFitCommand(Command):
    """Command to convert an existing DataSeries into a FitData entry (#298).

    Snapshots the source dataset's X/Y (and optional confidence lower/
    upper) columns into FitData.x_data/y_data/confidence_lower/
    confidence_upper at the moment of conversion -- matching
    ApplyFitCommand's existing behavior where a fit's data is a snapshot,
    not a live reference (unlike DataSeries, which resolves column ids
    live). Error-bar/vector/Z columns configured on the source series are
    dropped -- FitData has no such concepts.
    """

    def __init__(
        self,
        app_context: AppContext,
        chart_id: str,
        series_index: int,
        confidence_lower_column_id: str = "",
        confidence_upper_column_id: str = "",
    ):
        super().__init__()
        self.app_context = app_context
        self.ui_controller: UIController = app_context.get_ui_controller()
        self.chart_id = chart_id
        self.series_index = series_index
        self.confidence_lower_column_id = confidence_lower_column_id
        self.confidence_upper_column_id = confidence_upper_column_id

        # State for undo/redo, mirroring ApplyFitCommand's caching: the
        # FitData is built once (first execute()) and reused on redo, and
        # the original series is snapshotted once so undo can restore it
        # at its original position.
        self.removed_series: Optional[DataSeries] = None
        self.added_fit_index: Optional[int] = None
        self._fit: Optional[FitData] = None

    def _find_chart(self) -> Optional[Chart]:
        app_state = self.app_context.get_app_state()
        if not app_state.has_project or not app_state.current_project:
            return None
        chart = app_state.current_project.find_item(self.chart_id)
        return chart if isinstance(chart, Chart) else None

    def _find_dataset(self, dataset_id: str) -> Optional[Dataset]:
        app_state = self.app_context.get_app_state()
        project = app_state.current_project if app_state.has_project else None
        if project is None:
            return None
        dataset = project.find_item(dataset_id)
        return dataset if isinstance(dataset, Dataset) else None

    def _column_array(self, dataset: Optional[Dataset], column_id: str) -> Optional[np.ndarray]:
        if dataset is None or not column_id:
            return None
        name = resolve_series_column(dataset, column_id, "")
        if not name or dataset.data is None or name not in dataset.data.columns:
            return None
        return dataset.data[name].to_numpy(copy=True)

    def _build_fit(self, series: DataSeries) -> Optional[FitData]:
        dataset = self._find_dataset(series.dataset_id)
        x_data = self._column_array(dataset, series.x_column_id)
        y_data = self._column_array(dataset, series.y_column_id)
        if dataset is None or x_data is None or y_data is None:
            return None

        return FitData(
            source_dataset_id=series.dataset_id,
            source_x_column_id=series.x_column_id,
            source_y_column_id=series.y_column_id,
            fit_type="Custom",
            x_data=x_data,
            y_data=y_data,
            label=series.label,
            confidence_lower=self._column_array(dataset, self.confidence_lower_column_id),
            confidence_upper=self._column_array(dataset, self.confidence_upper_column_id),
            style=FitStyle(),
        )

    @override
    def execute(self) -> CommandResult:
        chart = self._find_chart()
        if chart is None:
            self.logger.warning(
                "ConvertSeriesToFitCommand.execute: chart '%s' not found or not a Chart",
                self.chart_id,
            )
            self.ui_controller.show_error_message(
                "Convert to Fit Error", f"Chart '{self.chart_id}' not found."
            )
            return CommandResult.FAILURE

        if self.series_index < 0 or self.series_index >= len(chart.data_series):
            self.logger.warning(
                "ConvertSeriesToFitCommand.execute: series_index %s out of range for "
                "chart '%s' (%d series)",
                self.series_index, self.chart_id, len(chart.data_series),
            )
            self.ui_controller.show_error_message(
                "Convert to Fit Error", f"Series index {self.series_index} is out of range."
            )
            return CommandResult.FAILURE

        series = chart.data_series[self.series_index]

        if self._fit is None:
            fit = self._build_fit(series)
            if fit is None:
                self.logger.warning(
                    "ConvertSeriesToFitCommand.execute: could not resolve source data "
                    "for series at index %s on chart '%s'",
                    self.series_index, self.chart_id,
                )
                self.ui_controller.show_error_message(
                    "Convert to Fit Error", "Could not read the series' source data."
                )
                return CommandResult.FAILURE
            self._fit = fit
            self.removed_series = copy.deepcopy(series)

        chart.remove_data_series(self.series_index)
        chart.fit_data.append(self._fit)
        self.added_fit_index = len(chart.fit_data) - 1
        chart.update_modified_time()

        self.app_context.event_bus.emit(ChartEvents.CHART_UPDATED, {
            "chart_id": self.chart_id,
            "update_type": "series_converted_to_fit",
            "chart": chart,
        })
        return CommandResult.SUCCESS

    @override
    def undo(self) -> CommandResult:
        chart = self._find_chart()
        if chart is None or self.removed_series is None or self.added_fit_index is None:
            self.logger.warning(
                "ConvertSeriesToFitCommand.undo: cannot undo for chart '%s' (chart "
                "found=%s, removed_series set=%s, added_fit_index set=%s)",
                self.chart_id, chart is not None,
                self.removed_series is not None, self.added_fit_index is not None,
            )
            return CommandResult.FAILURE

        chart.remove_fit_data(self.added_fit_index)
        chart.data_series.insert(self.series_index, copy.deepcopy(self.removed_series))
        chart.update_modified_time()

        self.app_context.event_bus.emit(ChartEvents.CHART_UPDATED, {
            "chart_id": self.chart_id,
            "update_type": "fit_converted_to_series",
            "chart": chart,
        })
        return CommandResult.SUCCESS

    @override
    def redo(self) -> CommandResult:
        return self.execute()

    @override
    def cleanup(self) -> None:
        """Release the removed-series/added-fit bookkeeping held for undo
        once this command is dropped from the stacks for good (see
        Command.cleanup)."""
        self.removed_series = None
        self.added_fit_index = None
        self._fit = None
