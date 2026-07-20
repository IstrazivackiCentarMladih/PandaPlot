from typing import List, Tuple, Union, override

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events.event_data import DatasetColumnsAddedData, DatasetColumnsRemovedData
from pandaplot.models.events.event_types import ChartEvents, DatasetOperationEvents
from pandaplot.models.project.items import Chart
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState


class DeleteColumnsCommand(Command):
    """
    Command to delete multiple columns from an existing dataset.
    Supports both column positions and column names for backward compatibility.
    """

    def __init__(self, app_context: AppContext, dataset_id: str, 
                 column_specs: Union[List[int], List[str]]):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()
        
        self.dataset_id = dataset_id
        self.column_specs = column_specs
        
        # These will be populated in execute() after we have access to the dataset
        self.column_names = []
        self.column_positions = []
        
        # Store state for undo
        self.original_data = None
        self.deleted_columns_data = None
        self.project = None
        self.dataset = None

        # chart_id -> {"series": [(index, DataSeries)], "fits": [(index, FitData)]}
        # populated when columns being deleted are referenced by chart series/fits
        self.removed_chart_refs = {}

    @override
    def execute(self) -> bool:
        """Execute the delete columns command."""
        try:
            self.logger.info(f"Executing DeleteColumnsCommand for {len(self.column_specs)} column specifications")
            
            # Validate input
            if not self.column_specs:
                self.ui_controller.show_warning_message(
                    "Delete Columns", 
                    "No columns specified for deletion."
                )
                return False
            
            # Check if we have a project loaded
            if not self.app_state.has_project:
                self.ui_controller.show_warning_message(
                    "Delete Columns", 
                    "Please open or create a project first."
                )
                return False
                
            self.project = self.app_state.current_project
            if not self.project:
                return False
            
            # Find the dataset
            found_item = self.project.find_item(self.dataset_id)
            if not found_item:
                self.ui_controller.show_error_message(
                    "Delete Columns", 
                    f"Dataset with ID '{self.dataset_id}' not found."
                )
                return False
            
            if not isinstance(found_item, Dataset):
                self.ui_controller.show_error_message(
                    "Delete Columns", 
                    "Selected item is not a dataset."
                )
                return False
                
            self.dataset = found_item
            
            # Get current data
            if self.dataset.data is None or self.dataset.data.empty:
                self.ui_controller.show_warning_message(
                    "Delete Columns", 
                    "Cannot delete columns from empty dataset."
                )
                return False
            
            # Resolve column names and positions based on input type
            self._resolve_columns()
            
            # Validate resolved columns
            if not self.column_names:
                self.ui_controller.show_warning_message(
                    "Delete Columns", 
                    "No valid columns found for deletion."
                )
                return False
            
            # Check if all resolved columns exist
            existing_columns = set(self.dataset.data.columns)
            missing_columns = [col for col in self.column_names if col not in existing_columns]
            if missing_columns:
                self.ui_controller.show_error_message(
                    "Delete Columns", 
                    f"The following columns do not exist: {', '.join(missing_columns)}"
                )
                return False
            
            # Check for duplicate column names
            if len(set(self.column_names)) != len(self.column_names):
                self.ui_controller.show_warning_message(
                    "Delete Columns", 
                    "Duplicate column names found in the deletion list."
                )
                return False
            
            # Check if we're trying to delete all columns
            remaining_columns = len(self.dataset.data.columns) - len(self.column_names)
            if remaining_columns <= 0:
                self.ui_controller.show_error_message(
                    "Delete Columns", 
                    "Cannot delete all columns from dataset. Dataset must have at least one column."
                )
                return False
            
            # Warn if any chart depends on the columns being deleted, since those
            # series/fit curves will be removed from the chart as part of this action
            references = self._find_chart_references(self.column_names)
            if references:
                details = "\n".join(
                    f"{chart.name}: " + ", ".join(
                        ([f"{len(series_idx)} series"] if series_idx else [])
                        + ([f"{len(fit_idx)} fit curve(s)"] if fit_idx else [])
                    )
                    for chart, series_idx, fit_idx in references
                )
                proceed = self.ui_controller.show_confirmation(
                    "Delete Columns",
                    f"{len(self.column_names)} column(s) are used by {len(references)} "
                    "chart(s). Deleting them will remove the dependent series/fit "
                    "curves from those charts. Continue?",
                    details=details
                )
                if not proceed:
                    return False

            # Store original data for undo
            self.original_data = self.dataset.data.copy()

            # Store the deleted columns data for potential restoration
            self.deleted_columns_data = {}
            for col_name in self.column_names:
                self.deleted_columns_data[col_name] = self.dataset.data[col_name].copy()

            self._perform_deletion(references)

            self.logger.info(f"Deleted {len(self.column_names)} columns from dataset '{self.dataset.name}' (ID: {self.dataset_id})")
            return True

        except Exception as e:
            error_msg = f"Failed to delete {len(self.column_specs) if self.column_specs else 0} columns: {str(e)}"
            self.logger.error(error_msg)
            self.ui_controller.show_error_message("Delete Columns Error", error_msg)
            return False

    def _find_chart_references(
        self, column_names: List[str]
    ) -> List[Tuple[Chart, List[int], List[int]]]:
        """Find charts whose series/fits reference this dataset's columns.

        Returns a list of (chart, data_series indices, fit_data indices) for
        every chart with at least one matching reference.
        """
        if not self.project:
            return []
        column_set = set(column_names)
        matches: List[Tuple[Chart, List[int], List[int]]] = []
        for item in self.project.get_all_items():
            if not isinstance(item, Chart):
                continue
            series_idx = [
                i for i, series in enumerate(item.data_series)
                if series.dataset_id == self.dataset_id
                and (series.x_column in column_set or series.y_column in column_set)
            ]
            fit_idx = [
                i for i, fit in enumerate(item.fit_data)
                if fit.source_dataset_id == self.dataset_id
                and (fit.source_x_column in column_set or fit.source_y_column in column_set)
            ]
            if series_idx or fit_idx:
                matches.append((item, series_idx, fit_idx))
        return matches

    def _perform_deletion(self, references: List[Tuple[Chart, List[int], List[int]]]) -> None:
        """Drop the columns from the dataset and remove dependent chart references."""
        # Create new DataFrame with the columns removed
        new_data = self.dataset.data.drop(columns=self.column_names)

        # Update dataset
        self.dataset.set_data(new_data)

        # Emit event
        self.app_state.event_bus.emit(DatasetOperationEvents.DATASET_COLUMN_REMOVED,
                                      DatasetColumnsRemovedData(dataset_id=self.dataset_id, column_positions=self.column_positions).to_dict()
        )

        self.removed_chart_refs = {}
        for chart, series_idx, fit_idx in references:
            removed_series = [(i, chart.data_series[i]) for i in series_idx]
            removed_fits = [(i, chart.fit_data[i]) for i in fit_idx]
            for i in sorted(series_idx, reverse=True):
                del chart.data_series[i]
            for i in sorted(fit_idx, reverse=True):
                del chart.fit_data[i]
            if removed_series or removed_fits:
                chart.update_modified_time()
                self.removed_chart_refs[chart.id] = {
                    "series": removed_series,
                    "fits": removed_fits,
                }
                self.app_state.event_bus.emit(ChartEvents.CHART_UPDATED, {
                    "chart_id": chart.id,
                    "chart": chart,
                })

    def _restore_chart_references(self) -> None:
        """Re-insert chart series/fits removed by _perform_deletion, for undo."""
        if not self.project or not self.removed_chart_refs:
            return
        for chart_id, removed in self.removed_chart_refs.items():
            chart = self.project.find_item(chart_id)
            if not isinstance(chart, Chart):
                continue
            for i, series in sorted(removed["series"], key=lambda pair: pair[0]):
                chart.data_series.insert(i, series)
            for i, fit in sorted(removed["fits"], key=lambda pair: pair[0]):
                chart.fit_data.insert(i, fit)
            if removed["series"] or removed["fits"]:
                chart.update_modified_time()
                self.app_state.event_bus.emit(ChartEvents.CHART_UPDATED, {
                    "chart_id": chart.id,
                    "chart": chart,
                })
        self.removed_chart_refs = {}

    def _resolve_columns(self):
        """
        Resolve column names and positions based on the input specification.
        Supports both column positions (integers) and column names (strings).
        """
        if not self.column_specs or not self.dataset or self.dataset.data is None:
            return
        
        all_columns = list(self.dataset.data.columns)
        self.column_names = []
        self.column_positions = []
        
        for spec in self.column_specs:
            if isinstance(spec, int):
                # Position-based specification
                if 0 <= spec < len(all_columns):
                    column_name = all_columns[spec]
                    self.column_names.append(column_name)
                    self.column_positions.append(spec)
                else:
                    self.logger.warning(f"Column position {spec} is out of range (0-{len(all_columns)-1})")
            elif isinstance(spec, str):
                # Name-based specification (backward compatibility)
                if spec in all_columns:
                    position = all_columns.index(spec)
                    self.column_names.append(spec)
                    self.column_positions.append(position)
                else:
                    self.logger.warning(f"Column '{spec}' not found in dataset")
            else:
                self.logger.warning(f"Invalid column specification: {spec}")

    def undo(self):
        """Undo the delete columns command by restoring the original data and chart refs."""
        try:
            if self.dataset and self.original_data is not None and self.column_positions:
                # Restore original data
                self.dataset.set_data(self.original_data)
                self._restore_chart_references()

                # Emit event
                self.app_state.event_bus.emit(
                    DatasetOperationEvents.DATASET_COLUMN_ADDED,
                    DatasetColumnsAddedData(dataset_id=self.dataset_id, column_positions=self.column_positions).to_dict())

                self.logger.info(f"Undid deleting {len(self.column_names)} columns from dataset '{self.dataset.name}'")
                return True
        except Exception as e:
            self.logger.error(f"DeleteColumnsCommand Undo Error: {e}")
            return False

    def redo(self):
        """Redo the delete columns command using the already-confirmed parameters."""
        try:
            if not (self.dataset and self.original_data is not None and self.column_names):
                return False
            references = self._find_chart_references(self.column_names)
            self._perform_deletion(references)
            self.logger.info(f"Redid deleting {len(self.column_names)} columns from dataset '{self.dataset.name}'")
            return True
        except Exception as e:
            error_msg = f"Failed to redo deleting {len(self.column_names)} columns: {e}"
            self.logger.error(f"DeleteColumnsCommand Redo Error: {error_msg}")
            self.ui_controller.show_error_message("Delete Columns Error", error_msg)
            return False
