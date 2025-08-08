"""
Command for creating chart items from datasets.
"""

from pandaplot.commands.base_command import Command
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState
from pandaplot.gui.controllers.ui_controller import UIController
from typing import Optional


class CreateChartCommand(Command):
    """
    Command to create a new chart item from a dataset.
    """
    
    def __init__(self, app_context: AppContext):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()
        
        self.created_chart_id = None
        self.dataset_id = None
        self.chart_name = None
        self.parent_id = None
    
    def execute(self, dataset_id: str, chart_name: Optional[str] = None, parent_id: Optional[str] = None, **kwargs):
        """
        Execute the create chart command.
        
        Args:
            dataset_id: ID of the dataset to create chart from
            chart_name: Name for the new chart (defaults to "Chart from {dataset_name}")
            parent_id: Parent folder ID (optional)
        """
        try:
            app_state = self.app_context.get_app_state()
            
            if not app_state.has_project:
                error_msg = "No project is currently loaded"
                print(f"CreateChartCommand Error: {error_msg}")
                self.ui_controller.show_error_message("Create Chart Error", error_msg)
                return None
            
            project = app_state.current_project
            
            # Verify dataset exists
            project = app_state.current_project
            if not project:
                error_msg = "No project is currently loaded"
                print(f"CreateChartCommand Error: {error_msg}")
                self.ui_controller.show_error_message("Create Chart Error", error_msg)
                return None

            dataset = project.find_item(dataset_id)
            if not dataset:
                error_msg = f"Dataset '{dataset_id}' not found"
                print(f"CreateChartCommand Error: {error_msg}")
                self.ui_controller.show_error_message("Create Chart Error", error_msg)
                return None
            
            # Store parameters for undo
            self.dataset_id = dataset_id
            self.parent_id = parent_id
            
            # Generate chart name if not provided
            if not chart_name:
                dataset_name = getattr(dataset, 'name', 'Dataset')
                chart_name = f"Chart from {dataset_name}"
            
            self.chart_name = chart_name
            
            # Create chart using chart manager
            
            chart = Chart(
                name=chart_name,
                chart_type="line"
            )
            
            # Add a default data series using the dataset
            # We'll set up basic defaults for x/y columns that can be configured later
            dataset_obj = project.find_item(dataset_id)
            from pandaplot.models.project.items.dataset import Dataset
            if isinstance(dataset_obj, Dataset) and dataset_obj.data is not None:
                    columns = list(dataset_obj.data.columns)
                    if len(columns) >= 2:
                        # Use first column as X and second as Y by default
                        chart.add_data_series(
                            dataset_id=dataset_id,
                            x_column=columns[0],
                            y_column=columns[1],
                            label=f"{dataset_obj.name}:{columns[1]}"
                        )
                    elif len(columns) == 1:
                        # Use index as X and only column as Y
                        chart.add_data_series(
                            dataset_id=dataset_id,
                            x_column="",  # Empty means use index
                            y_column=columns[0],
                            label=f"{dataset_obj.name}:{columns[0]}"
                        )
            
            project.add_item(chart, parent_id=self.parent_id)

            self.created_chart_id = chart.id
            
            # Publish chart creation event
            from pandaplot.models.events.event_types import ChartEvents
            event_bus = self.app_context.event_bus
            event_bus.emit(ChartEvents.CHART_CREATED, {
                'chart_id': chart.id,
                'chart_name': chart.name,
                'dataset_id': self.dataset_id,
                'parent_id': self.parent_id
            })
            
            return chart.id
            
        except Exception as e:
            error_msg = f"Failed to create chart from dataset: {str(e)}"
            print(f"CreateChartCommand Error: {error_msg}")
            self.ui_controller.show_error_message("Create Chart Error", error_msg)
            return None
    
    def undo(self):
        """Undo the chart creation."""
        if not self.created_chart_id:
            return
            
        try:
            app_state = self.app_context.get_app_state()
            
            if not app_state.has_project:
                return
            
            # TODO: project doesn't have to be current_project, it can be any project
            # that has the chart, so we should find it by ID
            project = app_state.current_project
            if not project:
                return

            project.remove_item_by_id(self.created_chart_id)
            
            print(f"CreateChartCommand: Undid creation of chart '{self.created_chart_id}'")
            
        except Exception as e:
            print(f"CreateChartCommand Undo Error: {str(e)}")
    
    def redo(self):
        """Redo the create chart command."""
        if self.dataset_id and self.chart_name:
            self.execute(self.dataset_id, self.chart_name, self.parent_id)
        
    def can_undo(self) -> bool:
        """Check if this command can be undone."""
        return self.created_chart_id is not None
    
    def get_description(self) -> str:
        """Get description of this command for UI purposes."""
        if self.chart_name:
            return f"Create chart '{self.chart_name}'"
        return "Create chart from dataset"
