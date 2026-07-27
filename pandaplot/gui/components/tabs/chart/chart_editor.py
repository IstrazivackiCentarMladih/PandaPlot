from dataclasses import dataclass
from typing import Any, Optional, override

from matplotlib.ticker import (
    AutoLocator,
    AutoMinorLocator,
    FuncFormatter,
    MaxNLocator,
    MultipleLocator,
    NullLocator,
    ScalarFormatter,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
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
from pandaplot.gui.components.tabs.chart.chart_error_bars import build_error_array
from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.events.event_types import ConfigEvents
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.config import (
    MAX_CHART_HEIGHT_CM,
    MAX_CHART_WIDTH_CM,
    MIN_CHART_HEIGHT_CM,
    MIN_CHART_WIDTH_CM,
)
from pandaplot.services.config.config_manager import ConfigManager
from pandaplot.services.theme.theme_manager import ThemeManager


def apply_chart_title(
    axes,
    title: str,
    subtitle: str,
    title_font_size: float,
    subtitle_font_size: float,
    title_padding: float = 6.0,
    main_title_padding: float = 10.0,
    fig_height_inches: float | None = None,
    title_bold: bool = True,
    title_italic: bool = False,
    subtitle_bold: bool = False,
    subtitle_italic: bool = False,
) -> None:
    """Render the title (figure-level) and subtitle (axes-level) as two
    independent Matplotlib Text artists so each can have its own font size
    -- a single set_title() call can't mix font sizes within one string.

    `title_padding` is the gap (in points) between the plot area and the
    subtitle/title block, matching Axes.set_title's own `pad` parameter
    (rcParam `axes.titlepad` default: 6.0).

    `main_title_padding` is the gap (in points) between the top edge of the
    figure and the main title. Figure.suptitle() has no `pad` parameter of
    its own -- it's positioned via `y`, a 0-1 fraction of the figure height
    (fixed default 0.98) -- so the points value is converted to that
    fraction, keeping the same points-based unit the subtitle's padding
    uses. `fig_height_inches` should be the figure's TARGET height (the one
    about to be applied via ChartCanvas.set_size(), which callers must
    resolve before calling this), not necessarily its current height -- the
    conversion is wrong if the figure is resized afterward using a
    different height than was used here. Defaults to the figure's current
    height when not given (e.g. in tests using a bare Figure/Axes).

    When `title`/`subtitle` is empty, that artist's text is cleared instead
    of being (re)positioned, so an absent title/subtitle doesn't leave a
    stale reserved-looking gap where it used to be."""
    fig = axes.figure

    if title:
        height = fig_height_inches if fig_height_inches is not None else fig.get_figheight()
        y = 1.0 - (main_title_padding / 72.0) / height if height else 0.98
        fig.suptitle(
            title, fontsize=title_font_size, y=y,
            fontweight="bold" if title_bold else "normal",
            fontstyle="italic" if title_italic else "normal",
        )
    elif fig._suptitle is not None:
        fig._suptitle.set_text("")

    axes.set_title(
        subtitle, fontsize=subtitle_font_size, pad=title_padding,
        fontweight="bold" if subtitle_bold else "normal",
        fontstyle="italic" if subtitle_italic else "normal",
    )


def resolve_chart_size(
    chart_width_cm, chart_height_cm, chart_dpi,
    default_width_cm: float, default_height_cm: float, default_dpi: int,
) -> tuple[float, float, int]:
    """Resolve effective (width_cm, height_cm, dpi), preferring per-chart
    overrides and falling back to the app-wide Settings defaults for any
    value left as None."""
    width = chart_width_cm if chart_width_cm is not None else default_width_cm
    height = chart_height_cm if chart_height_cm is not None else default_height_cm
    dpi = chart_dpi if chart_dpi is not None else default_dpi
    return width, height, dpi


def apply_axis_ticks(
    axis, mode, count, step, fmt, custom_fmt,
    direction="out", minor_enabled=False, minor_direction=None,
    major_color="#000000", minor_color="#000000",
):
    """Apply tick placement, label formatting, direction, and minor ticks to
    a matplotlib Axis.

    axis: a matplotlib Axis object (e.g. ax.xaxis or ax.yaxis)
    mode: "auto" | "count" | "step" - tick placement strategy
    count: number of ticks when mode == "count"
    step: fixed spacing between ticks when mode == "step"
    fmt: "auto" | "integer" | "1decimal" | "2decimal" | "scientific" | "custom"
    custom_fmt: a Python format spec (e.g. "{:.2f}") used when fmt == "custom"
    direction: "out" | "in" | "inout" - which way major ticks point
    minor_enabled: whether minor ticks are shown between the major ones
    minor_direction: "out" | "in" | "inout" - which way minor ticks point,
        independent of major `direction`. Defaults to `direction` when not
        given (e.g. in tests that only care about major-tick behavior).
    major_color: color of the major tick marks
    minor_color: color of the minor tick marks
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

    axis.set_minor_locator(AutoMinorLocator() if minor_enabled else NullLocator())
    axis.set_tick_params(which="major", direction=direction, color=major_color)
    axis.set_tick_params(
        which="minor",
        direction=minor_direction if minor_direction is not None else direction,
        color=minor_color,
    )


def apply_spine_colors(axes, axes2, x_color, y_color, y2_color):
    """Color the axis box lines ('spines'). Bottom/top belong to x, left
    belongs to y. Right belongs to y2 when a secondary y axis is active,
    otherwise to y. When axes2 exists (twinx()), it draws its own full
    spine box on top of axes, so its bottom/top/left must be kept in sync
    with axes's x/y colors or they'd visually override them with black.
    axes's own right spine is always kept on y_color too; when axes2 is
    present it is visually covered by axes2's right spine (set to
    y2_color), but keeping it in sync avoids a stray black edge showing
    through and keeps axes internally consistent."""
    axes.spines["bottom"].set_color(x_color)
    axes.spines["top"].set_color(x_color)
    axes.spines["left"].set_color(y_color)
    axes.spines["right"].set_color(y_color)
    if axes2 is not None:
        axes2.spines["bottom"].set_color(x_color)
        axes2.spines["top"].set_color(x_color)
        axes2.spines["left"].set_color(y_color)
        axes2.spines["right"].set_color(y2_color)


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

        # Apply theme to chart canvas navigation if it exists
        self.chart_canvas.apply_navigation_theme(base_fg, card_bg, card_border)

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
                self.chart_canvas.set_dpi(
                    dpi,
                    pad=self.chart.config.get("chart_padding", 2.0),
                    w_pad=self.chart.config.get("chart_padding_w", 2.0),
                    h_pad=self.chart.config.get("chart_padding_h", 2.0),
                    top_margin=self.chart.config.get("top_margin", 1.0),
                )
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

        # Resolve the initial canvas size/DPI, preferring per-chart overrides
        # (chart.config) over the app-wide Settings defaults fetched above.
        width_cm, height_cm, dpi = resolve_chart_size(
            self.chart.config.get("width_cm"), self.chart.config.get("height_cm"),
            self.chart.config.get("dpi"), default_width_cm, default_height_cm, dpi,
        )

        # Chart canvas
        self.chart_canvas = ChartCanvas(
            width=cm_to_inches(width_cm), height=cm_to_inches(height_cm), dpi=dpi)
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

            fig_bg = self.chart.style.get("figure_background_color", "#ffffff")
            axes_bg = self.chart.style.get("axes_background_color", "#ffffff")
            self.chart_canvas.fig.set_facecolor(fig_bg if fig_bg is not None else "none")
            self.chart_canvas.axes.set_facecolor(axes_bg if axes_bg is not None else "none")

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

                    series_data = resolve_series_data(project, series, self.chart.chart_type)
                    x_data = series_data.x_data
                    y_data = series_data.y_data
                    x_err = series_data.x_err
                    y_err = series_data.y_err
                    x_err_minus = series_data.x_err_minus
                    y_err_minus = series_data.y_err_minus
                    error = series_data.error
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
                                         markeredgewidth=series.marker_edge_width,
                                         label=series.label,
                                         alpha=alpha)
                    elif self.chart.chart_type == "scatter":
                        mfc = series.marker_color or series.color
                        mec = series.marker_edge_color or series.color
                        target_axes.scatter(x_data, y_data,
                                            c=mfc,
                                            edgecolors=mec,
                                            linewidths=series.marker_edge_width,
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
                        target_axes.hist(y_data, bins=self.chart.config.get("hist_bins", 20),
                                         color=series.color,
                                         label=series.label,
                                         alpha=alpha)

                    if self.chart.chart_type in ("line", "scatter", "bar"):
                        xerr = build_error_array(x_err, x_err_minus, series.error_direction, series.error_symmetric)
                        yerr = build_error_array(y_err, y_err_minus, series.error_direction, series.error_symmetric)
                        if xerr is not None or yerr is not None:
                            err_color = series.error_color or series.color
                            target_axes.errorbar(
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
                for fit in self.chart.fit_data:
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
                        # Plot confidence band if available
                        if fit.confidence_lower is not None and fit.confidence_upper is not None:
                            # Plot confidence band on the same axis as the fitted curve.
                            fit_axes.fill_between(
                                fit.x_data,
                                fit.confidence_lower,
                                fit.confidence_upper,
                                color=fit.color,
                                alpha=0.2)

            # Apply chart configuration
            config = self.chart.config

            # Resolve the target figure size *before* applying the title:
            # main_title_padding's points-to-fraction conversion needs the
            # height the figure is about to be set to, not whatever height
            # it happened to have from the previous render.
            cfg_manager = self.app_context.get_manager(ConfigManager)
            display_cfg = getattr(getattr(cfg_manager, "config", None), "chart_display", None)
            default_width = getattr(display_cfg, "default_width_cm", 20.0) if display_cfg else 20.0
            default_height = getattr(display_cfg, "default_height_cm", 15.0) if display_cfg else 15.0
            default_dpi = getattr(display_cfg, "dpi", 100) if display_cfg else 100
            width_cm, height_cm, dpi = resolve_chart_size(
                config.get("width_cm"), config.get("height_cm"), config.get("dpi"),
                default_width, default_height, default_dpi,
            )

            apply_chart_title(
                self.chart_canvas.axes,
                title=config.get("title", self.chart.name),
                subtitle=config.get("subtitle", ""),
                title_font_size=config.get("title_font_size", 14),
                subtitle_font_size=config.get("subtitle_font_size", 12),
                title_padding=config.get("title_padding", 6.0),
                main_title_padding=config.get("main_title_padding", 10.0),
                fig_height_inches=cm_to_inches(height_cm),
                title_bold=config.get("title_bold", True),
                title_italic=config.get("title_italic", False),
                subtitle_bold=config.get("subtitle_bold", False),
                subtitle_italic=config.get("subtitle_italic", False),
            )

            chart_padding = config.get("chart_padding", 2.0)
            chart_padding_w = config.get("chart_padding_w", 2.0)
            chart_padding_h = config.get("chart_padding_h", 2.0)
            top_margin = config.get("top_margin", 1.0)
            self.chart_canvas.set_size(
                cm_to_inches(width_cm), cm_to_inches(height_cm),
                pad=chart_padding, w_pad=chart_padding_w, h_pad=chart_padding_h, top_margin=top_margin,
            )
            self.chart_canvas.set_dpi(
                dpi, pad=chart_padding, w_pad=chart_padding_w, h_pad=chart_padding_h, top_margin=top_margin,
            )

            self.chart_canvas.axes.set_xlabel(config.get("x_label", ""))
            self.chart_canvas.axes.set_ylabel(config.get("y_label", ""))
            self.chart_canvas.axes.set_xscale(config.get("x_scale", "linear"))
            self.chart_canvas.axes.set_yscale(config.get("y_scale", "linear"))
            self.chart_canvas.axes.xaxis.label.set_size(config.get("x_font_size", 12))
            self.chart_canvas.axes.yaxis.label.set_size(config.get("y_font_size", 12))
            if config.get("y_side", "left") == "right":
                self.chart_canvas.axes.yaxis.tick_right()
                self.chart_canvas.axes.yaxis.set_label_position("right")
            else:
                self.chart_canvas.axes.yaxis.tick_left()
                self.chart_canvas.axes.yaxis.set_label_position("left")

            if self.chart_canvas.axes2 is not None:
                self.chart_canvas.axes2.set_ylabel(config.get("y2_label", ""))
                self.chart_canvas.axes2.set_yscale(config.get("y2_scale", "linear"))
                self.chart_canvas.axes2.yaxis.label.set_size(config.get("y2_font_size", 12))
                if config.get("y2_side", "right") == "left":
                    self.chart_canvas.axes2.yaxis.tick_left()
                    self.chart_canvas.axes2.yaxis.set_label_position("left")
                else:
                    self.chart_canvas.axes2.yaxis.tick_right()
                    self.chart_canvas.axes2.yaxis.set_label_position("right")

                if not config.get("y2_auto_limits", True):
                    self.chart_canvas.axes2.set_ylim(
                        config.get("y2_min", 0.0), config.get("y2_max", 1.0))

                apply_axis_ticks(
                    self.chart_canvas.axes2.yaxis,
                    config.get("y2_tick_mode", "auto"), config.get("y2_tick_count", 5),
                    config.get("y2_tick_step", 1.0), config.get("y2_tick_format", "auto"),
                    config.get("y2_tick_format_custom", ""),
                    direction=config.get("y2_tick_direction", "out"),
                    minor_enabled=config.get("y2_minor_ticks", False),
                    minor_direction=config.get("y2_minor_tick_direction", "out"),
                    major_color=config.get("y2_major_tick_color", "#000000"),
                    minor_color=config.get("y2_minor_tick_color", "#000000"))

                if config.get("show_grid_y2", True):
                    self.chart_canvas.axes2.grid(True, axis="y", alpha=config.get("grid_alpha", 0.3))
                else:
                    self.chart_canvas.axes2.grid(False, axis="y")

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
                config.get("x_tick_format_custom", ""),
                direction=config.get("x_tick_direction", "out"),
                minor_enabled=config.get("x_minor_ticks", False),
                minor_direction=config.get("x_minor_tick_direction", "out"),
                major_color=config.get("x_major_tick_color", "#000000"),
                minor_color=config.get("x_minor_tick_color", "#000000"))
            apply_axis_ticks(
                self.chart_canvas.axes.yaxis,
                config.get("y_tick_mode", "auto"), config.get("y_tick_count", 5),
                config.get("y_tick_step", 1.0), config.get("y_tick_format", "auto"),
                config.get("y_tick_format_custom", ""),
                direction=config.get("y_tick_direction", "out"),
                minor_enabled=config.get("y_minor_ticks", False),
                minor_direction=config.get("y_minor_tick_direction", "out"),
                major_color=config.get("y_major_tick_color", "#000000"),
                minor_color=config.get("y_minor_tick_color", "#000000"))

            apply_spine_colors(
                self.chart_canvas.axes, self.chart_canvas.axes2,
                config.get("x_spine_color", "#000000"),
                config.get("y_spine_color", "#000000"),
                config.get("y2_spine_color", "#000000"))

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
                    frameon=config.get("legend_show_frame", True),
                    ncol=config.get("legend_columns", 1),
                    framealpha=config.get("legend_bg_alpha", 1.0))

            if self.chart_canvas.axes2 is not None:
                # Reserve room for the secondary axis label/ticks so they
                # aren't clipped at the right edge of the figure.
                self.chart_canvas.fig.tight_layout(
                    pad=config.get("chart_padding", 2.0),
                    w_pad=config.get("chart_padding_w", 2.0),
                    h_pad=config.get("chart_padding_h", 2.0),
                    rect=(0, 0, 1, config.get("top_margin", 1.0)),
                )

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
        already closed or the panel hasn't been laid out yet, or if this
        chart already has a per-chart width/height saved in its config
        (in which case that saved size takes precedence and must not be
        overwritten by the fit-to-panel heuristic).
        """
        if not isValid(self.canvas_scroll) or not isValid(self.chart_canvas):
            return

        if self.chart.config.get("width_cm") is not None or self.chart.config.get("height_cm") is not None:
            return

        viewport = self.canvas_scroll.viewport()
        width_px = viewport.width()
        height_px = viewport.height()
        if width_px <= 0 or height_px <= 0:
            return

        width_cm, height_cm = fit_size_cm(
            width_px, height_px, self.chart_canvas.fig.dpi,
            min_width_cm=MIN_CHART_WIDTH_CM, max_width_cm=MAX_CHART_WIDTH_CM,
            min_height_cm=MIN_CHART_HEIGHT_CM, max_height_cm=MAX_CHART_HEIGHT_CM)

        self.chart.config["width_cm"] = width_cm
        self.chart.config["height_cm"] = height_cm
        self.update_chart()

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
