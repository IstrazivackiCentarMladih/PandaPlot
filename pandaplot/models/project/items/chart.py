"""
Chart model for managing chart/visualization items in the project.
"""

import copy
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional

import numpy as np

from pandaplot.models.project.items.item import Item


class YAxis(StrEnum):
    """Y-axis selection for a data series."""
    PRIMARY = "primary"
    SECONDARY = "secondary"


class ErrorDirection(StrEnum):
    """Which side(s) of a data point a symmetric error bar's magnitude is drawn on."""
    BOTH = "both"
    PLUS = "plus"
    MINUS = "minus"


@dataclass
class DataSeries:
    """Represents a single data series in a chart.

    Columns are referenced by stable id (``x_column_id`` / ``y_column_id``) which
    survives column renames. ``x_column`` / ``y_column`` hold the name at creation
    time and are used only as a fallback for references that predate column ids;
    the current name is always resolved from the owning dataset at use-time.
    """
    dataset_id: str
    x_column: str
    y_column: str
    x_column_id: str = ""
    y_column_id: str = ""
    label: str = ""
    color: str = "#1f77b4"
    marker_color: str = ""
    marker_edge_color: str = "#000000"
    line_style: str = "solid"
    marker_style: str = "circle"
    line_width: float = 2.0
    marker_size: float = 2.0
    visible: bool = True
    y_axis: YAxis = YAxis.PRIMARY  # "primary" or "secondary" - which Y axis this series plots against
    alpha: float = 1.0
    x_error_column: str = ""
    y_error_column: str = ""
    x_error_minus_column: str = ""  # only used when error_symmetric is False
    y_error_minus_column: str = ""  # only used when error_symmetric is False
    error_symmetric: bool = True
    error_direction: ErrorDirection = ErrorDirection.BOTH  # only used when error_symmetric is True
    error_color: str = ""  # "" => inherit series.color
    error_cap_size: float = 3.0

    def __post_init__(self):
        if isinstance(self.y_axis, str):
            try:
                self.y_axis = YAxis(self.y_axis)
            except ValueError:
                self.y_axis = YAxis.PRIMARY


@dataclass
class FitData:
    """Represents fitted curve data."""
    source_dataset_id: str
    source_x_column: str
    source_y_column: str
    fit_type: str
    x_data: np.ndarray
    y_data: np.ndarray
    label: str
    color: str = "#ff7f0e"
    line_style: str = "dashed"
    line_width: float = 2.0
    visible: bool = True
    fit_params: Optional[Dict[str, Any]] = None
    fit_stats: Optional[Dict[str, Any]] = None
    confidence_lower: np.ndarray | None = None
    confidence_upper: np.ndarray | None = None
    # Stable column ids (see DataSeries); source_x/y_column are the fallback name.
    source_x_column_id: str = ""
    source_y_column_id: str = ""

    def __post_init__(self):
        if self.fit_params is None:
            self.fit_params = {}
        if self.fit_stats is None:
            self.fit_stats = {}


class Chart(Item):
    """
    Represents a chart item in the project.
    
    A chart contains visualization configuration and references to datasets.
    It's part of the hierarchical project structure.
    Supports multiple data series from different datasets.
    """
    
    def __init__(self, id: Optional[str] = None, name: str = "", 
                 chart_type: str = "line"):
        # Call parent constructor with CHART item type
        super().__init__(id, name)
        
        # Set chart-specific attributes
        self.chart_type: str = chart_type
        self.data_series: List[DataSeries] = []
        self.fit_data: List[FitData] = []
        self.config: Dict[str, Any] = {}
        self.style: Dict[str, Any] = {}
        
        # Initialize default configuration
        self._init_default_config()
    
    def _init_default_config(self) -> None:
        """Initialize default chart configuration."""
        self.config = {
            "title": self.name,
            "x_label": "",
            "y_label": "",
            "y2_label": "",
            "show_legend": True,
            "legend_position": "upper right",
            "legend_show_frame": True,
            "legend_font_size": 10,
            "legend_bg_color": "#ffffff",
            "grid_style": "solid",
            "grid_alpha": 0.3,
            "show_grid_x": True,
            "show_grid_y": True,
            "x_font_size": 12,
            "y_font_size": 12,
            "x_scale": "linear",
            "y_scale": "linear",
            "x_auto_limits": True,
            "y_auto_limits": True,
            "x_min": 0.0,
            "x_max": 1.0,
            "y_min": 0.0,
            "y_max": 1.0,
            "x_tick_mode": "auto",
            "y_tick_mode": "auto",
            "x_tick_count": 5,
            "y_tick_count": 5,
            "x_tick_step": 1.0,
            "y_tick_step": 1.0,
            "x_tick_format": "auto",
            "y_tick_format": "auto",
            "x_tick_format_custom": "",
            "y_tick_format_custom": "",
            "hist_bins": 20,
        }

        self.style = {
            "figure_size": (10, 6),
            "background_color": "#ffffff",
            "font_size": 12,
            "font_family": "Arial",
            "dpi": 100
        }
    
    def update_name(self, new_name: str) -> None:
        """Update the chart name and modification timestamp."""
        # TODO: separate item name and title
        self.name = new_name
        self.config["title"] = new_name  # Update chart title as well
        self.update_modified_time()
    
    def set_chart_type(self, chart_type: str) -> None:
        """Set the chart type."""
        self.chart_type = chart_type
        self.update_modified_time()
    
    def add_data_series(self, dataset_id: str, x_column: str, y_column: str,
                       label: str = "", x_column_id: str = "", y_column_id: str = "",
                       **kwargs) -> DataSeries:
        """Add a new data series to the chart."""
        series = DataSeries(
            dataset_id=dataset_id,
            x_column=x_column,
            y_column=y_column,
            x_column_id=x_column_id,
            y_column_id=y_column_id,
            label=label or f"{dataset_id}:{y_column}",
            **kwargs
        )
        self.data_series.append(series)
        self.update_modified_time()
        return series
    
    def remove_data_series(self, index: int) -> bool:
        """Remove a data series by index."""
        if 0 <= index < len(self.data_series):
            del self.data_series[index]
            self.update_modified_time()
            return True
        return False
    
    def update_data_series(self, index: int, **kwargs) -> bool:
        """Update a data series by index."""
        if 0 <= index < len(self.data_series):
            series = self.data_series[index]
            for key, value in kwargs.items():
                if hasattr(series, key):
                    setattr(series, key, value)
            self.update_modified_time()
            return True
        return False
    
    def get_data_series(self, index: int) -> Optional[DataSeries]:
        """Get a data series by index."""
        if 0 <= index < len(self.data_series):
            return self.data_series[index]
        return None
    
    def get_all_datasets(self) -> List[str]:
        """Get all unique dataset IDs used in this chart."""
        return list(set(series.dataset_id for series in self.data_series))
    
    def add_fit_data(self, source_dataset_id: str, source_x_column: str,
                    source_y_column: str, fit_type: str, x_data: np.ndarray,
                    y_data: np.ndarray, label: str = "", source_x_column_id: str = "",
                    source_y_column_id: str = "", **kwargs) -> FitData:
        """Add fit data to the chart."""
        if not label:
            label = f"{fit_type.title()} Fit for {source_dataset_id}:{source_y_column}"

        fit = FitData(
            source_dataset_id=source_dataset_id,
            source_x_column=source_x_column,
            source_y_column=source_y_column,
            source_x_column_id=source_x_column_id,
            source_y_column_id=source_y_column_id,
            fit_type=fit_type,
            x_data=x_data,
            y_data=y_data,
            label=label,
            **kwargs
        )
        self.fit_data.append(fit)
        self.update_modified_time()
        return fit
    
    def remove_fit_data(self, index: int) -> bool:
        """Remove fit data by index."""
        if 0 <= index < len(self.fit_data):
            del self.fit_data[index]
            self.update_modified_time()
            return True
        return False
    
    def update_fit_data(self, index: int, **kwargs) -> bool:
        """Update fit data by index."""
        if 0 <= index < len(self.fit_data):
            fit = self.fit_data[index]
            for key, value in kwargs.items():
                if hasattr(fit, key):
                    setattr(fit, key, value)
            self.update_modified_time()
            return True
        return False
    
    def get_fit_data(self, index: int) -> Optional[FitData]:
        """Get fit data by index."""
        if 0 <= index < len(self.fit_data):
            return self.fit_data[index]
        return None
    
    def clear_fit_data(self) -> None:
        """Clear all fit data."""
        self.fit_data.clear()
        self.update_modified_time()
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """Update chart configuration."""
        self.config.update(config_updates)
        self.update_modified_time()
    
    def update_style(self, style_updates: Dict[str, Any]) -> None:
        """Update chart style."""
        self.style.update(style_updates)
        self.update_modified_time()
    
    def set_labels(self, title: Optional[str] = None, x_label: Optional[str] = None, 
                  y_label: Optional[str] = None) -> None:
        """Set chart labels."""
        if title is not None:
            self.config["title"] = title
            # Also update the item name if different
            if title != self.name:
                self.name = title
        if x_label is not None:
            self.config["x_label"] = x_label
        if y_label is not None:
            self.config["y_label"] = y_label
        self.update_modified_time()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the chart configuration."""
        return {
            "chart_type": self.chart_type,
            "data_series_count": len(self.data_series),
            "datasets": self.get_all_datasets(),
            "title": self.config.get("title", ""),
            "has_legend": self.config.get("show_legend", True),
            "has_grid": self.config.get("show_grid_x", True) or self.config.get("show_grid_y", True)
        }
    
    def search_chart(self, query: str) -> bool:
        """Search for a query string in the chart name or configuration."""
        query_lower = query.lower()
        
        # Search in name and title
        if (query_lower in self.name.lower() or 
            query_lower in self.config.get("title", "").lower()):
            return True
        
        # Search in chart type
        if query_lower in self.chart_type.lower():
            return True
        
        # Search in data series columns and labels
        for series in self.data_series:
            if (query_lower in series.x_column.lower() or
                query_lower in series.y_column.lower() or
                query_lower in series.label.lower() or
                query_lower in series.dataset_id.lower()):
                return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chart to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            "chart_type": self.chart_type,
            "data_series": [
                {
                    "dataset_id": series.dataset_id,
                    "x_column": series.x_column,
                    "y_column": series.y_column,
                    "x_column_id": series.x_column_id,
                    "y_column_id": series.y_column_id,
                    "label": series.label,
                    "color": series.color,
                    "marker_color": series.marker_color,
                    "marker_edge_color": series.marker_edge_color,
                    "line_style": series.line_style,
                    "marker_style": series.marker_style,
                    "line_width": series.line_width,
                    "marker_size": series.marker_size,
                    "visible": series.visible,
                    "y_axis": series.y_axis,
                    "alpha": series.alpha,
                    "x_error_column": series.x_error_column,
                    "y_error_column": series.y_error_column,
                    "x_error_minus_column": series.x_error_minus_column,
                    "y_error_minus_column": series.y_error_minus_column,
                    "error_symmetric": series.error_symmetric,
                    "error_direction": series.error_direction,
                    "error_color": series.error_color,
                    "error_cap_size": series.error_cap_size
                } for series in self.data_series
            ],
            "fit_data": [
                {
                    "source_dataset_id": fit.source_dataset_id,
                    "source_x_column": fit.source_x_column,
                    "source_y_column": fit.source_y_column,
                    "source_x_column_id": fit.source_x_column_id,
                    "source_y_column_id": fit.source_y_column_id,
                    "fit_type": fit.fit_type,
                    "x_data": fit.x_data.tolist(),
                    "y_data": fit.y_data.tolist(),
                    "label": fit.label,
                    "color": fit.color,
                    "line_style": fit.line_style,
                    "line_width": fit.line_width,
                    "visible": fit.visible,
                    "fit_params": fit.fit_params,
                    "fit_stats": fit.fit_stats
                } for fit in self.fit_data
            ],
            "config": self.config,
            "style": self.style
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chart":
        """Create chart from dictionary."""
        chart = cls(
            id=data.get("id"),
            name=data.get("name", ""),
            chart_type=data.get("chart_type", "line")
        )
        
        # Set inherited attributes
        chart.parent_id = data.get("parent_id")
        chart.created_at = data.get("created_at", datetime.now().isoformat())
        chart.modified_at = data.get("modified_at", chart.created_at)
        chart.metadata = data.get("metadata", {})
        
        # Set chart-specific attributes, merging persisted values over the
        # defaults so older saved charts still get any newly added keys
        chart.config.update(data.get("config", {}))
        chart.style.update(data.get("style", {}))
        
        # Load data series
        series_data = data.get("data_series", [])
        for series_dict in series_data:
            series = DataSeries(
                dataset_id=series_dict["dataset_id"],
                x_column=series_dict["x_column"],
                y_column=series_dict["y_column"],
                x_column_id=series_dict.get("x_column_id", ""),
                y_column_id=series_dict.get("y_column_id", ""),
                label=series_dict.get("label", ""),
                color=series_dict.get("color", "#1f77b4"),
                marker_color=series_dict.get("marker_color", ""),
                marker_edge_color=series_dict.get("marker_edge_color", "#000000"),
                line_style=series_dict.get("line_style", "solid"),
                marker_style=series_dict.get("marker_style", "circle"),
                line_width=series_dict.get("line_width", 2.0),
                marker_size=series_dict.get("marker_size", 2.0),
                visible=series_dict.get("visible", True),
                y_axis=series_dict.get("y_axis", "primary"),
                alpha=series_dict.get("alpha", 1.0),
                x_error_column=series_dict.get("x_error_column", ""),
                y_error_column=series_dict.get("y_error_column", ""),
                x_error_minus_column=series_dict.get("x_error_minus_column", ""),
                y_error_minus_column=series_dict.get("y_error_minus_column", ""),
                error_symmetric=series_dict.get("error_symmetric", True),
                error_direction=ErrorDirection(series_dict.get("error_direction", ErrorDirection.BOTH)),
                error_color=series_dict.get("error_color", ""),
                error_cap_size=series_dict.get("error_cap_size", 3.0)
            )
            chart.data_series.append(series)
        
        # Load fit data
        fit_data_list = data.get("fit_data", [])
        for fit_dict in fit_data_list:
            fit = FitData(
                source_dataset_id=fit_dict["source_dataset_id"],
                source_x_column=fit_dict["source_x_column"],
                source_y_column=fit_dict["source_y_column"],
                source_x_column_id=fit_dict.get("source_x_column_id", ""),
                source_y_column_id=fit_dict.get("source_y_column_id", ""),
                fit_type=fit_dict["fit_type"],
                x_data=np.array(fit_dict["x_data"]),
                y_data=np.array(fit_dict["y_data"]),
                label=fit_dict.get("label", ""),
                color=fit_dict.get("color", "#ff7f0e"),
                line_style=fit_dict.get("line_style", "dashed"),
                line_width=fit_dict.get("line_width", 2.0),
                visible=fit_dict.get("visible", True),
                fit_params=fit_dict.get("fit_params", {}),
                fit_stats=fit_dict.get("fit_stats", {})
            )
            chart.fit_data.append(fit)

        # Ensure required config keys exist
        if not chart.config:
            chart._init_default_config()

        return chart


def sync_series_column_ids(series: DataSeries, dataset) -> None:
    """Fill a series' column ids from its current column names.

    Resolves ``x_column`` / ``y_column`` against ``dataset`` and stores the
    stable ids. Only assigns ids that resolve, so a stale name (e.g. after a
    rename that the series predates) never clobbers an already-valid id.
    """
    if dataset is None:
        return
    xid = dataset.get_column_id(series.x_column)
    if xid:
        series.x_column_id = xid
    yid = dataset.get_column_id(series.y_column)
    if yid:
        series.y_column_id = yid


def sync_fit_column_ids(fit: FitData, dataset) -> None:
    """Fill fit data's source column ids from its current column names."""
    if dataset is None:
        return
    xid = dataset.get_column_id(fit.source_x_column)
    if xid:
        fit.source_x_column_id = xid
    yid = dataset.get_column_id(fit.source_y_column)
    if yid:
        fit.source_y_column_id = yid


def backfill_chart_column_ids(chart: "Chart", resolve_dataset) -> None:
    """Assign column ids to every series/fit of a chart that lacks them.

    ``resolve_dataset`` maps a dataset id to its Dataset (or None). Used at
    project load time to migrate charts saved before column ids existed.
    """
    for series in chart.data_series:
        if not (series.x_column_id and series.y_column_id):
            sync_series_column_ids(series, resolve_dataset(series.dataset_id))
    for fit in chart.fit_data:
        if not (fit.source_x_column_id and fit.source_y_column_id):
            sync_fit_column_ids(fit, resolve_dataset(fit.source_dataset_id))


def snapshot_chart_state(chart: "Chart") -> Dict[str, Any]:
    """Capture the mutable chart state that the properties panel can change.

    Fit data x/y arrays are intentionally not snapshotted — only their
    editable style fields — because the arrays are immutable in the panel
    and can be large.
    """
    return {
        "config": copy.deepcopy(chart.config),
        "chart_type": chart.chart_type,
        "name": chart.name,
        "data_series": [asdict(s) for s in chart.data_series],
        "fit_data_styles": [
            {"color": f.color, "line_width": f.line_width}
            for f in chart.fit_data
        ],
    }


def restore_chart_state(chart: "Chart", snapshot: Dict[str, Any]) -> None:
    """Restore chart state captured by snapshot_chart_state."""
    chart.config = copy.deepcopy(snapshot["config"])
    chart.chart_type = snapshot["chart_type"]
    chart.name = snapshot["name"]
    chart.data_series = [DataSeries(**d) for d in snapshot["data_series"]]
    for i, fit_style in enumerate(snapshot["fit_data_styles"]):
        if i < len(chart.fit_data):
            chart.fit_data[i].color = fit_style["color"]
            chart.fit_data[i].line_width = fit_style["line_width"]
    chart.update_modified_time()

