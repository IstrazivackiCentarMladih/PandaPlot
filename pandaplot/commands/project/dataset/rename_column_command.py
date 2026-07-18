"""Command for renaming a dataset column, cascading to chart/fit references."""

from typing import List, Optional, override

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events.event_data import DatasetColumnRenamedData
from pandaplot.models.events.event_types import ChartEvents, DatasetOperationEvents
from pandaplot.models.project.items import Chart, Dataset
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState


class RenameColumnCommand(Command):
    """Rename a dataset column and update chart/fit references to it.

    The DataFrame rename and the reference cascade are one undoable step;
    series/fit labels are user-editable text and are never modified.
    """

    def __init__(self, app_context: AppContext, dataset_id: str,
                 column_index: int, new_name: str):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()

        self.dataset_id = dataset_id
        self.column_index = column_index
        self.new_name = new_name.strip()
        self.old_name: Optional[str] = None
        self.dataset: Optional[Dataset] = None
        self._applied: bool = False

    @override
    def execute(self) -> bool:
        try:
            if not self.app_state.has_project or not self.app_state.current_project:
                self.ui_controller.show_warning_message(
                    "Rename Column", "Please open or create a project first.")
                return False
            project = self.app_state.current_project

            found_item = project.find_item(self.dataset_id)
            if not isinstance(found_item, Dataset) or found_item.data is None:
                self.ui_controller.show_error_message(
                    "Rename Column", f"Dataset with ID '{self.dataset_id}' not found.")
                return False
            self.dataset = found_item

            columns = list(self.dataset.data.columns)
            if not (0 <= self.column_index < len(columns)):
                self.ui_controller.show_error_message(
                    "Rename Column", f"Column index {self.column_index} is out of range.")
                return False

            self.old_name = columns[self.column_index]
            if not self.new_name:
                self.ui_controller.show_error_message(
                    "Rename Column", "Column name cannot be empty.")
                return False
            if self.new_name == self.old_name:
                return False
            if self.new_name in columns:
                self.ui_controller.show_error_message(
                    "Rename Column",
                    f"A column named '{self.new_name}' already exists in this dataset.")
                return False

            self._apply_rename(self.old_name, self.new_name)
            self._applied = True
            return True

        except Exception as e:
            error_msg = f"Failed to rename column: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Rename Column Error", error_msg)
            return False

    def _apply_rename(self, from_name: str, to_name: str) -> None:
        """Rename the DataFrame column, cascade references, emit events."""
        if self.dataset is None or self.dataset.data is None:
            return
        self.dataset.data.rename(columns={from_name: to_name}, inplace=True)
        self.dataset.update_modified_time()

        affected_charts = self._update_chart_references(from_name, to_name)

        self.app_context.event_bus.emit(
            DatasetOperationEvents.DATASET_COLUMN_RENAMED,
            DatasetColumnRenamedData(
                dataset_id=self.dataset_id,
                column_index=self.column_index,
                old_name=from_name,
                new_name=to_name,
            ).to_dict())
        for chart in affected_charts:
            self.app_context.event_bus.emit(ChartEvents.CHART_UPDATED, {
                "chart_id": chart.id,
                "chart": chart,
            })

    def _update_chart_references(self, from_name: str, to_name: str) -> List[Chart]:
        """Point series/fits of this dataset at the new name; return affected charts."""
        project = self.app_state.current_project
        if not project:
            return []
        affected: List[Chart] = []
        for item in project.get_all_items():
            if not isinstance(item, Chart):
                continue
            changed = False
            for series in item.data_series:
                if series.dataset_id != self.dataset_id:
                    continue
                if series.x_column == from_name:
                    series.x_column = to_name
                    changed = True
                if series.y_column == from_name:
                    series.y_column = to_name
                    changed = True
            for fit in item.fit_data:
                if fit.source_dataset_id != self.dataset_id:
                    continue
                if fit.source_x_column == from_name:
                    fit.source_x_column = to_name
                    changed = True
                if fit.source_y_column == from_name:
                    fit.source_y_column = to_name
                    changed = True
            if changed:
                item.update_modified_time()
                affected.append(item)
        return affected

    @override
    def undo(self):
        """Rename back and restore references (same walk, names swapped)."""
        if self._applied and self.old_name is not None:
            self._apply_rename(self.new_name, self.old_name)

    @override
    def redo(self):
        """Re-apply the rename and reference cascade."""
        if self._applied and self.old_name is not None:
            self._apply_rename(self.old_name, self.new_name)
