"""Command for removing fit data from a chart."""

from dataclasses import asdict
from typing import Any, Dict, Optional, override

from pandaplot.commands.base_command import Command
from pandaplot.models.events import ChartEvents
from pandaplot.models.project.items.chart import Chart, fit_from_flat_dict
from pandaplot.models.state import AppContext


class RemoveFitDataCommand(Command):
    """Command to remove fit data from an existing chart."""

    def __init__(self, app_context: AppContext, chart_id: str, fit_index: int):
        super().__init__()
        self.app_context = app_context
        self.chart_id = chart_id
        self.fit_index = fit_index
        self.removed_fit_data: Optional[Dict[str, Any]] = None

    def _find_chart(self) -> Optional[Chart]:
        app_state = self.app_context.get_app_state()
        if not app_state.has_project or not app_state.current_project:
            return None
        return app_state.current_project.find_item(self.chart_id)

    @override
    def execute(self) -> bool:
        chart = self._find_chart()
        if not chart or not isinstance(chart, Chart):
            return False

        if self.fit_index < 0 or self.fit_index >= len(chart.fit_data):
            return False

        # Snapshot the fit data before removing
        fit = chart.fit_data[self.fit_index]
        self.removed_fit_data = asdict(fit)

        chart.remove_fit_data(self.fit_index)

        self.app_context.event_bus.emit(ChartEvents.CHART_UPDATED, {
            "chart_id": self.chart_id,
            "update_type": "fit_removed",
            "chart": chart,
        })
        return True

    @override
    def undo(self):
        chart = self._find_chart()
        if not chart or self.removed_fit_data is None:
            return

        # Re-create and insert at original position
        fit = fit_from_flat_dict(self.removed_fit_data)
        chart.fit_data.insert(self.fit_index, fit)
        chart.update_modified_time()

        self.app_context.event_bus.emit(ChartEvents.CHART_UPDATED, {
            "chart_id": self.chart_id,
            "update_type": "fit_added",
            "chart": chart,
        })

    @override
    def redo(self):
        self.execute()
