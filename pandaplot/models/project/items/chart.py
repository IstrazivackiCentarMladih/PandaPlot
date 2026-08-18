"""
Chart model for managing chart/visualization items in the project.
"""

import copy
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional

import numpy as np

from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.chart_type_spec import CHART_TYPE_SPECS
from pandaplot.models.chart.error_direction import ErrorDirection
from pandaplot.models.chart.fit_style import FitStyle
from pandaplot.models.chart.series_style import SeriesStyleBase
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS
from pandaplot.models.project.items.item import Item


class YAxis(StrEnum):
    """Y-axis selection for a data series."""
    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass
class DataSeries:
    """Represents a single data series in a chart.

    Columns are referenced by their stable id (``*_column_id``); the
    ``*_column`` name fields are a resolution fallback for legacy/externally
    edited data and a display hint, never the authoritative reference. A
    column rename updates the dataset registry only — the ids here are
    untouched, so nothing has to cascade into series. Resolve a live name with
    :func:`pandaplot.models.project.items.chart.resolve_series_column`.
    """
    dataset_id: str
    x_column_id: str = ""
    y_column_id: str = ""
    x_error_column_id: str = ""
    y_error_column_id: str = ""
    x_error_minus_column_id: str = ""
    y_error_minus_column_id: str = ""
    # Legacy/fallback column names — populated only by loading old projects
    # (see resolve_series_column). New series reference columns by id.
    x_column: str = ""
    y_column: str = ""
    label: str = ""
    visible: bool = True
    y_axis: YAxis = YAxis.PRIMARY  # "primary" or "secondary" - which Y axis this series plots against
    alpha: float = 1.0
    x_error_column: str = ""
    y_error_column: str = ""
    x_error_minus_column: str = ""  # only used when error_symmetric is False
    y_error_minus_column: str = ""  # only used when error_symmetric is False
    error_symmetric: bool = True
    error_direction: ErrorDirection = ErrorDirection.BOTH  # only used when error_symmetric is True
    error_color: str = ""  # "" => inherit series.style.color
    error_cap_size: float = 3.0
    # Vector-plot ("quiver") column references. u/v are the vector components
    # at each (x, y); magnitude is optional and, when resolved, colors each
    # arrow via the vector style's colormap instead of a flat color.
    u_column_id: str = ""
    v_column_id: str = ""
    u_column: str = ""
    v_column: str = ""
    magnitude_column_id: str = ""
    magnitude_column: str = ""
    series_type: SeriesType = SeriesType.LINE
    style: Optional[SeriesStyleBase] = None

    def __post_init__(self):
        if isinstance(self.y_axis, str):
            try:
                self.y_axis = YAxis(self.y_axis)
            except ValueError:
                self.y_axis = YAxis.PRIMARY
        if isinstance(self.series_type, str):
            self.series_type = SeriesType(self.series_type)
        if self.style is None:
            self.style = SERIES_TYPE_SPECS[self.series_type].style_cls()

    @property
    def has_error_data(self) -> bool:
        """Whether any error-bar column is configured for this series, by
        stable id (current data) or legacy name (old projects loaded before
        stable column ids)."""
        return bool(
            self.x_error_column_id or self.y_error_column_id
            or self.x_error_column or self.y_error_column
        )


@dataclass
class FitData:
    """Represents fitted curve data.

    Source columns are referenced by stable id (``source_*_column_id``); the
    ``source_*_column`` name fields are a legacy/fallback populated only when
    loading old projects. The fit line itself renders from ``x_data``/``y_data``,
    so the source columns are metadata (display + series↔fit matching).
    """
    source_dataset_id: str
    fit_type: str
    x_data: np.ndarray
    y_data: np.ndarray
    label: str
    source_x_column_id: str = ""
    source_y_column_id: str = ""
    source_x_column: str = ""
    source_y_column: str = ""
    visible: bool = True
    fit_params: Optional[Dict[str, Any]] = None
    fit_stats: Optional[Dict[str, Any]] = None
    confidence_lower: np.ndarray | None = None
    confidence_upper: np.ndarray | None = None
    style: Optional[FitStyle] = None

    def __post_init__(self):
        if self.fit_params is None:
            self.fit_params = {}
        if self.fit_stats is None:
            self.fit_stats = {}
        if self.style is None:
            self.style = FitStyle()


class Chart(Item):
    """
    Represents a chart item in the project.
    
    A chart contains visualization configuration and references to datasets.
    It's part of the hierarchical project structure.
    Supports multiple data series from different datasets.
    """
    
    def __init__(self, id: Optional[str] = None, name: str = "",
                 chart_type: "str | ChartType" = ChartType.LINE):
        # Call parent constructor with CHART item type
        super().__init__(id, name)

        # Set chart-specific attributes
        self.chart_type: ChartType = ChartType(chart_type)
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
            "minor_grid_alpha": 0.15,
            "show_grid_x": True,
            "show_grid_y": True,
            "show_grid_y2": True,
            "x_font_size": 12,
            "y_font_size": 12,
            "y2_font_size": 12,
            "x_scale": "linear",
            "y_scale": "linear",
            "y2_scale": "linear",
            "y_side": "left",
            "y2_side": "right",
            "x_auto_limits": True,
            "y_auto_limits": True,
            "y2_auto_limits": True,
            "x_min": 0.0,
            "x_max": 1.0,
            "y_min": 0.0,
            "y_max": 1.0,
            "y2_min": 0.0,
            "y2_max": 1.0,
            "x_tick_mode": "auto",
            "y_tick_mode": "auto",
            "y2_tick_mode": "auto",
            "x_tick_count": 5,
            "y_tick_count": 5,
            "y2_tick_count": 5,
            "x_tick_step": 1.0,
            "y_tick_step": 1.0,
            "y2_tick_step": 1.0,
            "x_tick_format": "auto",
            "y_tick_format": "auto",
            "y2_tick_format": "auto",
            "x_tick_format_custom": "",
            "y_tick_format_custom": "",
            "y2_tick_format_custom": "",
            "hist_bins": 20,
            "subtitle": "",
            "title_font_size": 14,
            "subtitle_font_size": 12,
            "chart_padding": 2.0,
            "chart_padding_w": 2.0,
            "chart_padding_h": 2.0,
            "title_padding": 6.0,
            "main_title_padding": 10.0,
            "top_margin": 1.0,
            "title_bold": True,
            "title_italic": False,
            "subtitle_bold": False,
            "subtitle_italic": False,
            "title_color": "#000000",
            "subtitle_color": "#000000",
            "subtitle_match_title_color": True,
            "width_cm": None,
            "height_cm": None,
            "dpi": None,
            "legend_columns": 1,
            "legend_bg_alpha": 1.0,
        }

        self.style = {
            "figure_size": (10, 6),
            "figure_background_color": "#ffffff",
            "axes_background_color": "#ffffff",
            "font_size": 12,
            "font_family": "Arial",
            "dpi": 100
        }
    
    def retype_series(self, index: int, series_type: "str | SeriesType") -> None:
        """Retype a single series to `series_type`, rebuilding its
        `.style` for the new type and carrying over its current base
        color. This is the same per-series retype logic `set_chart_type`
        applies in bulk to every series a chart-type change makes
        disallowed -- extracted here so an explicit single-series retype
        (e.g. a user picking a type via a per-series UI control) shares
        one implementation with that bulk case, instead of duplicating
        the color-carry logic.
        """
        series = self.data_series[index]
        new_type = SeriesType(series_type)
        if series.series_type == new_type:
            return
        old_style = series.style
        base_color = (
            getattr(old_style, "vector_color", None)
            or getattr(old_style, "color", None)
            or "#1f77b4"
        )
        style_cls = SERIES_TYPE_SPECS[new_type].style_cls
        series.series_type = new_type
        if new_type == SeriesType.VECTOR:
            series.style = style_cls(vector_color=base_color)
        else:
            series.style = style_cls(color=base_color)
        self.update_modified_time()

    def set_chart_type(self, chart_type: "str | ChartType") -> None:
        """Set the chart type, retyping only series not allowed under it.

        chart_editor.py's renderer picks its dispatch function AND its
        style-field expectations from each series' own `series_type` --
        so a series only needs retyping when its current type falls
        OUTSIDE the new chart type's `allowed_series_types` (e.g. a HIST
        series can't stay on a chart that just became "line", since
        Line's spec only allows {LINE, SCATTER}). A series whose type is
        already allowed (e.g. a LINE series when the chart becomes
        "vector", since Vector's spec allows {VECTOR, LINE}) is left
        completely untouched -- mixed series types are legitimate for
        that combination. Retyped series become the new chart type's own
        `default_series_type`, via `retype_series`.
        """
        new_type = ChartType(chart_type)
        if new_type == self.chart_type:
            return
        self.chart_type = new_type
        spec = CHART_TYPE_SPECS[new_type]
        for index, series in enumerate(self.data_series):
            if series.series_type not in spec.allowed_series_types:
                self.retype_series(index, spec.default_series_type)
        self.update_modified_time()
    
    def add_data_series(self, dataset_id: str, x_column_id: str = "",
                       y_column_id: str = "", label: str = "", **kwargs) -> DataSeries:
        """Add a new data series to the chart.

        Columns are referenced by their stable ids (``x_column_id`` /
        ``y_column_id`` and the error-column ids via ``kwargs``). The caller
        resolves names to ids against the dataset; this model holds no
        :class:`Dataset` reference — the renderer resolves ids back to live
        names with :func:`resolve_series_column`.

        ``series_type`` defaults to this chart's own type when the caller
        doesn't pass one explicitly -- every series in a chart still shares
        the chart's type today (mixed series types don't exist until a
        later phase), so a series added without an explicit type should
        never silently default to SeriesType.LINE regardless of what kind
        of chart it's being added to.
        """
        kwargs.setdefault("series_type", SeriesType(self.chart_type))
        series = DataSeries(
            dataset_id=dataset_id,
            x_column_id=x_column_id,
            y_column_id=y_column_id,
            label=label,
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
    
    def add_fit_data(self, source_dataset_id: str, fit_type: str,
                    x_data: np.ndarray, y_data: np.ndarray,
                    source_x_column_id: str = "", source_y_column_id: str = "",
                    label: str = "", **kwargs) -> FitData:
        """Add fit data to the chart.

        Source columns are referenced by their stable ids
        (``source_x_column_id`` / ``source_y_column_id``); the caller resolves
        names to ids against the dataset. This model holds no :class:`Dataset`
        reference (see :meth:`add_data_series`).
        """
        if not label:
            label = f"{fit_type.title()} Fit"

        fit = FitData(
            source_dataset_id=source_dataset_id,
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
    
    def search_chart(self, query: str, project: Any = None) -> bool:
        """Search for a query string in the chart name or configuration.

        Series columns are referenced by id; pass ``project`` to resolve each
        series' column ids to their current names so the search matches on live
        column names (falls back to any stored legacy name when ``project`` is
        omitted or a column can't be resolved).
        """
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
            dataset = project.find_item(series.dataset_id) if project else None
            x_name = resolve_series_column(dataset, series.x_column_id, series.x_column) or ""
            y_name = resolve_series_column(dataset, series.y_column_id, series.y_column) or ""
            if (query_lower in x_name.lower() or
                query_lower in y_name.lower() or
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
                    "x_error_column_id": series.x_error_column_id,
                    "y_error_column_id": series.y_error_column_id,
                    "x_error_minus_column_id": series.x_error_minus_column_id,
                    "y_error_minus_column_id": series.y_error_minus_column_id,
                    "label": series.label,
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
                    "error_cap_size": series.error_cap_size,
                    "u_column_id": series.u_column_id,
                    "v_column_id": series.v_column_id,
                    "u_column": series.u_column,
                    "v_column": series.v_column,
                    "magnitude_column_id": series.magnitude_column_id,
                    "magnitude_column": series.magnitude_column,
                    "series_type": series.series_type.value,
                    "style": asdict(series.style) if series.style is not None else None,
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
                    "visible": fit.visible,
                    "fit_params": fit.fit_params,
                    "fit_stats": fit.fit_stats,
                    "style": asdict(fit.style) if fit.style is not None else None,
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
            series_type = SeriesType(series_dict.get("series_type", chart.chart_type))
            style_dict = series_dict.get("style")
            style = SERIES_TYPE_SPECS[series_type].style_cls(**style_dict) if style_dict is not None else None
            series = DataSeries(
                dataset_id=series_dict["dataset_id"],
                x_column=series_dict["x_column"],
                y_column=series_dict["y_column"],
                x_column_id=series_dict.get("x_column_id", ""),
                y_column_id=series_dict.get("y_column_id", ""),
                x_error_column_id=series_dict.get("x_error_column_id", ""),
                y_error_column_id=series_dict.get("y_error_column_id", ""),
                x_error_minus_column_id=series_dict.get("x_error_minus_column_id", ""),
                y_error_minus_column_id=series_dict.get("y_error_minus_column_id", ""),
                label=series_dict.get("label", ""),
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
                error_cap_size=series_dict.get("error_cap_size", 3.0),
                u_column_id=series_dict.get("u_column_id", ""),
                v_column_id=series_dict.get("v_column_id", ""),
                u_column=series_dict.get("u_column", ""),
                v_column=series_dict.get("v_column", ""),
                magnitude_column_id=series_dict.get("magnitude_column_id", ""),
                magnitude_column=series_dict.get("magnitude_column", ""),
                series_type=series_type,
                style=style,
            )
            chart.data_series.append(series)
        
        # Load fit data
        fit_data_list = data.get("fit_data", [])
        for fit_dict in fit_data_list:
            style_dict = fit_dict.get("style")
            style = FitStyle(**style_dict) if style_dict is not None else None
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
                visible=fit_dict.get("visible", True),
                fit_params=fit_dict.get("fit_params", {}),
                fit_stats=fit_dict.get("fit_stats", {}),
                style=style,
            )
            chart.fit_data.append(fit)

        # Ensure required config keys exist
        if not chart.config:
            chart._init_default_config()

        return chart


def resolve_series_column(dataset: Any, column_id: str,
                          fallback_name: str) -> Optional[str]:
    """Resolve a column reference to its current DataFrame name.

    Prefers the stable ``column_id`` (via the dataset's id->name registry) so a
    renamed column keeps resolving without any series update; falls back to the
    stored name for legacy files or data edited outside the app. Returns None
    when neither resolves (a genuinely missing column). An empty ``fallback_name``
    stays empty (e.g. "no x column" means plot against the index).
    """
    if dataset is not None and column_id:
        name = dataset.column_name(column_id)
        if name is not None:
            return name
    return fallback_name or None


def assign_series_column_ids(series: "DataSeries", dataset: Any) -> None:
    """Fill a series' ``*_column_id`` fields from its name fields via ``dataset``.

    Called at series write sites and during legacy-chart migration. A name that
    resolves to a column gets that column's id; an unresolved name leaves the
    existing id untouched (resolution falls back to the stored name).
    """
    if dataset is None:
        return
    pairs = (
        ("x_column", "x_column_id"),
        ("y_column", "y_column_id"),
        ("x_error_column", "x_error_column_id"),
        ("y_error_column", "y_error_column_id"),
        ("x_error_minus_column", "x_error_minus_column_id"),
        ("y_error_minus_column", "y_error_minus_column_id"),
        ("u_column", "u_column_id"),
        ("v_column", "v_column_id"),
        ("magnitude_column", "magnitude_column_id"),
    )
    for name_field, id_field in pairs:
        name = getattr(series, name_field, "")
        if name:
            cid = dataset.column_id(name)
            if cid is not None:
                setattr(series, id_field, cid)


def assign_fit_column_ids(fit: "FitData", dataset: Any) -> None:
    """Fill a fit's source ``*_column_id`` fields from its name fields."""
    if dataset is None:
        return
    for name_field, id_field in (("source_x_column", "source_x_column_id"),
                                 ("source_y_column", "source_y_column_id")):
        name = getattr(fit, name_field, "")
        if name:
            cid = dataset.column_id(name)
            if cid is not None:
                setattr(fit, id_field, cid)


def snapshot_chart_state(chart: "Chart") -> Dict[str, Any]:
    """Capture the mutable chart state that the properties panel can change.

    Fit data x/y arrays are intentionally not snapshotted — only their
    editable style fields — because the arrays are immutable in the panel
    and can be large.
    """
    return {
        "config": copy.deepcopy(chart.config),
        "style": copy.deepcopy(chart.style),
        "chart_type": chart.chart_type,
        "name": chart.name,
        "data_series": [asdict(s) for s in chart.data_series],
        "fit_data_styles": [copy.deepcopy(f.style) for f in chart.fit_data],
    }


def series_from_flat_dict(series_data: Dict[str, Any]) -> "DataSeries":
    """Reconstruct a DataSeries from a dict shaped like dataclasses.asdict(series)
    -- i.e. with `style` (if present) as a plain dict rather than a
    SeriesStyleBase instance, the shape asdict()'s recursive flattening
    always produces. Used by restore_chart_state (properties-panel
    cancel/undo) and RemoveSeriesCommand.undo() -- both capture a series
    via asdict() and need to reverse that flattening, not just re-apply
    the flat dict as **kwargs (which would leave `style` as a dict)."""
    series_data = dict(series_data)
    style_data = series_data.pop("style", None)
    series = DataSeries(**series_data)
    if style_data is not None:
        series.style = SERIES_TYPE_SPECS[series.series_type].style_cls(**style_data)
    return series


def fit_from_flat_dict(fit_data: dict) -> FitData:
    """Reconstruct a FitData from a flattened dict (e.g. the output of
    dataclasses.asdict()), rebuilding ``style`` as a FitStyle instance
    rather than the plain dict asdict() flattens it into. Mirrors
    series_from_flat_dict's identical fix for the same DataSeries bug
    (RemoveSeriesCommand.undo -- see Phase 3a)."""
    data = dict(fit_data)
    style = data.get("style")
    if isinstance(style, dict):
        data["style"] = FitStyle(**style)
    return FitData(**data)


def restore_chart_state(chart: "Chart", snapshot: Dict[str, Any]) -> None:
    """Restore chart state captured by snapshot_chart_state."""
    chart.config = copy.deepcopy(snapshot["config"])
    chart.style = copy.deepcopy(snapshot["style"])
    chart.chart_type = snapshot["chart_type"]
    chart.name = snapshot["name"]
    chart.data_series = [series_from_flat_dict(series_data) for series_data in snapshot["data_series"]]
    for i, fit_style in enumerate(snapshot["fit_data_styles"]):
        if i < len(chart.fit_data):
            chart.fit_data[i].style = copy.deepcopy(fit_style)
    chart.update_modified_time()

