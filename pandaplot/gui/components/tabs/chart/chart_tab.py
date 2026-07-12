"""Chart tab widget for displaying and editing charts."""

from typing import override

import numpy as np
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from pandaplot.gui.components.tabs.chart.chart_editor import ChartEditorWidget
from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.events import ChartEvents, FitEvents, UIEvents
from pandaplot.models.events.event_types import ProjectEvents
from pandaplot.models.project.items import Chart
from pandaplot.models.state.app_context import AppContext

# Maps a short fit-type name to its chart color. `fit_type` from the fit panel is a
# full descriptive string (e.g. "Linear (y = ax + b)"), so lookups use substring
# matching rather than exact-match, mirroring FitService._get_fit_func.
FIT_TYPE_COLORS = {
    "Linear": "#ff0000",       # Red
    "Quadratic": "#00aa00",    # Green
    "Exponential": "#0066cc",  # Blue
    "Power": "#cc00cc",        # Magenta
    "Logarithmic": "#ff6600",  # Orange
    "Custom": "#00cccc",       # Cyan
}


def _resolve_fit_style(fit_type: str) -> tuple[str, str]:
    """Return (short_name, color) for a fit_type string like 'Linear (y = ax + b)'."""
    for short_name, color in FIT_TYPE_COLORS.items():
        if short_name in fit_type:
            return short_name, color
    return fit_type, "#ff0000"


class ChartTab(PWidget):
    """
    Main chart tab widget that contains the chart editor.
    """

    def __init__(self, app_context: AppContext, chart: Chart, parent: QWidget):
        super().__init__(app_context=app_context, parent=parent)
        self.chart = chart
        self._initialize()

    @override
    def _init_ui(self):
        """Set up the chart tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create chart editor
        self.chart_editor = ChartEditorWidget(app_context=self.app_context, chart=self.chart, parent=self)

        layout.addWidget(self.chart_editor)

    @override
    def _apply_theme(self):
        pass

    def setup_event_subscriptions(self):
        """Set up event subscriptions for tab title changes and chart updates."""
        self.subscribe_to_event(
            UIEvents.TAB_TITLE_CHANGED, self.on_tab_title_changed)
        self.subscribe_to_event(
            ProjectEvents.PROJECT_ITEM_RENAMED, self.on_chart_renamed)
        self.subscribe_to_event(
            ChartEvents.CHART_UPDATED, self.on_chart_updated)
        self.subscribe_to_event(FitEvents.FIT_APPLIED, self.on_fit_applied)

    def on_tab_title_changed(self, event_data: dict):
        """Handle tab title change events."""
        if event_data.get("tab_type") == "chart" and event_data.get("chart_id") == self.chart.id:
            self.refresh_tab_title()

    def on_chart_renamed(self, event_data: dict):
        """Update the tab title when the underlying chart item is renamed."""
        if event_data.get("item_id") == self.chart.id:
            self.refresh_tab_title()

    def refresh_tab_title(self):
        """Push the current tab title up to the tab container."""
        parent_container = self.parent()
        while parent_container is not None and not hasattr(parent_container, "update_tab_title"):
            parent_container = parent_container.parent()
        if parent_container:
            update_fn = getattr(parent_container, "update_tab_title", None)
            if callable(update_fn):
                try:
                    update_fn(self, self.get_tab_title())
                except Exception:
                    pass

    def on_chart_updated(self, event_data: dict):
        """Handle chart update events from other components."""
        updated_chart_id = event_data.get("chart_id")

        # Only respond if this is our chart
        if updated_chart_id == self.chart.id:
            self._refresh_chart_editor()

    def _refresh_chart_editor(self):
        """Refresh the chart editor's preview, guarding against a deleted widget."""
        if hasattr(self, "chart_editor") and isValid(self.chart_editor):
            try:
                self.chart_editor.refresh_chart()
                self.logger.debug(
                    "ChartTab refreshed for chart %s", self.chart.name)
            except RuntimeError as e:
                # Widget was deleted during callback
                self.logger.debug(f"Chart editor deleted during update: {e}")

    def on_fit_applied(self, event_data: dict):
        """Handle fit applied events to add fit curves to the chart."""
        fit_chart_id = event_data.get("chart_id")

        # Only respond if this is our chart
        if fit_chart_id == self.chart.id:
            fit_results = event_data.get("fit_results", {})
            fit_type = fit_results.get("fit_type", "Unknown")
            source_dataset_name = event_data.get("dataset_name", "Unknown")

            # Get the source dataset info from the fit results
            source_dataset_id = fit_results.get("source_dataset_id", "")
            source_x_column = fit_results.get("source_x_column", "")
            source_y_column = fit_results.get("source_y_column", "")

            # fit_type is a full descriptive string (e.g. "Linear (y = ax + b)"),
            # so resolve both a short display name and its color together.
            short_fit_name, fit_color = _resolve_fit_style(fit_type)

            x_fit = np.array(fit_results.get("x_fit", []))
            y_fit = np.array(fit_results.get("y_fit", []))

            param_names = fit_results.get("param_names", [])
            parameters = fit_results.get("parameters", [])
            errors = fit_results.get("errors", [])
            fit_params = {name: float(value) for name, value in zip(param_names, parameters, strict=False)}
            fit_stats = {
                "errors": {name: float(value) for name, value in zip(param_names, errors, strict=False)},
                "r_squared": fit_results.get("r_squared"),
            }

            self.chart.add_fit_data(
                source_dataset_id=source_dataset_id,
                source_x_column=source_x_column,
                source_y_column=source_y_column,
                fit_type=fit_type,
                x_data=x_fit,
                y_data=y_fit,
                label=f"{short_fit_name} Fit ({source_dataset_name})",
                color=fit_color,
                line_style="dashed",
                line_width=2.0,
                fit_params=fit_params,
                fit_stats=fit_stats
            )

            # Publish chart updated event to notify other components; this
            # loops back into on_chart_updated above and refreshes our own
            # chart_editor too, so no separate direct refresh call is needed.
            self.publish_event(ChartEvents.CHART_UPDATED, {
                "chart_id": self.chart.id,
                "chart": self.chart,
                "update_type": "fit_added"
            })

    def get_tab_title(self) -> str:
        """Get the tab title."""
        return f"📈 {self.chart.name}"

    def get_chart(self) -> Chart:
        """Get the chart object."""
        return self.chart
