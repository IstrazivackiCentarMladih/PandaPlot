"""Command that opens the chart creation wizard and builds the resulting
Chart item — the single path every chart-creation entry point uses.

The wizard is opened non-blocking (`show()`, not `exec()`): `execute()` returns
as soon as the wizard is on screen, and the chart is built later in
`_on_wizard_finished`, driven by the wizard's `finished(int)` signal. This is
required for the pick-from-dataset flow — `DatasetColumnPicker` needs a real
hide -> change-modality -> show cycle on the wizard (the only sequence Qt
honours when updating a window's modal-blocking registration), which would tear
down a blocking `exec()` loop.
"""

from typing import Optional, override

from PySide6.QtWidgets import QDialog

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events import ChartEvents, ProjectEvents
from pandaplot.models.events.event_data import ChartCreatedData
from pandaplot.models.project.items import Chart, Dataset
from pandaplot.models.state import AppContext, AppState


class CreateChartFromWizardCommand(Command):
    """Opens `ChartWizard` non-blocking; on acceptance builds a `Chart` from it."""

    def __init__(self, app_context: AppContext, dataset_id: Optional[str] = None,
                 preselected_column_ids: Optional[list[str]] = None, parent_id: Optional[str] = None):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()

        self.created_chart_id: Optional[str] = None
        self.created_chart: Optional[Chart] = None
        self.dataset_id: Optional[str] = dataset_id
        self.preselected_column_ids: list[str] = preselected_column_ids or []
        self.parent_id: Optional[str] = parent_id
        self._dialog: Optional[QDialog] = None

    def _dataset_options(self, project) -> list[tuple[str, str]]:
        return [(item.id, item.name) for item in project.get_all_items() if isinstance(item, Dataset)]

    def _columns_provider(self, project):
        def provider(dataset_id: str) -> list[tuple[str, str]]:
            dataset = project.find_item(dataset_id)
            if not isinstance(dataset, Dataset) or dataset.data is None:
                return []
            return [(dataset.column_id(name) or "", name) for name in dataset.data.columns]
        return provider

    def _default_chart_name(self, project) -> str:
        """Name for the new chart, derived from the originating dataset.

        Computed *before* `Chart(...)` construction on purpose: `Chart.__init__`
        snapshots `config["title"] = self.name`, so a name assigned after
        construction would leave the rendered title permanently empty.
        """
        if self.dataset_id:
            dataset = project.find_item(self.dataset_id)
            if isinstance(dataset, Dataset):
                return f"Chart from {dataset.name}"
        return "New Chart"

    @override
    def execute(self) -> bool:
        from pandaplot.gui.dialogs.chart.chart_wizard import ChartWizard

        try:
            self.logger.info("Executing CreateChartFromWizardCommand")

            if not self.app_state.has_project or not self.app_state.current_project:
                self.ui_controller.show_error_message("Create Chart Error", "No project is currently loaded")
                return False
            project = self.app_state.current_project

            dialog = ChartWizard(
                self.app_context,
                parent=self.ui_controller.parent_widget,
                initial_dataset_id=self.dataset_id,
                initial_column_ids=self.preselected_column_ids,
                datasets=self._dataset_options(project),
                columns_provider=self._columns_provider(project),
            )
            # Keep a strong reference so the dialog isn't garbage-collected while
            # open -- `self` stays alive for as long as the command sits on the
            # CommandExecutor's undo stack, which outlives this call.
            self._dialog = dialog
            dialog.finished.connect(self._on_wizard_finished)
            # `exec()` used to make the wizard application-modal implicitly;
            # `show()` does not, so set it explicitly to keep the project from
            # being edited underneath a half-configured wizard. This is also
            # the modality `DatasetColumnPicker` temporarily drops (and later
            # restores) to hand the dataset table back to the user.
            dialog.setModal(True)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            return True

        except Exception as e:
            error_msg = f"Failed to open chart wizard: {str(e)}"
            self.logger.error(f"CreateChartFromWizardCommand Error: {error_msg}")
            self.ui_controller.show_error_message("Create Chart Error", error_msg)
            return False

    def _on_wizard_finished(self, result: int) -> None:
        """Runs once the user actually finishes the wizard (Finish or Cancel).

        `execute()` returning True now only means "the wizard opened
        successfully" -- the chart itself is created here, asynchronously, once
        the wizard's `finished` signal fires. A cancelled/closed wizard never
        emits `QDialog.DialogCode.Accepted`, so it simply never creates a chart
        (no error, matching the old blocking behaviour's early return on
        `Rejected`).
        """
        dialog = self._dialog
        if dialog is None or result != QDialog.DialogCode.Accepted:
            return

        try:
            if not self.app_state.has_project or not self.app_state.current_project:
                return
            project = self.app_state.current_project

            chart = Chart(name=self._default_chart_name(project), chart_type=dialog.get_chart_type())
            if not dialog.is_empty():
                for series_config in dialog.get_series_configs():
                    chart.add_data_series(
                        series_config["dataset_id"],
                        x_column_id=series_config["x_column_id"],
                        y_column_id=series_config["y_column_id"],
                        x_error_column_id=series_config["x_error_column_id"],
                        y_error_column_id=series_config["y_error_column_id"],
                        error_symmetric=series_config["error_symmetric"],
                    )

            project.add_item(chart, parent_id=self.parent_id)
            self.created_chart_id = chart.id
            self.created_chart = chart

            self.app_context.event_bus.emit(ChartEvents.CHART_CREATED, ChartCreatedData(
                chart_id=chart.id
            ).to_dict())
            self.logger.info("CreateChartFromWizardCommand: created chart '%s'", chart.id)
        except Exception as e:
            error_msg = f"Failed to create chart: {str(e)}"
            self.logger.error(f"CreateChartFromWizardCommand Error: {error_msg}")
            self.ui_controller.show_error_message("Create Chart Error", error_msg)

    @override
    def undo(self):
        if not self.created_chart_id or not self.app_state.has_project or not self.app_state.current_project:
            return
        try:
            project = self.app_state.current_project
            project.remove_item_by_id(self.created_chart_id)
            self.app_context.event_bus.emit(ProjectEvents.PROJECT_ITEM_REMOVED, {
                "item_id": self.created_chart_id,
                "item_type": "chart",
            })
            self.logger.info(
                "CreateChartFromWizardCommand: undid creation of chart '%s'", self.created_chart_id)
        except Exception as e:
            self.logger.error(f"CreateChartFromWizardCommand Undo Error: {str(e)}")

    @override
    def redo(self):
        if self.created_chart is None:
            self.execute()
            return
        if not self.app_state.has_project or not self.app_state.current_project:
            return
        project = self.app_state.current_project
        project.add_item(self.created_chart, parent_id=self.parent_id)
        self.created_chart_id = self.created_chart.id
        self.app_context.event_bus.emit(ChartEvents.CHART_CREATED, ChartCreatedData(
            chart_id=self.created_chart.id
        ).to_dict())
