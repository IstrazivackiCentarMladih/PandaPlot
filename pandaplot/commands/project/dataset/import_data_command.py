import os
import uuid
from typing import Any, Callable, Optional, Tuple, override

import pandas as pd

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events.event_types import DatasetEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.state import AppContext, AppState
from pandaplot.services.qtasks import TaskScheduler

# Delimited-text extensions handled via pandas' CSV reader.
CSV_EXTENSIONS = {".csv", ".txt", ".tsv"}
# Excel workbook extensions. Only the first sheet is imported today; see
# _read_excel_file() for how multi-sheet support can be added later.
EXCEL_EXTENSIONS = {".xlsx", ".xls"}
SUPPORTED_EXTENSIONS = CSV_EXTENSIONS | EXCEL_EXTENSIONS


class ImportDataCommand(Command):
    """
    Command to import a single data file (CSV/TSV or single-sheet Excel
    workbook) as a dataset in the project, via one unified "Import Data" action.

    Supporting a new file format only requires adding a `_read_*_file` method
    and registering its extensions in the sets above.
    """

    def __init__(self, app_context: AppContext, folder_id: Optional[str] = None):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()
        self.task_scheduler: TaskScheduler = app_context.get_task_scheduler()

        self.folder_id = folder_id
        self.file_path = None  # Path to the data file, can be set later
        self.dataset_name = None

        # Store state for undo
        self.dataset_id = None
        self.imported_data = None
        self.project = None

        # Task state
        self.is_importing = False

    @override
    def execute(self) -> bool:
        """Execute the import data command."""
        try:
            self.logger.info("Executing ImportDataCommand")

            # Prevent concurrent imports
            if self.is_importing:
                self.logger.warning("Import operation already in progress")
                self.ui_controller.show_info_message("Import In Progress", "A data import is already in progress.")
                return False

            # Check if we have a project loaded
            if not self.app_state.has_project:
                self.ui_controller.show_warning_message("Import Data", "Please open or create a project first.")
                return False

            self.project = self.app_state.current_project
            if not self.project:
                return False

            # Get file path
            if not self.file_path:
                self.file_path = self.ui_controller.show_import_data_dialog()
            if not self.file_path:
                return False  # User cancelled

            # Preflight check: validate file exists before starting import
            if not os.path.exists(self.file_path):
                error_msg = f"Selected file does not exist: {self.file_path}"
                self.ui_controller.show_error_message("Import Data Error", error_msg)
                self.logger.error(error_msg)
                return False

            # Preflight check: validate the file extension is supported
            extension = os.path.splitext(self.file_path)[1].lower()
            if extension not in SUPPORTED_EXTENSIONS:
                supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
                error_msg = f"Unsupported file type '{extension}'. Supported types: {supported}"
                self.ui_controller.show_error_message("Import Data Error", error_msg)
                self.logger.error(error_msg)
                return False

            # Get dataset name if not provided
            self.dataset_name = os.path.splitext(os.path.basename(self.file_path))[0]

            # Show starting message
            self.ui_controller.show_info_message("Import Starting", f"Starting to import file:\n{self.file_path}")

            # Start background import operation
            self.is_importing = True

            # Run import in background thread
            self.task_scheduler.run_task(
                task=self._import_data_task,
                task_arguments={},
                on_result=self._on_import_result,
                on_error=self._on_import_error,
                on_finished=self._on_import_finished,
                on_progress=self._on_import_progress,
            )

            return True  # Command initiated successfully

        except Exception as e:
            error_msg = f"Failed to initiate data import: {e}"
            self.logger.error("ImportDataCommand Error: %s", error_msg, exc_info=True)
            self.ui_controller.show_error_message("Import Data Error", error_msg)
            self.is_importing = False  # Reset flag on error
            return False

    def _read_csv_file(self, file_path: str) -> pd.DataFrame:
        """
        Read a delimited-text file, falling back through common encodings if
        the file isn't UTF-8 (e.g. files saved by Excel on Windows).
        """
        last_error: Optional[UnicodeDecodeError] = None
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError as e:
                last_error = e
                continue
        assert last_error is not None
        raise last_error

    def _read_excel_file(self, file_path: str) -> pd.DataFrame:
        """
        Read a single-sheet Excel workbook.

        Only the first sheet is imported for now. To add multi-sheet import
        later: use `pd.ExcelFile(file_path).sheet_names` to list sheets and let
        the caller choose which one(s) to import (e.g. one Dataset per sheet).
        """
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        if not sheet_names:
            raise ValueError("The Excel workbook contains no sheets.")

        if len(sheet_names) > 1:
            self.logger.info(
                "Excel file '%s' has %d sheets; importing only the first sheet '%s'.",
                file_path,
                len(sheet_names),
                sheet_names[0],
            )

        return excel_file.parse(sheet_name=0)

    def _read_data_file(self, file_path: str) -> pd.DataFrame:
        """Dispatch to the reader for the file's extension."""
        extension = os.path.splitext(file_path)[1].lower()
        if extension in CSV_EXTENSIONS:
            return self._read_csv_file(file_path)
        elif extension in EXCEL_EXTENSIONS:
            return self._read_excel_file(file_path)
        else:
            raise ValueError(f"Unsupported file type '{extension}'")

    def _import_data_task(self, progress_callback: Callable[[float], None], **kwargs) -> dict:
        """
        Import task function to be run in a background thread.
        Returns a dictionary with success status and any error message.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            dict: {'success': bool, 'error': str or None, 'dataset_id': str or None, 'dataset': Dataset or None}
        """
        self.logger.debug("Starting data import task")
        try:
            if progress_callback:
                progress_callback(0.1)  # Starting import

            if not self.file_path or not os.path.exists(self.file_path):
                return {"success": False, "error": f"File not found: {self.file_path}", "dataset_id": None, "dataset": None}

            if progress_callback:
                progress_callback(0.2)  # File validation complete

            # Read the data file
            try:
                df = self._read_data_file(self.file_path)
                if df.empty:
                    return {"success": False, "error": "The selected file is empty.", "dataset_id": None, "dataset": None}

                # Note: Don't assign to self.imported_data here to avoid thread safety issues
                # The DataFrame will be returned in the result payload

            except Exception as e:
                return {"success": False, "error": f"Failed to read file: {str(e)}", "dataset_id": None, "dataset": None}

            if progress_callback:
                progress_callback(0.6)  # File read successfully

            # Get dataset name if not provided
            if not self.dataset_name:
                self.dataset_name = os.path.splitext(os.path.basename(self.file_path))[0]

            # Create dataset ID
            self.dataset_id = str(uuid.uuid4())

            if progress_callback:
                progress_callback(0.8)  # Dataset metadata prepared

            # Create dataset object
            dataset = Dataset(id=self.dataset_id, name=self.dataset_name, data=df, source_file=self.file_path)

            if progress_callback:
                progress_callback(0.9)  # Dataset object created

            self.logger.info(
                "Successfully imported '%s' from '%s' with ID '%s' (rows=%d, cols=%d)",
                self.dataset_name,
                self.file_path,
                self.dataset_id,
                df.shape[0],
                df.shape[1],
            )

            if progress_callback:
                progress_callback(1.0)  # Finished

            return {
                "success": True,
                "error": None,
                "dataset_id": self.dataset_id,
                "dataset": dataset,
                "dataset_name": self.dataset_name,
                "file_path": self.file_path,
                "rows": df.shape[0],
                "cols": df.shape[1],
                "imported_data": df,  # Return DataFrame in result payload
            }

        except Exception as e:
            error_msg = f"Error during data import: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg, "dataset_id": None, "dataset": None}

    def _on_import_result(self, result: dict):
        """Handle successful completion of import task."""
        try:
            self.is_importing = False

            if result.get("success", False):
                dataset = result.get("dataset")
                dataset_id = result.get("dataset_id")
                dataset_name = result.get("dataset_name")
                file_path = result.get("file_path")
                rows = result.get("rows", 0)
                cols = result.get("cols", 0)
                imported_data = result.get("imported_data")

                # Assign imported_data on main thread to avoid thread safety issues
                self.imported_data = imported_data

                if dataset and self.project:
                    # Verify that we still have a project and it's the same as when we started the import
                    if not self.app_state.has_project:
                        # Project was closed during import - abort with user message
                        self.logger.warning("Project was closed during import - aborting import operation")
                        self.ui_controller.show_warning_message(
                            "Import Cancelled",
                            f"The project was closed during import of '{dataset_name}'. "
                            "The import has been cancelled."
                        )
                        return

                    current_project = self.app_state.current_project
                    if current_project != self.project:
                        # Project changed during import - abort with user message
                        self.logger.warning("Project changed during import - aborting import operation")
                        self.ui_controller.show_warning_message(
                            "Import Cancelled",
                            f"The project was changed during import of '{dataset_name}'. "
                            "The import has been cancelled to prevent data inconsistency."
                        )
                        return

                    # Add dataset to project
                    self.project.add_item(dataset, parent_id=self.folder_id)

                    # Emit event
                    # TODO: migrate to item created and create data class
                    self.app_state.event_bus.emit(
                        DatasetEvents.DATASET_CREATED,
                        {
                            "project": self.project,
                            "dataset_id": dataset_id,
                            "dataset_name": dataset_name,
                            "folder_id": self.folder_id,
                            "dataset_data": dataset.data,
                            "file_path": file_path,
                            "dataframe": imported_data,  # Use DataFrame from result payload
                        },
                    )

                    self.logger.info("Dataset '%s' successfully added to project", dataset_name)

                    # Show success message to user
                    self.ui_controller.show_info_message("Import Data", f"Successfully imported '{dataset_name}'\nRows: {rows}, Columns: {cols}")
                else:
                    error_msg = "Missing dataset or project in import result"
                    self.ui_controller.show_error_message("Import Failed", error_msg)
                    self.logger.error(error_msg)
            else:
                error_msg = result.get("error", "Unknown import error")
                self.ui_controller.show_error_message("Import Failed", error_msg)
                self.logger.error(f"Import failed: {error_msg}")

        except Exception as e:
            self.logger.error(f"Error handling import result: {e}", exc_info=True)
            self.ui_controller.show_error_message("Import Error", f"Error processing import result: {str(e)}")

    def _on_import_error(self, error_info: Tuple[Any, Any, str]):
        """Handle error during import task."""
        try:
            self.is_importing = False
            error_type, error_value, error_traceback = error_info
            error_msg = f"Import failed with {error_type.__name__}: {str(error_value)}"

            self.logger.error(f"Import task error: {error_msg}")
            self.logger.error(f"Traceback: {error_traceback}")

            self.ui_controller.show_error_message("Import Data Error", error_msg)

        except Exception as e:
            self.logger.error(f"Error handling import error: {e}", exc_info=True)

    def _on_import_finished(self):
        """Handle completion of import task (success or failure)."""
        try:
            self.is_importing = False
            self.logger.info("Import task finished")

        except Exception as e:
            self.logger.error(f"Error in import finished handler: {e}", exc_info=True)

    def _on_import_progress(self, progress: float):
        """Handle progress updates from import task."""
        try:
            # Log the progress for now - could update a progress bar if UI supports it
            if progress <= 1.0:
                percentage = int(progress * 100)
                self.logger.debug(f"Import progress: {percentage}%")

        except Exception as e:
            self.logger.error(f"Error handling import progress: {e}", exc_info=True)

    def undo(self):
        """Undo the import data command."""
        try:
            if self.dataset_id and self.app_state.has_project:
                project = self.app_state.current_project
                if project:
                    dataset = project.find_item(self.dataset_id)
                    if dataset:
                        project.remove_item(dataset)

                    # Emit event
                    self.app_state.event_bus.emit(
                        DatasetEvents.DATASET_DELETED, {"project": project, "dataset_id": self.dataset_id, "dataset_data": self.imported_data}
                    )

                    self.logger.info("Undone import of dataset '%s'", self.dataset_id)

        except Exception as e:
            error_msg = f"Failed to undo data import: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Undo Error", error_msg)

    def redo(self):
        """Redo the import data command."""
        try:
            if not self.is_importing:
                if self.dataset_id and self.imported_data is not None and self.app_state.has_project:
                    # We have cached data, could re-add directly or re-execute
                    # For now, re-execute to maintain consistency
                    return self.execute()
                else:
                    self.logger.warning("Cannot redo: no cached import data available")
                    return False
            else:
                self.logger.warning("Cannot redo import command while import is in progress")
                return False
        except Exception as e:
            error_msg = f"Failed to redo data import: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Redo Error", error_msg)
            return False
