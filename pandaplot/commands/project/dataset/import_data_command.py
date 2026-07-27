import os
import uuid
from typing import Any, Callable, List, Optional, Tuple, override

import pandas as pd
from PySide6.QtWidgets import QDialog

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.gui.dialogs.select_sheets_dialog import SelectSheetsDialog
from pandaplot.models.events.event_types import DatasetEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.state import AppContext, AppState
from pandaplot.services.data_import import ImportOptions, data_importer
from pandaplot.services.qtasks import TaskScheduler

# Delimited-text extensions handled via pandas' CSV reader.
CSV_EXTENSIONS = {".csv", ".txt", ".tsv"}
# Excel workbook extensions. Every sheet the user selects is imported as its
# own Dataset - see execute()'s sheet-selection step and _import_data_task().
EXCEL_EXTENSIONS = {".xlsx", ".xls"}
SUPPORTED_EXTENSIONS = CSV_EXTENSIONS | EXCEL_EXTENSIONS


class ImportDataCommand(Command):
    """
    Command to import a data file (CSV/TSV, or one or more sheets of an Excel
    workbook) as dataset(s) in the project, via one unified "Import Data" action.

    The command drives the interactive import wizard
    (:class:`ImportWizardDialog`), which handles format detection, parse
    options, and preview. Once the user confirms, the full file is read on a
    background thread using the chosen :class:`ImportOptions`.
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
        # Parse options chosen in the wizard; drives the background read.
        self.import_options: Optional[ImportOptions] = None
        # Excel sheets to import, in workbook order. None until execute() has
        # resolved it (auto-picked for a single-sheet workbook, or chosen by
        # the user via SelectSheetsDialog for a multi-sheet one). Not used
        # for CSV/TSV files.
        self.selected_sheets: Optional[List[str]] = None

        # Store state for undo
        self.dataset_ids: List[str] = []
        self.imported_datasets: List[Dataset] = []
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

            # Collect the file, parse options, and dataset name via the wizard.
            if not self._collect_import_settings():
                return False  # User cancelled

            # Preflight check: validate file still exists before starting import
            if not self.file_path or not os.path.exists(self.file_path):
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

            # For Excel workbooks, resolve which sheet(s) to import: auto-pick
            # the only one for a single-sheet workbook, otherwise let the user
            # choose. Cached in self.selected_sheets so redo() re-executing
            # doesn't prompt again.
            if extension in EXCEL_EXTENSIONS and self.selected_sheets is None:
                try:
                    sheet_names = pd.ExcelFile(self.file_path).sheet_names
                except Exception as e:
                    error_msg = f"Failed to read Excel workbook: {e}"
                    self.ui_controller.show_error_message("Import Data Error", error_msg)
                    self.logger.error(error_msg)
                    return False

                if not sheet_names:
                    error_msg = "The Excel workbook contains no sheets."
                    self.ui_controller.show_error_message("Import Data Error", error_msg)
                    self.logger.error(error_msg)
                    return False

                if len(sheet_names) == 1:
                    self.selected_sheets = list(sheet_names)
                else:
                    dialog = SelectSheetsDialog(self.app_context, list(sheet_names), parent=self.ui_controller.parent_widget)
                    if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_sheets:
                        self.logger.info("Sheet selection cancelled by user")
                        return False
                    self.selected_sheets = dialog.selected_sheets

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

    def _collect_import_settings(self) -> bool:
        """
        Show the import wizard and capture the chosen file, parse options, and
        dataset name. Returns False if the user cancels.

        When `self.file_path` is already set (e.g. programmatic import), it
        seeds the wizard so tests and callers can pre-select a file.
        """
        # Imported lazily so the command layer stays free of Qt at import time.
        from PySide6.QtWidgets import QDialog

        from pandaplot.gui.dialogs.import_wizard_dialog import ImportWizardDialog

        dialog = ImportWizardDialog(
            self.app_context,
            parent=self.ui_controller.parent_widget,
            initial_file_path=self.file_path,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.logger.info("Import wizard cancelled by user")
            return False

        self.file_path = dialog.get_file_path()
        self.import_options = dialog.get_import_options()
        self.dataset_name = dialog.get_dataset_name()
        return True

    def _read_data_file(self, file_path: str) -> pd.DataFrame:
        """Read the file with the parse options chosen in the wizard."""
        options = self.import_options or data_importer.default_options(file_path)
        return data_importer.read_dataframe(file_path, options)
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

    def _read_excel_sheets(self, file_path: str, sheet_names: List[str]) -> List[Tuple[str, pd.DataFrame]]:
        """Read each requested sheet, returning (dataset_name, dataframe) pairs.

        A single selected sheet is named after the file (matching the
        existing CSV/single-sheet behavior); multiple selected sheets are
        each named "<file> - <sheet>" so they don't collide with each other
        or with datasets imported from other files.
        """
        excel_file = pd.ExcelFile(file_path)
        base_name = self.dataset_name or os.path.splitext(os.path.basename(file_path))[0]

        results = []
        for sheet_name in sheet_names:
            df = excel_file.parse(sheet_name=sheet_name)
            name = base_name if len(sheet_names) == 1 else f"{base_name} - {sheet_name}"
            results.append((name, df))
        return results

    def _import_data_task(self, progress_callback: Callable[[float], None], **kwargs) -> dict:
        """
        Import task function to be run in a background thread.
        Returns a dictionary with success status and any error message.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            dict: {'success': bool, 'error': str or None, 'datasets': List[Dataset], 'file_path': str or None}
        """
        self.logger.debug("Starting data import task")
        try:
            if progress_callback:
                progress_callback(0.1)  # Starting import

            if not self.file_path or not os.path.exists(self.file_path):
                return {"success": False, "error": f"File not found: {self.file_path}", "datasets": []}

            if progress_callback:
                progress_callback(0.2)  # File validation complete

            extension = os.path.splitext(self.file_path)[1].lower()

            # Read the data file into one or more (name, dataframe) pairs
            try:
                if extension in EXCEL_EXTENSIONS:
                    sheet_names = self.selected_sheets or [0]
                    frames = self._read_excel_sheets(self.file_path, sheet_names)
                else:
                    df = self._read_csv_file(self.file_path)
                    name = self.dataset_name or os.path.splitext(os.path.basename(self.file_path))[0]
                    frames = [(name, df)]
            except Exception as e:
                return {"success": False, "error": f"Failed to read file: {str(e)}", "datasets": []}

            if progress_callback:
                progress_callback(0.6)  # File read successfully

            # Drop empty sheets rather than failing the whole import over one blank tab
            non_empty = [(name, df) for name, df in frames if not df.empty]
            if not non_empty:
                error_msg = "The selected file is empty." if len(frames) == 1 else "The selected sheet(s) contain no data."
                return {"success": False, "error": error_msg, "datasets": []}

            datasets = []
            for name, df in non_empty:
                dataset = Dataset(id=str(uuid.uuid4()), name=name, data=df, source_file=self.file_path)
                datasets.append(dataset)

            if progress_callback:
                progress_callback(0.9)  # Dataset objects created

            self.logger.info(
                "Successfully imported %d dataset(s) from '%s' (%s)",
                len(datasets),
                self.file_path,
                ", ".join(f"{d.name} (rows={d.data.shape[0]}, cols={d.data.shape[1]})" for d in datasets),
            )

            if progress_callback:
                progress_callback(1.0)  # Finished

            return {
                "success": True,
                "error": None,
                "datasets": datasets,
                "file_path": self.file_path,
            }

        except Exception as e:
            error_msg = f"Error during data import: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg, "datasets": []}

    def _on_import_result(self, result: dict):
        """Handle successful completion of import task."""
        try:
            self.is_importing = False

            if result.get("success", False):
                datasets: List[Dataset] = result.get("datasets") or []
                file_path = result.get("file_path")

                # Assign on main thread to avoid thread safety issues
                self.imported_datasets = datasets

                if datasets and self.project:
                    # Verify that we still have a project and it's the same as when we started the import
                    if not self.app_state.has_project:
                        # Project was closed during import - abort with user message
                        self.logger.warning("Project was closed during import - aborting import operation")
                        self.ui_controller.show_warning_message(
                            "Import Cancelled",
                            "The project was closed during import. The import has been cancelled."
                        )
                        return

                    current_project = self.app_state.current_project
                    if current_project != self.project:
                        # Project changed during import - abort with user message
                        self.logger.warning("Project changed during import - aborting import operation")
                        self.ui_controller.show_warning_message(
                            "Import Cancelled",
                            "The project was changed during import. The import has been cancelled to prevent data inconsistency."
                        )
                        return

                    # Add each dataset to the project
                    for dataset in datasets:
                        self.project.add_item(dataset, parent_id=self.folder_id)
                        self.dataset_ids.append(dataset.id)

                        # Emit event
                        # TODO: migrate to item created and create data class
                        self.app_state.event_bus.emit(
                            DatasetEvents.DATASET_CREATED,
                            {
                                "project": self.project,
                                "dataset_id": dataset.id,
                                "dataset_name": dataset.name,
                                "folder_id": self.folder_id,
                                "dataset_data": dataset.data,
                                "file_path": file_path,
                                "dataframe": dataset.data,
                            },
                        )

                    self.logger.info("%d dataset(s) successfully added to project", len(datasets))

                    # Show success message to user
                    if len(datasets) == 1:
                        d = datasets[0]
                        self.ui_controller.show_info_message(
                            "Import Data", f"Successfully imported '{d.name}'\nRows: {d.data.shape[0]}, Columns: {d.data.shape[1]}"
                        )
                    else:
                        names = "\n".join(f"- {d.name} ({d.data.shape[0]} rows, {d.data.shape[1]} cols)" for d in datasets)
                        self.ui_controller.show_info_message(
                            "Import Data", f"Successfully imported {len(datasets)} sheets as datasets:\n{names}"
                        )
                else:
                    error_msg = "Missing datasets or project in import result"
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
            if self.dataset_ids and self.app_state.has_project:
                project = self.app_state.current_project
                if project:
                    for dataset_id in self.dataset_ids:
                        dataset = project.find_item(dataset_id)
                        if dataset:
                            project.remove_item(dataset)

                        # Emit event
                        self.app_state.event_bus.emit(
                            DatasetEvents.DATASET_DELETED, {"project": project, "dataset_id": dataset_id, "dataset_data": None}
                        )

                    self.logger.info("Undone import of %d dataset(s)", len(self.dataset_ids))

        except Exception as e:
            error_msg = f"Failed to undo data import: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Undo Error", error_msg)

    def redo(self):
        """
        Redo the import by re-adding the cached dataset directly.

        Unlike the first run, redo does not reopen the wizard: the file was
        already parsed and the resulting data is cached, so we simply re-insert
        the dataset and re-emit the creation event.
        """
        try:
            if self.is_importing:
            if not self.is_importing:
                if self.dataset_ids and self.imported_datasets and self.app_state.has_project:
                    # We have cached data, could re-add directly or re-execute
                    # For now, re-execute to maintain consistency
                    self.dataset_ids = []
                    return self.execute()
                else:
                    self.logger.warning("Cannot redo: no cached import data available")
                    return False
            else:
                self.logger.warning("Cannot redo import command while import is in progress")
                return False

            if not (self.dataset_id and self.imported_data is not None and self.app_state.has_project):
                self.logger.warning("Cannot redo: no cached import data available")
                return False

            project = self.app_state.current_project
            if not project:
                return False

            dataset = Dataset(id=self.dataset_id, name=self.dataset_name, data=self.imported_data, source_file=self.file_path)
            project.add_item(dataset, parent_id=self.folder_id)

            self.app_state.event_bus.emit(
                DatasetEvents.DATASET_CREATED,
                {
                    "project": project,
                    "dataset_id": self.dataset_id,
                    "dataset_name": self.dataset_name,
                    "folder_id": self.folder_id,
                    "dataset_data": dataset.data,
                    "file_path": self.file_path,
                    "dataframe": self.imported_data,
                },
            )

            self.logger.info("Redone import of dataset '%s'", self.dataset_id)
            return True
        except Exception as e:
            error_msg = f"Failed to redo data import: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Redo Error", error_msg)
            return False
