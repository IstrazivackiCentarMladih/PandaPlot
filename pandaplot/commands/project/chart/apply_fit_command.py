"""Command for applying a fit to a chart."""

from typing import Optional, override

from pandaplot.commands.base_command import Command
from pandaplot.models.events import ChartEvents
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.state import AppContext


class ApplyFitCommand(Command):
    """Command to apply fitted data to an existing chart."""

    def __init__(
        self,
        app_context: AppContext,
        chart_id: str,
        fit_results,
        source_dataset_id: str,
        source_x_column_id: str,
        source_y_column_id: str,
        source_x_column: str = "",
        source_y_column: str = "",
        label: str = "",
    ):
        super().__init__()

        self.app_context = app_context
        self.chart_id = chart_id
        self.fit_results = fit_results

        self.source_dataset_id = source_dataset_id
        self.source_x_column_id = source_x_column_id
        self.source_y_column_id = source_y_column_id
        self.source_x_column = source_x_column
        self.source_y_column = source_y_column
        self.label = label

        self.added_index: Optional[int] = None

    def _find_chart(self) -> Optional[Chart]:
        app_state = self.app_context.get_app_state()

        if not app_state.has_project or not app_state.current_project:
            return None

        chart = app_state.current_project.find_item(self.chart_id)

        if not isinstance(chart, Chart):
            return None

        return chart

    @override
    def execute(self) -> bool:
        chart = self._find_chart()

        if chart is None:
            return False

        results = self.fit_results

        chart.add_fit_data(
            source_dataset_id=self.source_dataset_id,
            source_x_column_id=self.source_x_column_id,
            source_y_column_id=self.source_y_column_id,
            fit_type=results.fit_type,
            x_data=results.x_fit,
            y_data=results.y_fit,
            source_x_column=self.source_x_column,
            source_y_column=self.source_y_column,
            label=self.label,
            fit_params={
                name: value
                for name, value in zip(
                    results.param_names,
                    results.params,
                )
            },
            fit_stats={
                "r_squared": results.r_squared,
            },
            confidence_lower=results.confidence_lower,
            confidence_upper=results.confidence_upper,
        )

        self.added_index = len(chart.fit_data) - 1

        self.app_context.event_bus.emit(
            ChartEvents.CHART_UPDATED,
            {
                "chart_id": self.chart_id,
                "update_type": "fit_added",
                "chart": chart,
            },
        )

        return True

    @override
    def undo(self):
        chart = self._find_chart()

        if chart is None or self.added_index is None:
            return

        chart.remove_fit_data(self.added_index)

        self.app_context.event_bus.emit(
            ChartEvents.CHART_UPDATED,
            {
                "chart_id": self.chart_id,
                "update_type": "fit_removed",
                "chart": chart,
            },
        )

    @override
    def redo(self):
        self.execute()
