from typing import override
from dataclasses import dataclass
from typing import Optional, Any

import numpy as np
from matplotlib.ticker import AutoLocator, FuncFormatter, MaxNLocator, MultipleLocator, ScalarFormatter
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas, cm_to_inches, fit_size_cm
from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.events.event_types import ConfigEvents
from pandaplot.models.project.items.chart import Chart, ErrorDirection
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.config import (
    MAX_CHART_HEIGHT_CM,
    MAX_CHART_WIDTH_CM,
    MIN_CHART_HEIGHT_CM,
    MIN_CHART_WIDTH_CM,
)
from pandaplot.services.config.config_manager import ConfigManager
from pandaplot.services.theme.theme_manager import ThemeManager


def apply_axis_ticks(axis, mode, count, step, fmt, custom_fmt):
    """Apply tick placement and label formatting to a matplotlib Axis.

    axis: a matplotlib Axis object (e.g. ax.xaxis or ax.yaxis)
    mode: "auto" | "count" | "step" - tick placement strategy
    count: number of ticks when mode == "count"
    step: fixed spacing between ticks when mode == "step"
    fmt: "auto" | "integer" | "1decimal" | "2decimal" | "scientific" | "custom"
    custom_fmt: a Python format spec (e.g. "{:.2f}") used when fmt == "custom"
    """
    if mode == "count":
        axis.set_major_locator(MaxNLocator(nbins=count))
    elif mode == "step":
        axis.set_major_locator(MultipleLocator(step))
    else:
        axis.set_major_locator(AutoLocator())

    if fmt == "integer":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    elif fmt == "1decimal":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}"))
    elif fmt == "2decimal":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}"))
    elif fmt == "scientific":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2e}"))
    elif fmt == "custom" and custom_fmt:
        def _safe_custom(v, _, _fmt=custom_fmt):
            try:
                return _fmt.format(v)
            except Exception:
                return str(v)
        axis.set_major_formatter(FuncFormatter(_safe_custom))
    else:
        axis.set_major_formatter(ScalarFormatter())


def _resolve_error_column(df, column_name):
    """Best-effort lookup of an optional error column.

    Returns None (never an error) when the column isn't configured or no
    longer exists, so a stale error-column reference just silently drops
    the error bars instead of hiding the whole series.
    """
    if not column_name or column_name not in df.columns:
        return None
    return df[column_name].to_numpy()


@dataclass
class SeriesData:
    x_data: Any
    y_data: Any
    x_err: Optional[Any]
    y_err: Optional[Any]
    x_err_minus: Optional[Any]
    y_err_minus: Optional[Any]
    error: Optional[str]


def resolve_series_data(project, series, chart_type=None) -> SeriesData:
    """Resolve a DataSeries against the project's datasets.

    Returns (x_data, y_data, x_err, y_err, x_err_minus, y_err_minus, None) on
    success, or all-None with a message when the dataset or a required
    column can't be found. An empty x_column means "plot against the
    DataFrame index". Histograms only ever plot y_column, so a stale/unused
    x_column is ignored when chart_type == "hist". The error columns are
    resolved leniently (see _resolve_error_column) since they're optional;
    x_err_minus/y_err_minus are only meaningful when series.error_symmetric
    is False.
    """
    from pandaplot.models.project.items.dataset import Dataset

    if project is None:
        return SeriesData(None, None, None, None, None, None, "no project loaded")

    dataset = project.find_item(series.dataset_id)
    if not isinstance(dataset, Dataset) or dataset.data is None:
        return SeriesData(None, None, None, None, None, None, f"dataset '{series.dataset_id}' not found")

    df = dataset.data
    if not series.y_column:
        return SeriesData(None, None, None, None, None, None, "no Y column configured")

    needs_x_column = chart_type != "hist"
    x_column = series.x_column if needs_x_column else None

    missing = [c for c in (x_column, series.y_column)
               if c and c not in df.columns]
    if missing:
        cols = ", ".join(f"'{c}'" for c in missing)
        return SeriesData(None, None, None, None, None, None, f"column {cols} not found in '{dataset.name}'")

    x_data = df[x_column] if x_column else df.index
    x_err = _resolve_error_column(df, series.x_error_column)
    y_err = _resolve_error_column(df, series.y_error_column)
    x_err_minus = _resolve_error_column(df, series.x_error_minus_column)
    y_err_minus = _resolve_error_column(df, series.y_error_minus_column)
    return SeriesData(x_data, df[series.y_column], x_err, y_err, x_err_minus, y_err_minus, None)


def _symmetric_directional_error(magnitude, direction: ErrorDirection):
    """Turn a symmetric error magnitude into the array matplotlib expects.

    ErrorDirection.PLUS/MINUS produce an asymmetric (2, N) array with the
    unused side zeroed out, since matplotlib's errorbar() only accepts a
    single magnitude or an explicit lower/upper pair.
    """
    if magnitude is None:
        return None
    if direction == ErrorDirection.BOTH:
        return magnitude
    zeros = np.zeros_like(magnitude)
    return np.vstack([zeros, magnitude]) if direction == ErrorDirection.PLUS else np.vstack([magnitude, zeros])


def build_error_array(magnitude, minus_magnitude, direction, symmetric):
    """Combine a series' resolved error column(s) into what errorbar() expects.

    In symmetric mode only `magnitude` is used, expanded per `direction` via
    _symmetric_directional_error. In asymmetric mode `magnitude` is the
    upper (+) error and `minus_magnitude` the lower (-) error; either side
    missing is treated as zero so a one-sided uncertainty column is still
    usable on its own.
    """
    if symmetric:
        return _symmetric_directional_error(magnitude, direction)
    if magnitude is None and minus_magnitude is None:
        return None
    n = len(magnitude) if magnitude is not None else len(minus_magnitude)
    zeros = np.zeros(n)
    lower = minus_magnitude if minus_magnitude is not None else zeros
    upper = magnitude if magnitude is not None else zeros
    return np.vstack([lower, upper])


class ChartEditorWidget(PWidget):
    """
    A chart editor widget with configuration options and live preview.
    """

    def __init__(self, app_context: AppContext, chart: Chart, parent: QWidget):
        super().__init__(app_context=app_context, parent=parent)
        self.chart = chart

        self._initialize()
        self.load_chart_config()
        self.update_chart()

        # Apply theme after UI is fully constructed
        QTimer.singleShot(100, self._apply_theme)

        # Fit the chart to the preview panel once the layout has settled and
        # the panel's real viewport size is known (a new chart has no saved
        # size yet, so start it filling the visible preview area).
        QTimer.singleShot(100, self._apply_initial_fit_size)

    @override
    def _apply_theme(self):
        """Apply theme-specific styling to all components."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        
        # Get theme-appropriate colors
        card_bg = palette.get("card_bg", "#f8f9fa")
        card_border = palette.get("card_border", "#dee2e6")
        base_fg = palette.get("base_fg", "#000000")
        secondary_fg = palette.get("secondary_fg", "#555555")
        
        # Apply styling to preview frame
        self.preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 6px;
            }}
        """)
        
        # Apply styling to status frame
        self.status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 6px;
                padding: 1px;
            }}
        """)
        
        # Apply styling to dataset label
        self.dataset_label.setStyleSheet(f"color: {secondary_fg}; font-size: 12px;")
        
        # Apply styling to status label (preserve color logic based on current text)
        self._update_status_label_style()
        
        # Apply theme to toolbar if it exists
        self._apply_toolbar_theme()
        
        # Apply theme to spinboxes
        self._apply_spinbox_style(self.width_spin)
        self._apply_spinbox_style(self.height_spin)
        
        # Apply theme to size label
        self._apply_label_style(self.size_label)
        self._apply_label_style(self.multiply_label)
        
        # Apply theme to chart canvas navigation if it exists
        self.chart_canvas.apply_navigation_theme(base_fg, card_bg, card_border)

    def _apply_spinbox_style(self, spinbox):
        """Apply theme-aware styling to a spin box (QSpinBox or QDoubleSpinBox)"""
        try:
            theme_manager = self.app_context.get_manager(ThemeManager)
            palette = theme_manager.get_surface_palette()

            base_fg = palette.get("base_fg", "#000000")
            card_border = palette.get("card_border", "#dee2e6")
            card_bg = palette.get("card_bg", "#f8f9fa")

            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spinbox.setStyleSheet(f"""
                QAbstractSpinBox {{
                    background-color: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 3px;
                    padding: 2px 5px;
                    color: {base_fg};
                    font-size: 12px;
                }}
                QAbstractSpinBox:focus {{
                    border-color: #007bff;
                    background-color: {card_bg};
                }}
            """)
        except Exception as e:
            self.logger.debug(f"Could not apply spinbox style: {e}")

    def _apply_label_style(self, label):
        """Apply theme-aware styling to a QLabel"""
        try:
            theme_manager = self.app_context.get_manager(ThemeManager)
            palette = theme_manager.get_surface_palette()
            base_fg = palette.get("base_fg", "#000000")

            label.setStyleSheet(f"""
                QLabel {{
                    color: {base_fg};
                    font-weight: 500;
                    margin: 0 5px;
                }}
            """)
        except Exception as e:
            self.logger.debug(f"Could not apply label style: {e}")

    def _apply_toolbar_theme(self):
        """Apply theme-aware styling to the preview toolbar."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        base_fg = palette.get("base_fg", "#000000")
        card_bg = palette.get("card_bg", "#f8f9fa")
        card_border = palette.get("card_border", "#dee2e6")
        
        self.preview_toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {card_bg};
                border-bottom: 1px solid {card_border};
                padding: 4px;
                color: {base_fg};
            }}
            QToolBar QToolButton {{
                color: {base_fg};
                background-color: transparent;
                border: none;
                padding: 6px 10px;
                margin: 1px;
                border-radius: 3px;
                font-weight: 500;
            }}
            QToolBar QToolButton:hover {{
                background-color: {card_border};
                color: {base_fg};
            }}
            QToolBar QToolButton:pressed {{
                background-color: {card_border};
                color: {base_fg};
            }}
        """)

    def _update_status_label_style(self):
        """Update status label styling based on current status and theme."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        secondary_fg = palette.get("secondary_fg", "#555555")
        
        status_text = self.status_label.text()
        
        # Determine color based on status
        if "Modified" in status_text:
            color = "#ffc107"  # Warning yellow
        elif "Saved" in status_text:
            color = "#28a745"  # Success green
        elif "Error" in status_text:
            color = "#dc3545"  # Error red
        else:
            color = secondary_fg  # Default theme color
            
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

    @override
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        # Main content area with splitter
        self.create_content_section(layout)

        # Status bar
        self.create_status_section(layout)

    def setup_event_subscriptions(self):
        """Set up event subscriptions for the chart editor."""
        # Subscribe to config updates to adjust display settings like DPI
        self.subscribe_to_event(ConfigEvents.CONFIG_UPDATED, self._on_config_updated)

    def _on_config_updated(self, data):
        """Handle config.updated events to apply display changes (e.g., DPI)."""
        try:
            cfg = data.get("config") if isinstance(data, dict) else None
            if not cfg:
                return
            dpi = getattr(getattr(cfg, "chart_display", None), "dpi", None)
            if dpi and isValid(self.chart_canvas):
                self.chart_canvas.set_dpi(dpi)
        except Exception:
            self.logger.exception("Failed applying updated DPI setting")

    def create_content_section(self, layout):
        """Create the main content section with chart preview only."""
        # Chart preview section (full width, no configuration panel)
        self.create_chart_preview_section(layout)

    def create_chart_preview_section(self, layout):
        """Create the chart preview section."""
        self.preview_frame = QFrame()
        # Set size policy to expand and take all available space
        self.preview_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(10, 10, 10, 10)

        # Preview toolbar with chart actions and size controls
        self.preview_toolbar = QToolBar()
        self.preview_toolbar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Add chart actions
        self.create_chart_toolbar_actions(self.preview_toolbar)

        # Add separator
        self.preview_toolbar.addSeparator()

        # Add size controls
        self.size_label = QLabel("Size:")
        self.preview_toolbar.addWidget(self.size_label)

        # Fetch preferred DPI and default chart size from config manager
        dpi = 100
        default_width_cm = 20
        default_height_cm = 15
        try:
            cfg_manager = self.app_context.get_manager(ConfigManager)
            cfg = getattr(cfg_manager, "config", None)
            chart_display = getattr(cfg, "chart_display", None) if cfg else None
            if chart_display:
                dpi = getattr(chart_display, "dpi", dpi) or dpi
                default_width_cm = getattr(chart_display, "default_width_cm", default_width_cm) or default_width_cm
                default_height_cm = getattr(chart_display, "default_height_cm", default_height_cm) or default_height_cm
        except Exception:
            pass

        # Width control
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setDecimals(1)
        self.width_spin.setSingleStep(0.1)
        self.width_spin.setRange(MIN_CHART_WIDTH_CM, MAX_CHART_WIDTH_CM)
        self.width_spin.setValue(default_width_cm)
        self.width_spin.setSuffix(" cm")
        self.width_spin.setToolTip("Chart width in centimeters")
        self.width_spin.valueChanged.connect(self._on_size_changed)
        self.preview_toolbar.addWidget(self.width_spin)

        self.multiply_label = QLabel("×")
        self.preview_toolbar.addWidget(self.multiply_label)

        # Height control
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setDecimals(1)
        self.height_spin.setSingleStep(0.1)
        self.height_spin.setRange(MIN_CHART_HEIGHT_CM, MAX_CHART_HEIGHT_CM)
        self.height_spin.setValue(default_height_cm)
        self.height_spin.setSuffix(" cm")
        self.height_spin.setToolTip("Chart height in centimeters")
        self.height_spin.valueChanged.connect(self._on_size_changed)
        self.preview_toolbar.addWidget(self.height_spin)

        # Chart canvas
        self.chart_canvas = ChartCanvas(
            width=cm_to_inches(default_width_cm), height=cm_to_inches(default_height_cm), dpi=dpi)
        self.chart_canvas.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Combine our chart-action toolbar and matplotlib's pan/zoom/save
        # toolbar into a single row instead of stacking them, to save space.
        toolbar_row = QHBoxLayout()
        toolbar_row.setContentsMargins(0, 0, 0, 0)
        toolbar_row.setSpacing(4)
        toolbar_row.addWidget(self.preview_toolbar)
        if hasattr(self.chart_canvas, "navigation_toolbar"):
            nav_toolbar = self.chart_canvas.navigation_toolbar
            nav_toolbar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            toolbar_row.addWidget(nav_toolbar)
        toolbar_row.addStretch()
        preview_layout.addLayout(toolbar_row)

        # Wrap chart canvas in scroll area for large charts
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidgetResizable(False)
        canvas_scroll.setWidget(self.chart_canvas)
        canvas_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canvas_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.canvas_scroll = canvas_scroll
        preview_layout.addWidget(canvas_scroll)

        layout.addWidget(self.preview_frame)

    def create_status_section(self, layout):
        """Create the status section."""
        self.status_frame = QFrame()
        # Set fixed height to prevent expansion
        self.status_frame.setFixedHeight(30)
        self.status_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(8, 1, 8, 1)
        status_layout.setSpacing(4)

        datasets = self.chart.get_all_datasets()
        dataset_text = f"Datasets: {', '.join(datasets)}" if datasets else "Sample Data"
        self.dataset_label = QLabel(dataset_text)
        status_layout.addWidget(self.dataset_label)

        status_layout.addStretch()

        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        layout.addWidget(self.status_frame)

    def create_chart_toolbar_actions(self, toolbar):
        """Create toolbar actions for chart operations."""
        # Reset action
        reset_action = QAction("🔄 Reset", self)
        reset_action.triggered.connect(self.reset_chart)
        toolbar.addAction(reset_action)

        # Reset zoom button (the nav toolbar's own Home/Back/Forward are
        # removed since they rely on a view stack that goes stale whenever
        # the chart re-renders; this uses the chart's own tracked limits)
        reset_zoom_action = QAction("🔍 Reset Zoom", self)
        reset_zoom_action.setToolTip("Reset chart zoom to fit all data")
        reset_zoom_action.triggered.connect(self._on_reset_zoom)
        toolbar.addAction(reset_zoom_action)

    def load_chart_config(self):
        """Load chart configuration into UI controls."""
        # No configuration UI to load since it's now in the side panel
        pass

    def update_chart(self):
        """Update the chart preview."""
        # Guard: Check if widget still exists
        if not isValid(self.chart_canvas):
            self.logger.debug("Chart canvas already deleted, skipping update")
            return

        # Mapping from model string values to matplotlib parameters
        _marker_map = {
            "circle": "o", "square": "s", "triangle": "^", "diamond": "D",
            "star": "*", "plus": "+", "cross": "x", "none": "",
        }
        _linestyle_map = {
            "solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-.", "none": "none",
        }

        try:
            # Clear the current plot
            self.chart_canvas.axes.clear()

            # Set up (or tear down) the secondary Y axis depending on whether
            # any series is currently routed to it.
            needs_secondary = any(series.y_axis == "secondary" for series in self.chart.data_series)
            if needs_secondary:
                if self.chart_canvas.axes2 is None:
                    self.chart_canvas.axes2 = self.chart_canvas.axes.twinx()
                else:
                    self.chart_canvas.axes2.clear()
            elif self.chart_canvas.axes2 is not None:
                self.chart_canvas.axes2.remove()
                self.chart_canvas.axes2 = None
                self.chart_canvas.original_ylim2 = None

            series_errors = []
            if not self.chart.data_series:
                self.dataset_label.setText("No Data Loaded")
            else:
                project = self.app_context.get_app_state().current_project
                for i, series in enumerate(self.chart.data_series):
                    # Route this series to its configured Y axis
                    target_axes = (self.chart_canvas.axes2
                                   if series.y_axis == "secondary" and self.chart_canvas.axes2 is not None
                                   else self.chart_canvas.axes)

                    x_data, y_data, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(
                        project, series, self.chart.chart_type)
                    if error:
                        series_errors.append(
                            f"{series.label or f'Series {i + 1}'}: {error}")
                        continue

                    alpha = series.alpha if series.visible else 0.3
                    if self.chart.chart_type == "line":
                        mfc = series.marker_color or series.color
                        mec = series.marker_edge_color or series.color
                        target_axes.plot(x_data, y_data,
                                         color=series.color,
                                         linewidth=series.line_width,
                                         linestyle=_linestyle_map.get(series.line_style, "-"),
                                         marker=_marker_map.get(series.marker_style, "o"),
                                         markersize=series.marker_size,
                                         markerfacecolor=mfc,
                                         markeredgecolor=mec,
                                         label=series.label,
                                         alpha=alpha)
                    elif self.chart.chart_type == "scatter":
                        mfc = series.marker_color or series.color
                        mec = series.marker_edge_color or series.color
                        target_axes.scatter(x_data, y_data,
                                            c=mfc,
                                            edgecolors=mec,
                                            marker=_marker_map.get(series.marker_style, "o"),
                                            s=series.marker_size ** 2,
                                            label=series.label,
                                            alpha=alpha)
                    elif self.chart.chart_type == "bar":
                        target_axes.bar(x_data, y_data,
                                        color=series.color,
                                        label=series.label,
                                        alpha=alpha)
                    elif self.chart.chart_type == "hist":
                        self.chart_canvas.axes.hist(y_data, bins=self.chart.config.get("hist_bins", 20),
                                                    color=series.color,
                                                    label=series.label,
                                                    alpha=alpha)

                    if self.chart.chart_type in ("line", "scatter", "bar"):
                        xerr = build_error_array(x_err, x_err_minus, series.error_direction, series.error_symmetric)
                        yerr = build_error_array(y_err, y_err_minus, series.error_direction, series.error_symmetric)
                        if xerr is not None or yerr is not None:
                            err_color = series.error_color or series.color
                            self.chart_canvas.axes.errorbar(
                                x_data, y_data,
                                xerr=xerr,
                                yerr=yerr,
                                fmt="none",
                                ecolor=err_color,
                                elinewidth=series.line_width,
                                capsize=series.error_cap_size,
                                alpha=alpha)

                # Plot fit data from chart.fit_data, routed to the same axis as
                # the data series it was fitted from (if that series uses the
                # secondary Y axis).
                for i, fit in enumerate(self.chart.fit_data):
                    if fit.visible:
                        fit_axes = self.chart_canvas.axes
                        if self.chart_canvas.axes2 is not None:
                            for series in self.chart.data_series:
                                if (series.y_axis == "secondary"
                                        and series.dataset_id == fit.source_dataset_id
                                        and series.x_column == fit.source_x_column
                                        and series.y_column == fit.source_y_column):
                                    fit_axes = self.chart_canvas.axes2
                                    break

                        # Plot the fit line
                        fit_axes.plot(fit.x_data, fit.y_data,
                                     color=fit.color,
                                     linewidth=fit.line_width,
                                     linestyle=_linestyle_map.get(fit.line_style, "--"),
                                     label=fit.label,
                                     alpha=1.0)
                        self.chart_canvas.axes.plot(fit.x_data, fit.y_data,
                                                    color=fit.color,
                                                    linewidth=fit.line_width,
                                                    linestyle=_linestyle_map.get(fit.line_style, "--"),
                                                    label=fit.label,
                                                    alpha=1.0)
                        # Plot confidence band if available
                        if fit.confidence_lower is not None and fit.confidence_upper is not None:
                            self.chart_canvas.axes.fill_between(
                                fit.x_data,
                                fit.confidence_lower,
                                fit.confidence_upper,
                                color=fit.color,
                                alpha=0.2)

            # Apply chart configuration
            config = self.chart.config
            self.chart_canvas.axes.set_title(config.get(
                "title", self.chart.name), fontsize=14, fontweight="bold")
            self.chart_canvas.axes.set_xlabel(config.get("x_label", ""))
            self.chart_canvas.axes.set_ylabel(config.get("y_label", ""))
            self.chart_canvas.axes.set_xscale(config.get("x_scale", "linear"))
            self.chart_canvas.axes.set_yscale(config.get("y_scale", "linear"))
            self.chart_canvas.axes.xaxis.label.set_size(config.get("x_font_size", 12))
            self.chart_canvas.axes.yaxis.label.set_size(config.get("y_font_size", 12))

            if self.chart_canvas.axes2 is not None:
                self.chart_canvas.axes2.set_ylabel(config.get("y2_label", ""))

            if not config.get("x_auto_limits", True):
                self.chart_canvas.axes.set_xlim(config.get("x_min", 0.0), config.get("x_max", 1.0))
            if not config.get("y_auto_limits", True):
                self.chart_canvas.axes.set_ylim(config.get("y_min", 0.0), config.get("y_max", 1.0))

            apply_axis_ticks(
                self.chart_canvas.axes.xaxis,
                config.get("x_tick_mode", "auto"), config.get("x_tick_count", 5),
                config.get("x_tick_step", 1.0), config.get("x_tick_format", "auto"),
                config.get("x_tick_format_custom", ""))
            apply_axis_ticks(
                self.chart_canvas.axes.yaxis,
                config.get("y_tick_mode", "auto"), config.get("y_tick_count", 5),
                config.get("y_tick_step", 1.0), config.get("y_tick_format", "auto"),
                config.get("y_tick_format_custom", ""))

            grid_alpha = config.get("grid_alpha", 0.3)
            if config.get("show_grid_x", True):
                self.chart_canvas.axes.grid(True, axis="x", alpha=grid_alpha)
            else:
                self.chart_canvas.axes.grid(False, axis="x")
            if config.get("show_grid_y", True):
                self.chart_canvas.axes.grid(True, axis="y", alpha=grid_alpha)
            else:
                self.chart_canvas.axes.grid(False, axis="y")

            if config.get("show_legend", True) and (self.chart.data_series or self.chart.fit_data):
                # Combine handles/labels from both axes since twinx() legends
                # are independent by default.
                handles, labels = self.chart_canvas.axes.get_legend_handles_labels()
                if self.chart_canvas.axes2 is not None:
                    handles2, labels2 = self.chart_canvas.axes2.get_legend_handles_labels()
                    handles += handles2
                    labels += labels2
                self.chart_canvas.axes.legend(
                    handles, labels,
                    loc=config.get("legend_position", "upper right"),
                    fontsize=config.get("legend_font_size", 10),
                    facecolor=config.get("legend_bg_color", "#ffffff"),
                    frameon=config.get("legend_show_frame", True))

            if self.chart_canvas.axes2 is not None:
                # Reserve room for the secondary axis label/ticks so they
                # aren't clipped at the right edge of the figure.
                self.chart_canvas.fig.tight_layout()

            # Store original limits for zoom reset functionality
            self.chart_canvas.store_original_limits()

            # Refresh canvas
            self.chart_canvas.draw()

            if series_errors:
                self.update_status("Skipped: " + "; ".join(series_errors))
            else:
                self.update_status("Ready")

        except Exception as e:
            self.logger.exception("Error updating chart")
            self.update_status(f"Chart error: {str(e)}")

    def reset_chart(self):
        """Reset chart to default configuration."""
        self.chart._init_default_config()
        self.update_chart()
        self.update_status("Reset to defaults ✓")

        # Reset status after 2 seconds
        QTimer.singleShot(2000, lambda: self.update_status("Ready"))

    def update_status(self, status: str):
        """Update the status label."""
        # Guard: Check if widget still exists
        if not isValid(self.status_label):
            return

        self.status_label.setText(status)
        self._update_status_label_style()

    def _apply_initial_fit_size(self):
        """Size a freshly opened chart to fill the visible preview panel.

        Runs once, shortly after construction, once the scroll area has a
        real viewport size to measure. Has no effect if the widget was
        already closed or the panel hasn't been laid out yet.
        """
        if not isValid(self.canvas_scroll) or not isValid(self.chart_canvas):
            return

        viewport = self.canvas_scroll.viewport()
        width_px = viewport.width()
        height_px = viewport.height()
        if width_px <= 0 or height_px <= 0:
            return

        width_cm, height_cm = fit_size_cm(
            width_px, height_px, self.chart_canvas.fig.dpi,
            min_width_cm=self.width_spin.minimum(), max_width_cm=self.width_spin.maximum(),
            min_height_cm=self.height_spin.minimum(), max_height_cm=self.height_spin.maximum())

        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.width_spin.setValue(width_cm)
        self.height_spin.setValue(height_cm)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self._on_size_changed()

    def _on_size_changed(self):
        """Handle chart size changes."""
        if hasattr(self, "chart_canvas"):
            try:
                width = cm_to_inches(self.width_spin.value())
                height = cm_to_inches(self.height_spin.value())
                self.chart_canvas.set_size(width, height)
                self.update_status("Chart size updated")
            except Exception as e:
                self.update_status(f"Resize error: {str(e)}")

            # Reset status after 2 seconds
            QTimer.singleShot(2000, lambda: self.update_status("Ready"))

    def _on_reset_zoom(self):
        """Handle reset zoom action."""
        if hasattr(self, "chart_canvas"):
            try:
                self.chart_canvas.reset_zoom()
                self.update_status("Zoom reset")
            except Exception as e:
                self.update_status(f"Zoom reset error: {str(e)}")

            # Reset status after 2 seconds
            QTimer.singleShot(2000, lambda: self.update_status("Ready"))

    def get_chart(self) -> Chart:
        """Get the current chart object."""
        return self.chart

    def refresh_chart(self):
        """Refresh the chart preview when configuration changes from external sources."""
        # Guard: Check if widget still exists
        if not isValid(self.chart_canvas):
            return

        self.update_chart()

        # Update dataset label in status
        datasets = self.chart.get_all_datasets()
        dataset_text = f"Datasets: {', '.join(datasets)}" if datasets else "Sample Data"
        self.dataset_label.setText(dataset_text)
