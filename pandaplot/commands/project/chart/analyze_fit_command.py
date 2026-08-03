"""
Command for running an analysis (derivative / integral / arc length) on a
fitted curve and storing the result as a new dataset, with undo/redo support.

Fits live on charts as :class:`FitData` (resampled ``x_data``/``y_data``
arrays). This command lets the user run the same calculus operations the
Analysis panel offers for dataset columns on a fitted curve instead, optionally
restricted to an index range (segment) of the curve.
"""

import uuid
from typing import Optional, override

import pandas as pd

from pandaplot.analysis import AnalysisEngine, AnalysisType
from pandaplot.commands.base_command import Command
from pandaplot.models.events.event_types import DatasetEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.state import AppContext, AppState


class AnalyzeFitCommand(Command):
    """Analyze a chart's fitted curve and add the result to the project as a dataset."""

    def __init__(
        self,
        app_context: AppContext,
        chart_id: str,
        fit_index: int,
        analysis_type: AnalysisType,
        start_index: int = 0,
        end_index: int = -1,
        derivative_method: str = "central",
        result_name: Optional[str] = None,
        folder_id: Optional[str] = None,
    ):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()

        self.chart_id = chart_id
        self.fit_index = fit_index
        self.analysis_type = analysis_type
        self.start_index = start_index
        self.end_index = end_index
        self.derivative_method = derivative_method
        self.result_name = result_name
        self.folder_id = folder_id

        # State for undo/redo.
        self.result_dataset_id: Optional[str] = None

    def _get_chart(self) -> Optional[Chart]:
        project = self.app_state.current_project
        if not project:
            return None
        item = project.find_item(self.chart_id)
        return item if isinstance(item, Chart) else None

    def run_analysis(self) -> tuple[pd.DataFrame, str]:
        """Compute the analysis and return (result dataframe, default name).

        Raises ``ValueError`` if the chart/fit is unavailable. Does not touch the
        project, so the UI can call it for a preview.
        """
        chart = self._get_chart()
        if chart is None:
            raise ValueError("Chart is not available.")
        if not (0 <= self.fit_index < len(chart.fit_data)):
            raise ValueError("Selected fit no longer exists.")

        fit = chart.fit_data[self.fit_index]
        x = pd.Series(fit.x_data, dtype="float64")
        y = pd.Series(fit.y_data, dtype="float64")
        if len(x) < 2:
            raise ValueError("Fitted curve has too few points to analyze.")

        x_label = fit.source_x_column or "x"

        if self.analysis_type == AnalysisType.DERIVATIVE:
            result = AnalysisEngine.calculate_derivative(
                x, y, self.derivative_method, self.start_index, self.end_index
            )
            value_label = f"d({fit.label})/d{x_label}"
        elif self.analysis_type == AnalysisType.INTEGRAL:
            result = AnalysisEngine.calculate_integral(x, y, self.start_index, self.end_index)
            value_label = f"∫ {fit.label} d{x_label}"
        elif self.analysis_type == AnalysisType.ARC_LENGTH:
            result = AnalysisEngine.calculate_arc_length(x, y, self.start_index, self.end_index)
            value_label = f"arc length of {fit.label}"
        else:
            raise ValueError(f"Unsupported analysis for a fitted curve: {self.analysis_type}")

        results_df = pd.DataFrame({
            x_label: pd.Series(result.x_data).reset_index(drop=True),
            value_label: pd.Series(result.result_data).reset_index(drop=True),
        })
        default_name = f"{self.analysis_type.value.replace('_', ' ').title()} — {fit.label}"
        return results_df, default_name

    @override
    def execute(self) -> bool:
        try:
            if not self.app_state.has_project or not self.app_state.current_project:
                self.logger.warning("No project loaded; cannot analyze fit.")
                return False

            project = self.app_state.current_project
            results_df, default_name = self.run_analysis()
            name = self.result_name or default_name

            self.result_dataset_id = str(uuid.uuid4())
            dataset = Dataset(
                id=self.result_dataset_id,
                name=name,
                data=results_df,
                source_file=None,
            )
            project.add_item(dataset, parent_id=self.folder_id)

            self.app_state.event_bus.emit(DatasetEvents.DATASET_CREATED, {
                "project": project,
                "dataset_id": self.result_dataset_id,
                "dataset_name": name,
                "folder_id": self.folder_id,
                "dataset_data": dataset.data,
            })
            self.logger.info("Created fit-analysis dataset '%s' (%s)", name, self.result_dataset_id)
            return True

        except Exception as e:
            self.logger.error("Analyze-fit failed: %s", e, exc_info=True)
            return False

    @override
    def undo(self) -> bool:
        try:
            if not self.result_dataset_id or not self.app_state.current_project:
                return False
            project = self.app_state.current_project
            dataset = project.find_item(self.result_dataset_id)
            if dataset:
                project.remove_item(dataset)
                self.app_state.event_bus.emit(DatasetEvents.DATASET_DELETED, {
                    "project": project,
                    "dataset_id": self.result_dataset_id,
                    "dataset_name": dataset.name,
                })
            return True
        except Exception as e:
            self.logger.error("Failed to undo analyze-fit: %s", e, exc_info=True)
            return False

    @override
    def redo(self) -> bool:
        return self.execute()
