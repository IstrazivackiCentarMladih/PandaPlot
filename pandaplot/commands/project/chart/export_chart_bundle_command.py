"""
Command to export a Chart as a standalone Python code and data bundle (.zip).
"""

from typing import Any, Callable, Optional, Tuple, override

from pandaplot.commands.base_command import Command, CommandResult
from pandaplot.commands.project.current_project import get_current_project
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState
from pandaplot.services.export.chart_bundle_exporter import ChartBundleExporter
from pandaplot.services.qtasks import TaskScheduler


class ExportChartBundleCommand(Command):
    """
    Command to export a chart as a Python code + data bundle (.zip).
    """

    def __init__(self, app_context: AppContext, chart_id: str, export_path: Optional[str] = None):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()
        self.task_scheduler: TaskScheduler = app_context.get_task_scheduler()

        self.chart_id = chart_id
        self.export_path = export_path

        self.project = None
        self.chart = None
        self.is_exporting = False

    @override
    def marks_project_modified(self) -> bool:
        """Only writes an external zip file; project is never modified."""
        return False

    @override
    def occupies_undo_slot(self) -> bool:
        """Exporting to a file is not an undoable project mutation."""
        return False

    @override
    def execute(self) -> CommandResult:
        """Execute the export chart bundle command."""
        try:
            self.logger.info("Executing ExportChartBundleCommand for chart %s", self.chart_id)

            if not self.app_state.has_project:
                self.logger.warning("ExportChartBundleCommand.execute: no project is loaded")
                self.ui_controller.show_warning_message(
                    "Export Chart Bundle",
                    "Please open or create a project first."
                )
                return CommandResult.FAILURE

            self.project = get_current_project(self.app_context)
            if not self.project:
                self.logger.warning("ExportChartBundleCommand.execute: has_project is True but current_project is None")
                return CommandResult.FAILURE

            found_item = self.project.find_item(self.chart_id)
            if not found_item or not isinstance(found_item, Chart):
                self.logger.warning("ExportChartBundleCommand.execute: chart '%s' not found", self.chart_id)
                self.ui_controller.show_error_message(
                    "Export Chart Bundle",
                    f"Chart with ID '{self.chart_id}' not found."
                )
                return CommandResult.FAILURE

            self.chart = found_item

            # Prompt for export path if not provided
            if not self.export_path:
                self.export_path = self.ui_controller.show_export_chart_bundle_dialog(self.chart.name)
                if not self.export_path:
                    return CommandResult.FAILURE  # User cancelled

            self.is_exporting = True
            self.ui_controller.show_info_message(
                "Export Starting",
                f"Starting export of chart '{self.chart.name}' bundle to:\n{self.export_path}"
            )

            # Run export task in background thread
            self.task_scheduler.run_task(
                task=self._export_bundle_task,
                task_arguments={},
                on_result=self._on_export_result,
                on_error=self._on_export_error,
                on_finished=self._on_export_finished,
                on_progress=self._on_export_progress,
            )

            return CommandResult.SUCCESS

        except Exception as e:
            error_msg = f"Failed to export chart bundle: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Export Chart Bundle Error", error_msg)
            return CommandResult.FAILURE

    def _export_bundle_task(self, progress_callback: Optional[Callable[[float], None]] = None, **kwargs) -> dict:
        """Export task run in a background thread."""
        try:
            if progress_callback:
                progress_callback(0.1)

            if not self.chart or not self.project or not self.export_path:
                return {"success": False, "error": "Missing chart, project, or export path", "path": None}

            if progress_callback:
                progress_callback(0.3)

            exporter = ChartBundleExporter(self.chart, self.project)
            success = exporter.export(self.export_path)

            if progress_callback:
                progress_callback(1.0)

            if success:
                return {"success": True, "error": None, "path": self.export_path}
            return {"success": False, "error": "ChartBundleExporter encountered an error", "path": None}

        except Exception as e:
            error_msg = f"Error during chart bundle export: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg, "path": None}

    def _on_export_result(self, result: dict):
        """Handle completion of export task."""
        try:
            self.is_exporting = False
            if result.get("success", False):
                chart_name = self.chart.name if self.chart else "Chart"
                self.ui_controller.show_info_message(
                    "Export Successful",
                    f"Chart bundle for '{chart_name}' exported successfully to:\n{result['path']}"
                )
                self.logger.info("Chart bundle export completed successfully: %s", result["path"])
            else:
                error_msg = result.get("error", "Unknown export error")
                self.ui_controller.show_error_message("Export Failed", error_msg)
                self.logger.error("Chart bundle export failed: %s", error_msg)

        except Exception as e:
            self.logger.error("Error handling chart bundle export result: %s", e, exc_info=True)

    def _on_export_error(self, error_info: Tuple[Any, Any, str]):
        """Handle task error."""
        try:
            self.is_exporting = False
            error_type, error_value, _ = error_info
            error_msg = f"Export failed with {error_type.__name__}: {str(error_value)}"
            self.logger.error("Chart bundle export task error: %s", error_msg)
            self.ui_controller.show_error_message("Export Error", error_msg)
        except Exception as e:
            self.logger.error("Error handling export error: %s", e, exc_info=True)

    def _on_export_finished(self):
        """Handle task finish."""
        self.is_exporting = False

    def _on_export_progress(self, progress: float):
        """Handle progress updates."""
        pass

    def undo(self) -> CommandResult:
        """Undo is a no-op for file export."""
        return CommandResult.NOOP

    def redo(self) -> CommandResult:
        """Redo the export operation."""
        if self.export_path and not self.is_exporting:
            self.is_exporting = True
            self.task_scheduler.run_task(
                task=self._export_bundle_task,
                task_arguments={},
                on_result=self._on_export_result,
                on_error=self._on_export_error,
                on_finished=self._on_export_finished,
                on_progress=self._on_export_progress,
            )
            return CommandResult.SUCCESS
        return CommandResult.FAILURE

    @override
    def cleanup(self) -> None:
        """Release project/chart references."""
        self.project = None
        self.chart = None
