"""Command for generating a standalone fit report (a note plus a dataset of
fitted values) from a completed curve fit, without touching the chart."""

import uuid
from typing import Optional, override

import pandas as pd

from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events.event_types import DatasetEvents, ProjectEvents
from pandaplot.models.project.items import Dataset, Note
from pandaplot.models.state import AppContext, AppState
from pandaplot.services.fit.fit_service import FitResult, FitService


class CreateFitReportCommand(Command):
    """Creates a Note (a human-readable fit report) and a Dataset (the
    fitted x/y values) from a :class:`FitResult`, and adds both to the
    project as their own items -- rather than bundling the fit only into the
    chart it was performed on (see issue #95)."""

    def __init__(
        self,
        app_context: AppContext,
        fit_results: FitResult,
        source_dataset_id: str,
        source_x_column: str = "",
        source_y_column: str = "",
        fixed_parameters: Optional[str] = None,
        *,
        report_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
        folder_id: Optional[str] = None,
    ):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()

        self.fit_results = fit_results
        self.source_dataset_id = source_dataset_id
        self.source_x_column = source_x_column
        self.source_y_column = source_y_column
        self.fixed_parameters = fixed_parameters
        self.report_name = report_name
        self.dataset_name = dataset_name
        self.folder_id = folder_id

        # State for undo/redo.
        self.result_dataset_id: Optional[str] = None
        self.report_note_id: Optional[str] = None

    def _report_text(self) -> str:
        results = self.fit_results
        fit_service = FitService()

        lines = [
            f"# Fit Report: {results.fit_type}",
            "",
            "## Equation",
            "",
            results.equation or "Unknown equation",
            "",
            "## Parameters",
            "",
            fit_service.format_parameters(
                results.param_names,
                results.params,
                results.errors,
                fixed_parameters=self.fixed_parameters,
            ),
            "",
        ]

        if results.r_squared is not None:
            lines += [f"R² = {results.r_squared:.6f}", ""]

        lines += [
            "## Data",
            "",
            f"Source dataset: {self.source_dataset_id}",
            f"X column: {self.source_x_column or '?'}",
            f"Y column: {self.source_y_column or '?'}",
            f"Data points: {len(results.x_data)}",
            f"Fit points: {len(results.x_fit)}",
        ]

        return "\n".join(lines)

    def _fit_dataframe(self) -> pd.DataFrame:
        results = self.fit_results
        data = {"x": results.x_fit, "y": results.y_fit}
        if results.confidence_lower is not None:
            data["y_lower"] = results.confidence_lower
        if results.confidence_upper is not None:
            data["y_upper"] = results.confidence_upper
        return pd.DataFrame(data)

    @override
    def execute(self) -> CommandResult:
        try:
            self.logger.info(
                "Executing CreateFitReportCommand for fit type %s", self.fit_results.fit_type
            )
            if not self.app_state.has_project or not self.app_state.current_project:
                message = "No project loaded; cannot create fit report."
                self.logger.warning(message)
                self.ui_controller.show_error_message("Fit Report Error", message)
                return CommandResult.FAILURE

            project = self.app_state.current_project

            if self.folder_id is None:
                source = project.find_item(self.source_dataset_id)
                self.folder_id = source.parent_id if source else None

            short_name = self.fit_results.fit_type.split(" (")[0]

            # Fitted values dataset.
            dataset_name = self.dataset_name or f"{short_name} Fit Data"
            self.result_dataset_id = str(uuid.uuid4())
            dataset = Dataset(
                id=self.result_dataset_id,
                name=dataset_name,
                data=self._fit_dataframe(),
                source_file=None,
            )
            project.add_item(dataset, parent_id=self.folder_id)
            self.app_state.event_bus.emit(DatasetEvents.DATASET_CREATED, {
                "project": project,
                "dataset_id": self.result_dataset_id,
                "dataset_name": dataset_name,
                "folder_id": self.folder_id,
                "dataset_data": dataset.data,
            })

            # Written report note.
            report_name = self.report_name or f"{short_name} Fit Report"
            self.report_note_id = str(uuid.uuid4())
            note = Note(
                id=self.report_note_id,
                name=report_name,
                content=self._report_text(),
            )
            project.add_item(note, parent_id=self.folder_id)
            self.app_state.event_bus.emit(ProjectEvents.PROJECT_ITEM_ADDED, {
                "project": project,
                "note_id": self.report_note_id,
                "note_name": report_name,
                "folder_id": self.folder_id,
                "note": note,
            })

            self.logger.info(
                "Created fit report '%s' and fit data '%s'", report_name, dataset_name
            )
            return CommandResult.SUCCESS

        except Exception as e:
            self.logger.error("Fit report creation failed: %s", e, exc_info=True)
            self.ui_controller.show_error_message("Fit Report Error", str(e))
            return CommandResult.FAILURE

    @override
    def undo(self) -> CommandResult:
        try:
            if not self.app_state.current_project:
                self.logger.warning(
                    "CreateFitReportCommand.undo: no project loaded; cannot undo report '%s'",
                    self.report_note_id,
                )
                return CommandResult.FAILURE
            project = self.app_state.current_project

            if self.report_note_id:
                note = project.find_item(self.report_note_id)
                if note:
                    project.remove_item(note)
                    self.app_state.event_bus.emit(ProjectEvents.PROJECT_ITEM_REMOVED, {
                        "project": project,
                        "note_id": self.report_note_id,
                        "note": note,
                    })

            if self.result_dataset_id:
                dataset = project.find_item(self.result_dataset_id)
                if dataset:
                    project.remove_item(dataset)
                    self.app_state.event_bus.emit(DatasetEvents.DATASET_DELETED, {
                        "project": project,
                        "dataset_id": self.result_dataset_id,
                        "dataset_name": dataset.name,
                    })

            self.logger.info("Undone fit report '%s'", self.report_note_id)
            return CommandResult.SUCCESS
        except Exception as e:
            self.logger.error("Failed to undo fit report: %s", e, exc_info=True)
            return CommandResult.FAILURE

    @override
    def redo(self) -> CommandResult:
        return self.execute()

    @override
    def cleanup(self) -> None:
        """Release the created-dataset/note ids held for undo once this
        command is dropped from the stacks for good (see Command.cleanup)."""
        self.result_dataset_id = None
        self.report_note_id = None
