"""Chart properties side panel for configuring chart appearance and data."""
from typing import List, Optional, override

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pandaplot.commands.project.chart import (
    AddSeriesCommand,
    ApplyChartPropertiesCommand,
    RemoveFitDataCommand,
    RemoveSeriesCommand,
)
from pandaplot.gui.components.common.card import Card
from pandaplot.gui.components.common.chip_row import ChipRow
from pandaplot.gui.components.common.color_swatch_row import ColorSwatchRow
from pandaplot.gui.components.common.dirty_footer import DirtyFooter
from pandaplot.gui.components.common.line_style_icons import build_line_style_icon
from pandaplot.gui.components.common.section_header import SectionHeader
from pandaplot.gui.components.common.segmented_control import SegmentedControl
from pandaplot.gui.components.common.slider_with_spinbox import SliderWithSpinbox
from pandaplot.gui.components.common.toggle_switch import ToggleSwitch
from pandaplot.gui.components.common.value_combo_box import ValueComboBox
from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.chart.chart_configuration import (
    ChartType,
    LegendPosition,
    LineStyleType,
    MarkerType,
    ScaleType,
)
from pandaplot.models.events import ChartEvents, ProjectEvents, UIEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import YAxis, restore_chart_state, snapshot_chart_state
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.config import (
    MAX_CHART_HEIGHT_CM,
    MAX_CHART_WIDTH_CM,
    MIN_CHART_HEIGHT_CM,
    MIN_CHART_WIDTH_CM,
)
from pandaplot.services.config.config_manager import ConfigManager
from pandaplot.services.theme.theme_manager import ThemeManager

# Only chart types that ChartEditorWidget.update_chart can actually render.
# BOX and VIOLIN exist in the enum but have no rendering branch yet.
IMPLEMENTED_CHART_TYPES = [
    ChartType.LINE,
    ChartType.SCATTER,
    ChartType.BAR,
    ChartType.HISTOGRAM,
]

# Preset swatch palette offered by the Style tab's line/marker color pickers.
STYLE_SWATCH_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


class ChartPropertiesPanel(PWidget):
    """Side panel for configuring chart properties."""

    def __init__(self, app_context: AppContext, parent: Optional[QWidget] = None):
        super().__init__(app_context=app_context, parent=parent)
        self.command_executor = app_context.command_executor
        self.current_project = None
        self.current_chart = None  # Current Chart object being edited
        self.datasets: List = []
        # Internal flags/state for safe UI updates
        self._updating_controls: bool = False  # Guard to prevent feedback loops
        self._pending_label: str = ""        # Buffer while user types label
        self._has_unsaved_changes: bool = False
        # Baseline for Cancel and for Apply's undo: the chart state as of the
        # last load into this panel or the last Apply.
        self._loaded_snapshot: Optional[dict] = None
        # Tracks whether the loaded chart's type is one the combo can
        # represent, so an unsupported/hidden type (e.g. a saved "box" or
        # "violin" chart) isn't silently overwritten with "line" just
        # because that's what the combo defaults to for display.
        self._loaded_chart_type_supported: bool = True
        self._chart_type_touched_by_user: bool = False
        # Whether the Custom size/DPI fields have already been pre-filled
        # for the currently loaded chart (reset on every load_chart_object/
        # _clear_controls call). Prevents re-filling with defaults if the
        # user toggles back and forth between Custom and a preset.
        self._custom_size_prefilled: bool = False
        self._custom_dpi_prefilled: bool = False
        # Reference to the expanded Data-tab card's Y1/Y2 badge QLabel (and
        # the design tokens it was last styled with), so a live series
        # Y-axis edit can restyle it in place. See _on_series_config_changed.
        self._expanded_card_y_axis_badge: Optional[QLabel] = None
        self._expanded_card_y_axis_badge_tokens: dict = {}
        # Which entry (data series index, then fit-data index appended after
        # all series) is currently shown expanded in the Data tab's card list.
        self._expanded_series_index: int = 0

        self._initialize()
        self._connect_signals()
    
    @override
    def _init_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.title_label = QLabel("📊 Chart Properties", self)
        layout.addWidget(self.title_label)

        # Tab widget for organizing chart properties
        self.tab_widget = QTabWidget(self)

        # Chart tab: chart identity (title, chart type, histogram bins)
        chart_tab = QWidget()
        chart_tab_layout = QVBoxLayout(chart_tab)
        self._create_chart_info_section(chart_tab_layout)
        chart_tab_layout.addStretch(1)
        self.chart_tab = chart_tab
        self.tab_widget.addTab(self.chart_tab, "Chart")

        # Data tab: series list + per-series dataset/X/Y/label configuration
        data_tab = QWidget()
        data_tab_layout = QVBoxLayout(data_tab)
        self._create_series_management_section(data_tab_layout)
        data_tab_layout.addStretch(1)
        self.data_tab = data_tab
        self.tab_widget.addTab(self.data_tab, "Data")

        # Style tab (line/marker style)
        self.style_tab = self._create_style_tab()
        self.tab_widget.addTab(self.style_tab, "Style")

        # Axes tab
        self.axes_tab = self._create_axes_tab()
        self.tab_widget.addTab(self.axes_tab, "Axes")

        # Legend tab
        self.legend_tab = self._create_legend_tab()
        self.tab_widget.addTab(self.legend_tab, "Legend")

        layout.addWidget(self.tab_widget, stretch=1)

        # Footer: dirty-state indicator + Revert/Apply
        self.footer = DirtyFooter(self)
        self.footer.applyClicked.connect(self._on_apply)
        self.footer.revertClicked.connect(self._on_reset)
        layout.addWidget(self.footer)
    
    @override
    def _apply_theme(self):
        """Apply theme styling to all components."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        
        # Get theme colors with fallbacks
        card_bg = palette.get("card_bg", "#ffffff")
        card_border = palette.get("card_border", "#dee2e6")
        base_fg = palette.get("base_fg", "#333333")
        card_hover = palette.get("card_hover", "#e5f3ff")
        
        # Apply theme to main widget
        self.setStyleSheet(f"""
            ChartPropertiesPanel {{
                background-color: {card_bg};
                color: {base_fg};
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 9pt;
                color: {base_fg};
                margin-top: 5px;
                padding-top: 10px;
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 4px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: {card_bg};
            }}
        """)
        
        # Title label with improved styling
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {base_fg};
                padding: 5px;
                background-color: {card_border};
                border-radius: 3px;
            }}
        """)
        
        # Tab widget with theme-aware colors
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 1px solid {card_border}; 
                top: 1px; 
                background: {card_bg}; 
            }}
            QTabBar::tab {{ 
                background: {card_hover}; 
                border: 1px solid {card_border}; 
                border-bottom: none; 
                padding: 4px 8px; 
                margin-right: 2px; 
                border-top-left-radius: 4px; 
                border-top-right-radius: 4px;
                color: {base_fg};
            }}
            QTabBar::tab:selected {{ 
                background: {card_bg}; 
                font-weight: bold; 
            }}
            QTabBar::tab:hover {{ 
                background: {card_hover}; 
            }}
        """)
        
        # Series management buttons
        self._apply_series_button_styling()

        # Footer (DirtyFooter) theme token propagation
        tokens = theme_manager.get_design_tokens()
        self.footer.set_tokens(tokens)
        self.chart_type_control.set_tokens(tokens)

        # Style tab: shared widgets
        self.style_series_chips.set_tokens(tokens)
        self.line_color_row.set_tokens(tokens)
        self.line_style_control.set_tokens(tokens)
        for _index in range(self.line_style_control.count()):
            _style = self.line_style_control.itemData(_index)
            self.line_style_control.setItemIcon(_index, build_line_style_icon(_style, tokens))
        self.line_width_slider.set_tokens(tokens)
        self.line_opacity_slider.set_tokens(tokens)
        self.markers_enabled_toggle.set_tokens(tokens)
        self.marker_shape_control.set_tokens(tokens)
        self.marker_size_slider.set_tokens(tokens)
        self.marker_color_row.set_tokens(tokens)
        self.marker_match_line_toggle.set_tokens(tokens)

        # Data tab: cards/SegmentedControl are rebuilt with fresh tokens
        # every time _rebuild_series_cards runs, so re-running it here is
        # the simplest way to make a live theme change reach them.
        self._series_section_header.set_tokens(tokens)
        self.series_y_axis_control.set_tokens(tokens)
        self._rebuild_series_cards()

        # Axes tab: chip row plus each axis form's Card/SegmentedControl/
        # ToggleSwitch/SectionHeader widgets.
        if hasattr(self, "axis_chips"):
            self.axis_chips.set_tokens(tokens)
        if hasattr(self, "axes_forms"):
            for form in self.axes_forms.values():
                form["scale_control"].set_tokens(tokens)
                if form["side_control"] is not None:
                    form["side_control"].set_tokens(tokens)
                form["range_card"].set_tokens(tokens)
                form["ticks_card"].set_tokens(tokens)
                form["mode_control"].set_tokens(tokens)
                form["auto_toggle"].set_tokens(tokens)
                form["grid_toggle"].set_tokens(tokens)

        # Legend tab: shared widgets
        self.show_legend_toggle.set_tokens(tokens)
        self.legend_columns_control.set_tokens(tokens)
        self.legend_show_frame_toggle.set_tokens(tokens)
        self.legend_bg_color_row.set_tokens(tokens)
        self.legend_bg_opacity_slider.set_tokens(tokens)

    def _apply_series_button_styling(self):
        """Apply theme styling to series management buttons."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        
        # Get colors with fallbacks
        accent = palette.get("accent", "#4CAF50")
        secondary_fg = palette.get("secondary_fg", "#666666")
        card_hover = palette.get("card_hover", "#e5f3ff")
        base_fg = palette.get("base_fg", "#333333")
        card_border = palette.get("card_border", "#dee2e6")
        card_bg = palette.get("card_bg", "#ffffff")
        
        # Add series button (primary style)
        add_style = f"""
            QPushButton {{ 
                background: {accent}; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                padding: 4px 10px;
            }}
            QPushButton:hover {{ 
                background: {card_hover}; 
                color: {base_fg}; 
            }}
            QPushButton:disabled {{ 
                background: {secondary_fg}; 
            }}
        """
        self.add_series_button.setStyleSheet(add_style)
        
        # Remove series button (secondary style)
        remove_style = f"""
            QPushButton {{ 
                background: {card_hover}; 
                color: {base_fg}; 
                border: 1px solid {card_border}; 
                border-radius: 4px; 
                padding: 4px 10px;
            }}
            QPushButton:hover {{ 
                background: {card_bg}; 
            }}
            QPushButton:disabled {{ 
                background: {card_hover}; 
                color: {secondary_fg}; 
            }}
        """
        self.remove_series_button.setStyleSheet(remove_style)

    def _create_chart_info_section(self, layout):
        """Create the basic chart information section."""
        # Chart info group
        info_group = QGroupBox("Chart Information")
        info_layout = QGridLayout(info_group)
        info_layout.setSpacing(8)

        info_layout.addWidget(QLabel("Title:"), 0, 0)
        self.title_edit = QLineEdit()
        info_layout.addWidget(self.title_edit, 0, 1, 1, 2)

        info_layout.addWidget(QLabel("Subtitle:"), 1, 0)
        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("Optional")
        info_layout.addWidget(self.subtitle_edit, 1, 1, 1, 2)

        info_layout.addWidget(QLabel("Type:"), 2, 0)
        self.chart_type_control = ValueComboBox(
            [
                ("Scatter", ChartType.SCATTER),
                ("Line", ChartType.LINE),
                ("Bar", ChartType.BAR),
                ("Histogram", ChartType.HISTOGRAM),
            ]
        )
        info_layout.addWidget(self.chart_type_control, 2, 1, 1, 2)

        self.hist_bins_label = QLabel("Bins:")
        info_layout.addWidget(self.hist_bins_label, 3, 0)
        self.hist_bins_spin = QSpinBox()
        self.hist_bins_spin.setRange(2, 200)
        self.hist_bins_spin.setValue(20)
        self.hist_bins_spin.setToolTip("Number of bins used when chart type is Histogram")
        info_layout.addWidget(self.hist_bins_spin, 3, 1)
        self._update_hist_bins_visibility()

        layout.addWidget(info_group)
    
    def _create_series_management_section(self, layout):
        """Create the data series management section: an expand/collapse card
        per series (plus any fit-data entries), backed by a single persistent
        configuration form that is reparented into whichever card is
        currently expanded (tracked by `self._expanded_series_index`).
        """
        header_row = QHBoxLayout()
        self._series_section_header = SectionHeader("Series")
        header_row.addWidget(self._series_section_header)
        header_row.addStretch(1)
        self.add_series_button = QPushButton("+ Add series")
        self.add_series_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_series_button.clicked.connect(self._add_series)
        header_row.addWidget(self.add_series_button)
        layout.addLayout(header_row)

        self._series_cards_container = QWidget()
        self._series_cards_layout = QVBoxLayout(self._series_cards_container)
        self._series_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._series_cards_layout.setSpacing(6)
        layout.addWidget(self._series_cards_container)

        self.remove_series_button = QPushButton("Remove selected series")
        self.remove_series_button.setMinimumHeight(28)
        self.remove_series_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_series_button.clicked.connect(self._remove_series)
        self.remove_series_button.setEnabled(False)
        layout.addWidget(self.remove_series_button)

        # Persistent configuration form (dataset/X/Y/Y-axis/label). Created
        # once so signal connections in _connect_signals stay valid for the
        # panel's lifetime; it gets moved (reparented) into whichever card is
        # currently expanded by _build_expanded_series_card.
        self._series_form_widget = QWidget()
        series_config_layout = QGridLayout(self._series_form_widget)
        series_config_layout.setContentsMargins(0, 0, 0, 0)

        series_config_layout.addWidget(QLabel("Dataset:"), 0, 0)
        self.dataset_combo = QComboBox()
        series_config_layout.addWidget(self.dataset_combo, 0, 1)

        series_config_layout.addWidget(QLabel("X Column:"), 1, 0)
        self.x_column_combo = QComboBox()
        series_config_layout.addWidget(self.x_column_combo, 1, 1)

        series_config_layout.addWidget(QLabel("Y Column:"), 2, 0)
        self.y_column_combo = QComboBox()
        series_config_layout.addWidget(self.y_column_combo, 2, 1)

        series_config_layout.addWidget(QLabel("Y Axis:"), 3, 0)
        self.series_y_axis_control = SegmentedControl(
            [("Y₁ left", YAxis.PRIMARY), ("Y₂ right", YAxis.SECONDARY)]
        )
        series_config_layout.addWidget(self.series_y_axis_control, 3, 1)

        series_config_layout.addWidget(QLabel("Label:"), 4, 0)
        self.series_label_edit = QLineEdit()
        series_config_layout.addWidget(self.series_label_edit, 4, 1)

        self._rebuild_series_cards()

    def _expand_series(self, index: int):
        """Expand the card at `index` (collapsing whichever was expanded)."""
        self._expanded_series_index = index
        self._rebuild_series_cards()

    def _rebuild_series_cards(self):
        """Rebuild the Data tab's card list from `self.current_chart`.

        Renders one collapsed row per data series / fit-data entry, except
        the entry at `self._expanded_series_index`, which gets the full
        configuration card (dataset/X/Y/Y-axis/label). Safe to call at any
        point: fetches fresh theme tokens, so this doubles as the mechanism
        by which cards pick up a live theme change (see `_apply_theme`).
        """
        # Detach the persistent form widget from whatever card currently
        # hosts it *before* that card is torn down below, so it survives
        # the rebuild instead of being deleted as a child of a discarded card.
        if self._series_form_widget.parent() is not None:
            self._series_form_widget.setParent(None)

        while self._series_cards_layout.count():
            item = self._series_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        theme_manager = self.app_context.get_manager(ThemeManager)
        tokens = theme_manager.get_design_tokens()

        if not self.current_chart:
            self.remove_series_button.setEnabled(False)
            if hasattr(self, "style_series_chips"):
                self.style_series_chips.setItems([])
            self._refresh_axis_chips()
            return

        total_series = len(self.current_chart.data_series)
        total_fit = len(self.current_chart.fit_data)
        total_items = total_series + total_fit

        for index, series in enumerate(self.current_chart.data_series):
            if index == self._expanded_series_index:
                card = self._build_expanded_series_card(index, tokens)
            else:
                card = self._build_collapsed_series_row(series, index, tokens)
            self._series_cards_layout.addWidget(card)

        for fit_offset, fit in enumerate(self.current_chart.fit_data):
            index = total_series + fit_offset
            if index == self._expanded_series_index:
                card = self._build_expanded_series_card(index, tokens)
            else:
                card = self._build_collapsed_fit_row(fit, index, tokens)
            self._series_cards_layout.addWidget(card)

        self.remove_series_button.setEnabled(total_items > 0)
        self._refresh_style_chips()
        self._refresh_axis_chips()

    def _refresh_style_chips(self):
        """Sync the Style tab's chip row with the same series+fit list the
        Data tab's cards are built from, keeping the chip row's selection in
        lockstep with `self._expanded_series_index` (the single, panel-wide
        "currently edited entry" state also driven by Data-tab card expand)
        -- unless "Chart" is the currently selected chip, which is its own
        independent target and must survive a series/fit list refresh.

        Chip values are the combined index (int) for series/fit, or the
        "chart" sentinel, so selecting a chip can drive `_expand_series`
        directly without needing to search for the clicked object's index.
        """
        if not hasattr(self, "style_series_chips"):
            # The Data tab (built first) triggers an initial
            # _rebuild_series_cards() call before the Style tab (and its chip
            # row) exists yet. There is no chart loaded yet at that point
            # either, so there is nothing to reflect; the chip row is
            # populated for real the next time a chart is loaded.
            return
        previous_value = self.style_series_chips.currentValue()
        chip_items = [("Chart", "chart")]
        for index, series in enumerate(self.current_chart.data_series):
            label = series.label or f"{series.dataset_id}:{series.y_column}"
            chip_items.append((label, index))
        total_series = len(self.current_chart.data_series)
        for fit_offset, fit in enumerate(self.current_chart.fit_data):
            index = total_series + fit_offset
            chip_items.append((f"\U0001f527 {fit.label}", index))

        # Neither setItems nor setCurrentValue emits currentValueChanged (only
        # a user click on a chip does), so no signal-blocking is needed here
        # to avoid re-entering _expand_series. setItems() already preserves
        # the previous selection if it's still present (true for "chart",
        # always in the list) -- only force it back to the expanded series
        # index when the user wasn't on "Chart".
        self.style_series_chips.setItems(chip_items)
        if previous_value != "chart":
            self.style_series_chips.setCurrentValue(self._expanded_series_index)
        self._update_style_target_cards_visibility()

    def _on_style_chip_selected(self, value):
        """Route a Style-tab chip click: an int (combined series/fit index)
        drives the same expanded-card state the Data tab uses; the "chart"
        sentinel shows chart-level style settings instead, independent of
        which series/fit is expanded on the Data tab."""
        if value == "chart":
            self._update_style_target_cards_visibility()
        else:
            self._expand_series(value)

    def _update_style_target_cards_visibility(self):
        """Show the Chart card XOR the Line/Marker cards, matching whichever
        Style-tab chip is currently selected."""
        is_chart = self.style_series_chips.currentValue() == "chart"
        self.chart_style_card.setVisible(is_chart)
        self.line_card.setVisible(not is_chart)
        self.marker_card.setVisible(not is_chart)

    def _build_collapsed_series_row(self, series, index: int, tokens: dict) -> QWidget:
        """A chip-like collapsed row: color square, name, Y-axis badge, chevron."""
        card = Card()
        card.set_tokens(tokens)
        row = QHBoxLayout(card)

        swatch = QFrame()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(
            f"background-color: {series.color}; "
            f"border: 1px solid {tokens.get('border_control', '#999')}; "
            f"border-radius: {tokens.get('radius_swatch', 4)}px;"
        )
        row.addWidget(swatch)

        name_label = QLabel(series.label or f"{series.dataset_id}:{series.y_column}")
        name_label.setStyleSheet(f"color: {tokens.get('text_primary', '#000')};")
        row.addWidget(name_label, 1)

        row.addWidget(self._build_y_axis_badge(series.y_axis, tokens))

        chevron = QPushButton("▸")  # ▸
        chevron.setFlat(True)
        chevron.setFixedWidth(24)
        chevron.setCursor(Qt.CursorShape.PointingHandCursor)
        chevron.clicked.connect(lambda _checked=False, i=index: self._expand_series(i))
        row.addWidget(chevron)

        return card

    def _build_collapsed_fit_row(self, fit, index: int, tokens: dict) -> QWidget:
        """Collapsed row for a fit-data entry (no Y-axis picker for fits)."""
        card = Card()
        card.set_tokens(tokens)
        row = QHBoxLayout(card)

        swatch = QFrame()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(
            f"background-color: {fit.color}; "
            f"border: 1px solid {tokens.get('border_control', '#999')}; "
            f"border-radius: {tokens.get('radius_swatch', 4)}px;"
        )
        row.addWidget(swatch)

        name_label = QLabel(f"\U0001f527 {fit.label}")  # wrench emoji
        name_label.setStyleSheet(f"color: {tokens.get('text_primary', '#000')};")
        row.addWidget(name_label, 1)

        chevron = QPushButton("▸")
        chevron.setFlat(True)
        chevron.setFixedWidth(24)
        chevron.setCursor(Qt.CursorShape.PointingHandCursor)
        chevron.clicked.connect(lambda _checked=False, i=index: self._expand_series(i))
        row.addWidget(chevron)

        return card

    def _build_y_axis_badge(self, y_axis, tokens: dict) -> QLabel:
        """Small 'Y₁'/'Y₂' badge, accented for the secondary axis."""
        badge = QLabel()
        self._apply_y_axis_badge_style(badge, y_axis, tokens)
        return badge

    def _apply_y_axis_badge_style(self, badge: QLabel, y_axis, tokens: dict):
        """Set a Y-axis badge's text/style in place (shared by initial build
        and live in-place refresh from `_on_series_config_changed`)."""
        is_secondary = y_axis == YAxis.SECONDARY
        badge.setText("Y₂" if is_secondary else "Y₁")
        bg = tokens.get("y2_accent_bg") if is_secondary else tokens.get("surface_inset", "#eee")
        fg = tokens.get("y2_accent") if is_secondary else tokens.get("text_muted", "#666")
        badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            f"border-radius: {tokens.get('radius_chip', 12)}px; "
            "padding: 1px 8px; font-size: 10px; font-weight: 600;"
        )

    def _build_expanded_series_card(self, index: int, tokens: dict) -> QWidget:
        """The expanded card: title + the persistent config form, loaded with
        `index`'s values (a data-series index, or a fit-data index appended
        after all series, matching the combined indexing used throughout
        this panel)."""
        card = Card()
        card.set_tokens(tokens)
        outer = QVBoxLayout(card)

        total_series = len(self.current_chart.data_series)
        is_fit = index >= total_series
        if is_fit:
            fit = self.current_chart.fit_data[index - total_series]
            title_text = f"\U0001f527 {fit.label}"
        else:
            series = self.current_chart.data_series[index]
            title_text = series.label or f"{series.dataset_id}:{series.y_column}"

        header = QHBoxLayout()
        title_label = QLabel(title_text)
        title_label.setStyleSheet(f"font-weight: 600; color: {tokens.get('text_primary', '#000')};")
        header.addWidget(title_label, 1)
        # Keep a reference so _on_series_config_changed can refresh this
        # badge in place on a live Y-axis edit, without a full card rebuild
        # (see that method's docstring for why a rebuild is unsafe there).
        self._expanded_card_y_axis_badge = None
        if not is_fit:
            badge = self._build_y_axis_badge(series.y_axis, tokens)
            self._expanded_card_y_axis_badge = badge
            self._expanded_card_y_axis_badge_tokens = tokens
            header.addWidget(badge)
        chevron = QPushButton("▾")  # ▾, indicates "currently expanded"
        chevron.setFlat(True)
        chevron.setFixedWidth(24)
        chevron.setEnabled(False)
        header.addWidget(chevron)
        outer.addLayout(header)

        outer.addWidget(self._series_form_widget)

        if is_fit:
            self._load_fit_into_controls(fit)
        else:
            self._reset_controls_for_series()
            self._load_series_into_controls(series)

        return card

    def _create_style_tab(self) -> QWidget:
        """Create the style configuration tab.

        There is deliberately no independent series selector here: the chip
        row at the top drives the same `self._expanded_series_index` state
        that the Data tab's expand/collapse cards drive (via `_expand_series`),
        so the two tabs can never disagree about which series/fit is being
        styled. All controls below always reflect whichever entry is
        currently expanded.

        A literal rendered line/marker preview (as sketched in the original
        design brief) is intentionally omitted here: this panel has no chart
        canvas of its own to paint into, and the live chart view already
        re-renders immediately on every change (see `_on_style_changed`), so
        a second, redundant mini-renderer wasn't worth the complexity.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.style_series_chips = ChipRow()
        self.style_series_chips.currentValueChanged.connect(self._on_style_chip_selected)
        layout.addWidget(self.style_series_chips)

        # CHART group: chart-level rendering settings (title/subtitle font
        # size, margin padding, size, dpi) -- shown instead of the Line/
        # Marker cards when the "Chart" chip is selected. Independent of
        # `self._expanded_series_index`: selecting "Chart" never touches
        # which Data-tab series card is expanded.
        self.chart_style_card = Card()
        chart_layout = QGridLayout(self.chart_style_card)
        chart_layout.addWidget(SectionHeader("Chart"), 0, 0, 1, 3)

        chart_layout.addWidget(QLabel("Font size:"), 1, 0)
        chart_layout.addWidget(QLabel("Title"), 1, 1)
        self.title_font_size_spin = QSpinBox()
        self.title_font_size_spin.setRange(8, 32)
        self.title_font_size_spin.setValue(14)
        chart_layout.addWidget(self.title_font_size_spin, 1, 2)

        chart_layout.addWidget(QLabel("Subtitle"), 2, 1)
        self.subtitle_font_size_spin = QSpinBox()
        self.subtitle_font_size_spin.setRange(8, 32)
        self.subtitle_font_size_spin.setValue(12)
        chart_layout.addWidget(self.subtitle_font_size_spin, 2, 2)

        chart_layout.addWidget(QLabel("Padding:"), 3, 0)
        self.chart_padding_spin = QDoubleSpinBox()
        self.chart_padding_spin.setRange(0.0, 10.0)
        self.chart_padding_spin.setSingleStep(0.5)
        self.chart_padding_spin.setValue(2.0)
        chart_layout.addWidget(self.chart_padding_spin, 3, 1, 1, 2)

        chart_layout.addWidget(QLabel("Size:"), 4, 0)
        self.chart_size_combo = QComboBox()
        self.chart_size_combo.addItem("15 × 8 cm", (15.0, 8.0))
        self.chart_size_combo.addItem("20 × 15 cm", (20.0, 15.0))
        self.chart_size_combo.addItem("Custom", "custom")
        self.chart_size_combo.addItem("Use app default", None)
        chart_layout.addWidget(self.chart_size_combo, 4, 1, 1, 2)

        self.custom_size_row = QWidget()
        custom_size_layout = QVBoxLayout(self.custom_size_row)
        custom_size_layout.setContentsMargins(0, 0, 0, 0)
        width_row = QHBoxLayout()
        width_row.addWidget(QLabel("Width"))
        self.chart_width_spin = QDoubleSpinBox()
        self.chart_width_spin.setRange(MIN_CHART_WIDTH_CM, MAX_CHART_WIDTH_CM)
        self.chart_width_spin.setSuffix(" cm")
        width_row.addWidget(self.chart_width_spin)
        width_row.addStretch(1)
        custom_size_layout.addLayout(width_row)
        height_row = QHBoxLayout()
        height_row.addWidget(QLabel("Height"))
        self.chart_height_spin = QDoubleSpinBox()
        self.chart_height_spin.setRange(MIN_CHART_HEIGHT_CM, MAX_CHART_HEIGHT_CM)
        self.chart_height_spin.setSuffix(" cm")
        height_row.addWidget(self.chart_height_spin)
        height_row.addStretch(1)
        custom_size_layout.addLayout(height_row)
        chart_layout.addWidget(self.custom_size_row, 5, 1, 1, 2)
        self.custom_size_row.setVisible(False)

        chart_layout.addWidget(QLabel("DPI:"), 6, 0)
        self.chart_dpi_combo = QComboBox()
        self.chart_dpi_combo.addItem("100 dpi", 100)
        self.chart_dpi_combo.addItem("150 dpi", 150)
        self.chart_dpi_combo.addItem("300 dpi", 300)
        self.chart_dpi_combo.addItem("Custom", "custom")
        self.chart_dpi_combo.addItem("Use app default", None)
        chart_layout.addWidget(self.chart_dpi_combo, 6, 1, 1, 2)

        self.custom_dpi_row = QWidget()
        custom_dpi_layout = QHBoxLayout(self.custom_dpi_row)
        custom_dpi_layout.setContentsMargins(0, 0, 0, 0)
        custom_dpi_layout.addWidget(QLabel("DPI"))
        self.chart_dpi_spin = QSpinBox()
        self.chart_dpi_spin.setRange(50, 600)
        custom_dpi_layout.addWidget(self.chart_dpi_spin)
        custom_dpi_layout.addStretch(1)
        chart_layout.addWidget(self.custom_dpi_row, 7, 1, 1, 2)
        self.custom_dpi_row.setVisible(False)

        hint = QLabel("Size affects export & default fonts")
        hint.setStyleSheet("font-size: 10.5px;")
        chart_layout.addWidget(hint, 8, 0, 1, 3)

        layout.addWidget(self.chart_style_card)

        # LINE group
        self.line_card = Card()
        line_card = self.line_card
        line_layout = QGridLayout(line_card)
        line_layout.addWidget(SectionHeader("Line"), 0, 0, 1, 2)

        line_layout.addWidget(QLabel("Color:"), 1, 0)
        self.line_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        line_layout.addWidget(self.line_color_row, 1, 1)

        line_layout.addWidget(QLabel("Style:"), 2, 0)
        _line_style_items = [
            ("Solid", LineStyleType.SOLID),
            ("Dashed", LineStyleType.DASHED),
            ("Dotted", LineStyleType.DOTTED),
            ("Dash-Dot", LineStyleType.DASHDOT),
            ("None", LineStyleType.NONE),
        ]
        _default_tokens = {"text_primary": "#1C1E26"}
        self.line_style_control = ValueComboBox(
            _line_style_items,
            icons=[build_line_style_icon(style, _default_tokens) for _, style in _line_style_items],
        )
        line_layout.addWidget(self.line_style_control, 2, 1)

        line_layout.addWidget(QLabel("Width:"), 3, 0)
        self.line_width_slider = SliderWithSpinbox(minimum=0.1, maximum=10.0, decimals=1)
        line_layout.addWidget(self.line_width_slider, 3, 1)

        line_layout.addWidget(QLabel("Opacity:"), 4, 0)
        self.line_opacity_slider = SliderWithSpinbox(minimum=0.0, maximum=1.0, decimals=2)
        line_layout.addWidget(self.line_opacity_slider, 4, 1)

        layout.addWidget(line_card)

        # MARKERS group
        self.marker_card = Card()
        marker_card = self.marker_card
        marker_layout = QGridLayout(marker_card)

        marker_header_row = QHBoxLayout()
        marker_header_row.addWidget(SectionHeader("Markers"))
        marker_header_row.addStretch(1)
        self.markers_enabled_toggle = ToggleSwitch()
        marker_header_row.addWidget(self.markers_enabled_toggle)
        marker_layout.addLayout(marker_header_row, 0, 0, 1, 2)

        marker_layout.addWidget(QLabel("Shape:"), 1, 0)
        self.marker_shape_control = ValueComboBox(
            [
                ("● Circle", MarkerType.CIRCLE),
                ("■ Square", MarkerType.SQUARE),
                ("▲ Triangle", MarkerType.TRIANGLE),
                ("◆ Diamond", MarkerType.DIAMOND),
                ("★ Star", MarkerType.STAR),
                ("+ Plus", MarkerType.PLUS),
                ("✕ Cross", MarkerType.CROSS),
            ]
        )
        marker_layout.addWidget(self.marker_shape_control, 1, 1)

        marker_layout.addWidget(QLabel("Size:"), 2, 0)
        self.marker_size_slider = SliderWithSpinbox(minimum=1.0, maximum=20.0, decimals=1)
        marker_layout.addWidget(self.marker_size_slider, 2, 1)

        marker_layout.addWidget(QLabel("Color:"), 3, 0)
        self.marker_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        marker_layout.addWidget(self.marker_color_row, 3, 1)

        marker_layout.addWidget(QLabel("Match line:"), 4, 0)
        self.marker_match_line_toggle = ToggleSwitch(checked=True)
        marker_layout.addWidget(self.marker_match_line_toggle, 4, 1)

        layout.addWidget(marker_card)

        layout.addStretch()
        self.chart_style_card.setVisible(False)
        return widget

    def _create_axes_tab(self) -> QWidget:
        """Create the axes configuration tab: an X/Y1/Y2 chip switcher above
        a single form area that shows only the selected axis's controls.

        Each axis (x, y, y2) gets its own independent set of widgets (built
        by `_build_axis_form_widgets`) rather than one shared form, because
        (unlike the Data/Style tabs' "currently edited series") the three
        axes are genuinely independent, simultaneously-existing config
        state - nothing here is "the currently active axis's data", so
        there's no shared model to reparent a single form around.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.axis_chips = ChipRow()
        self.axis_chips.setItems([("X", "x"), ("Y₁", "y")])
        self.axis_chips.currentValueChanged.connect(self._on_axis_chip_selected)
        layout.addWidget(self.axis_chips)

        self._axis_form_container = QWidget()
        self._axis_form_container_layout = QVBoxLayout(self._axis_form_container)
        self._axis_form_container_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._axis_form_container)
        layout.addStretch()

        self.axes_forms = {}
        for prefix in ("x", "y", "y2"):
            self._build_axis_form_widgets(prefix)
        self._show_axis_form("x")
        return widget

    def _build_axis_form_widgets(self, prefix: str):
        """Build one axis's full control set and register it in `self.axes_forms[prefix]`."""
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("Label:"))
        label_edit = QLineEdit()
        label_row.addWidget(label_edit)
        label_row.addWidget(QLabel("Font size:"))
        font_spin = QSpinBox()
        font_spin.setRange(6, 32)
        font_spin.setValue(12)
        label_row.addWidget(font_spin)
        form_layout.addLayout(label_row)

        scale_control = SegmentedControl([("Linear", ScaleType.LINEAR), ("Log", ScaleType.LOG)])
        form_layout.addWidget(scale_control)

        side_control = None
        if prefix in ("y", "y2"):
            side_control = SegmentedControl([("Left", "left"), ("Right", "right")])
            form_layout.addWidget(side_control)

        range_card = Card()
        range_layout = QGridLayout(range_card)
        range_layout.addWidget(SectionHeader("Range"), 0, 0)
        range_layout.addWidget(QLabel("Auto"), 0, 1)
        auto_toggle = ToggleSwitch(checked=True)
        range_layout.addWidget(auto_toggle, 0, 2)
        min_spin = QDoubleSpinBox()
        min_spin.setRange(-1e9, 1e9)
        min_spin.setEnabled(False)
        max_spin = QDoubleSpinBox()
        max_spin.setRange(-1e9, 1e9)
        max_spin.setValue(1.0)
        max_spin.setEnabled(False)
        range_layout.addWidget(QLabel("Min:"), 1, 0)
        range_layout.addWidget(min_spin, 1, 1, 1, 2)
        range_layout.addWidget(QLabel("Max:"), 2, 0)
        range_layout.addWidget(max_spin, 2, 1, 1, 2)
        form_layout.addWidget(range_card)

        ticks_card = Card()
        ticks_layout = QGridLayout(ticks_card)
        ticks_layout.addWidget(SectionHeader("Ticks"), 0, 0, 1, 2)
        mode_control = SegmentedControl([("Auto", "auto"), ("Count", "count"), ("Step", "step")])
        ticks_layout.addWidget(mode_control, 1, 0, 1, 2)
        count_spin = QSpinBox()
        count_spin.setRange(2, 50)
        count_spin.setValue(5)
        count_spin.setEnabled(False)
        step_spin = QDoubleSpinBox()
        step_spin.setRange(0.001, 1e9)
        step_spin.setValue(1.0)
        step_spin.setEnabled(False)
        ticks_layout.addWidget(QLabel("Count:"), 2, 0)
        ticks_layout.addWidget(count_spin, 2, 1)
        ticks_layout.addWidget(QLabel("Step:"), 3, 0)
        ticks_layout.addWidget(step_spin, 3, 1)
        format_combo = QComboBox()
        for text, value in [("Auto", "auto"), ("Integer", "integer"), ("1 Decimal", "1decimal"),
                            ("2 Decimals", "2decimal"), ("Scientific", "scientific"), ("Custom...", "custom")]:
            format_combo.addItem(text, value)
        ticks_layout.addWidget(QLabel("Format:"), 4, 0)
        ticks_layout.addWidget(format_combo, 4, 1)
        format_custom_edit = QLineEdit()
        format_custom_edit.setPlaceholderText("e.g. {:.2f} units")
        format_custom_edit.setEnabled(False)
        ticks_layout.addWidget(format_custom_edit, 5, 0, 1, 2)
        grid_toggle = ToggleSwitch(checked=True)
        ticks_layout.addWidget(QLabel("Show grid"), 6, 0)
        ticks_layout.addWidget(grid_toggle, 6, 1)
        form_layout.addWidget(ticks_card)

        copy_button = None
        if prefix in ("y", "y2"):
            copy_button = QPushButton("Copy settings to Y axis")
            copy_button.setFlat(True)
            copy_button.clicked.connect(lambda _checked=False, p=prefix: self._on_copy_axis_settings(p))
            form_layout.addWidget(copy_button)

        self.axes_forms[prefix] = {
            "widget": form_widget, "label_edit": label_edit, "font_spin": font_spin,
            "scale_control": scale_control, "side_control": side_control,
            "range_card": range_card, "ticks_card": ticks_card,
            "auto_toggle": auto_toggle, "min_spin": min_spin, "max_spin": max_spin,
            "mode_control": mode_control, "count_spin": count_spin, "step_spin": step_spin,
            "format_combo": format_combo, "format_custom_edit": format_custom_edit,
            "grid_toggle": grid_toggle, "copy_button": copy_button,
        }

        # Wire this form's widgets directly to shared handlers - the forms
        # are built dynamically (there are no static self.x_*/self.y_*
        # attributes to hook up in _connect_signals), so wiring happens here.
        label_edit.textChanged.connect(self._on_chart_config_changed)
        font_spin.valueChanged.connect(self._on_chart_config_changed)
        scale_control.currentValueChanged.connect(self._on_chart_config_changed)
        if side_control is not None:
            side_control.currentValueChanged.connect(self._on_chart_config_changed)
        auto_toggle.toggled.connect(lambda checked, p=prefix: self._on_axis_auto_limits_toggled(p, checked))
        min_spin.valueChanged.connect(self._on_chart_config_changed)
        max_spin.valueChanged.connect(self._on_chart_config_changed)
        mode_control.currentValueChanged.connect(lambda _v, p=prefix: self._on_axis_tick_mode_changed(p))
        count_spin.valueChanged.connect(self._on_chart_config_changed)
        step_spin.valueChanged.connect(self._on_chart_config_changed)
        format_combo.currentIndexChanged.connect(lambda _i, p=prefix: self._on_axis_tick_format_changed(p))
        format_custom_edit.textChanged.connect(self._on_chart_config_changed)
        grid_toggle.toggled.connect(self._on_chart_config_changed)

        form_widget.setVisible(False)
        self._axis_form_container_layout.addWidget(form_widget)

    def _show_axis_form(self, prefix: str):
        """Show only the selected axis's form, hiding the other two."""
        for key, form in self.axes_forms.items():
            form["widget"].setVisible(key == prefix)

    def _on_axis_chip_selected(self, prefix: str):
        self._show_axis_form(prefix)

    def _on_axis_auto_limits_toggled(self, prefix: str, checked: bool):
        form = self.axes_forms[prefix]
        form["min_spin"].setEnabled(not checked)
        form["max_spin"].setEnabled(not checked)
        self._on_chart_config_changed()

    def _on_axis_tick_mode_changed(self, prefix: str):
        form = self.axes_forms[prefix]
        mode = form["mode_control"].currentValue()
        form["count_spin"].setEnabled(mode == "count")
        form["step_spin"].setEnabled(mode == "step")
        self._on_chart_config_changed()

    def _on_axis_tick_format_changed(self, prefix: str):
        form = self.axes_forms[prefix]
        form["format_custom_edit"].setEnabled(form["format_combo"].currentData() == "custom")
        self._on_chart_config_changed()

    def _on_copy_axis_settings(self, prefix: str):
        """Copy the shown Y axis's non-label settings to the other Y axis."""
        other = "y2" if prefix == "y" else "y"
        source = self.axes_forms[prefix]
        target = self.axes_forms[other]

        target["font_spin"].setValue(source["font_spin"].value())
        target["scale_control"].setCurrentValue(source["scale_control"].currentValue())
        if source["side_control"] is not None and target["side_control"] is not None:
            target["side_control"].setCurrentValue(source["side_control"].currentValue())
        target["auto_toggle"].setChecked(source["auto_toggle"].isChecked())
        target["min_spin"].setValue(source["min_spin"].value())
        target["max_spin"].setValue(source["max_spin"].value())
        target["min_spin"].setEnabled(not target["auto_toggle"].isChecked())
        target["max_spin"].setEnabled(not target["auto_toggle"].isChecked())
        target["mode_control"].setCurrentValue(source["mode_control"].currentValue())
        target["count_spin"].setValue(source["count_spin"].value())
        target["step_spin"].setValue(source["step_spin"].value())
        target["count_spin"].setEnabled(target["mode_control"].currentValue() == "count")
        target["step_spin"].setEnabled(target["mode_control"].currentValue() == "step")
        format_index = target["format_combo"].findData(source["format_combo"].currentData())
        if format_index >= 0:
            target["format_combo"].setCurrentIndex(format_index)
        target["format_custom_edit"].setText(source["format_custom_edit"].text())
        target["format_custom_edit"].setEnabled(target["format_combo"].currentData() == "custom")
        target["grid_toggle"].setChecked(source["grid_toggle"].isChecked())

        self._on_chart_config_changed()

    def _refresh_axis_chips(self):
        """Sync the Axes tab's chip row with whether any series currently
        uses the secondary Y axis, adding/removing the Y2 chip accordingly.
        Safe to call whenever the chart or its series may have changed
        (chart load, series rebuild) - mirrors `_refresh_style_chips`.
        """
        if not hasattr(self, "axis_chips"):
            return
        has_secondary = bool(self.current_chart) and any(
            series.y_axis == YAxis.SECONDARY for series in self.current_chart.data_series
        )
        items = [("X", "x"), ("Y₁", "y")]
        if has_secondary:
            items.append(("Y₂", "y2"))
        self.axis_chips.setItems(items)

    def _write_axis_config(self, prefix: str, config: dict):
        """Write one axis form's widget values into `config` (the mutable chart.config dict)."""
        form = self.axes_forms[prefix]
        config[f"{prefix}_label"] = form["label_edit"].text()
        config[f"{prefix}_font_size"] = form["font_spin"].value()
        if form["scale_control"].currentValue():
            config[f"{prefix}_scale"] = form["scale_control"].currentValue().value
        if form["side_control"] is not None:
            config[f"{prefix}_side"] = form["side_control"].currentValue()
        config[f"{prefix}_auto_limits"] = form["auto_toggle"].isChecked()
        config[f"{prefix}_min"] = form["min_spin"].value()
        config[f"{prefix}_max"] = form["max_spin"].value()
        config[f"{prefix}_tick_mode"] = form["mode_control"].currentValue()
        config[f"{prefix}_tick_count"] = form["count_spin"].value()
        config[f"{prefix}_tick_step"] = form["step_spin"].value()
        config[f"{prefix}_tick_format"] = form["format_combo"].currentData()
        config[f"{prefix}_tick_format_custom"] = form["format_custom_edit"].text()
        config[f"show_grid_{prefix}"] = form["grid_toggle"].isChecked()

    def _read_axis_config(self, prefix: str, config: dict):
        """Populate one axis form's widgets from `config`. Assumes the caller
        already has `self._updating_controls` set so change signals don't
        write half-loaded values back out."""
        form = self.axes_forms[prefix]
        form["label_edit"].setText(config.get(f"{prefix}_label", ""))
        form["font_spin"].setValue(config.get(f"{prefix}_font_size", 12))

        scale_value = config.get(f"{prefix}_scale", "linear")
        try:
            form["scale_control"].setCurrentValue(ScaleType(scale_value))
        except ValueError:
            form["scale_control"].setCurrentValue(ScaleType.LINEAR)

        if form["side_control"] is not None:
            default_side = "left" if prefix == "y" else "right"
            form["side_control"].setCurrentValue(config.get(f"{prefix}_side", default_side))

        auto_limits = config.get(f"{prefix}_auto_limits", True)
        form["auto_toggle"].setChecked(auto_limits)
        form["min_spin"].setValue(config.get(f"{prefix}_min", 0.0))
        form["max_spin"].setValue(config.get(f"{prefix}_max", 1.0))
        form["min_spin"].setEnabled(not auto_limits)
        form["max_spin"].setEnabled(not auto_limits)

        tick_mode = config.get(f"{prefix}_tick_mode", "auto")
        form["mode_control"].setCurrentValue(tick_mode)
        form["count_spin"].setValue(config.get(f"{prefix}_tick_count", 5))
        form["step_spin"].setValue(config.get(f"{prefix}_tick_step", 1.0))
        form["count_spin"].setEnabled(tick_mode == "count")
        form["step_spin"].setEnabled(tick_mode == "step")

        tick_format = config.get(f"{prefix}_tick_format", "auto")
        format_index = form["format_combo"].findData(tick_format)
        form["format_combo"].setCurrentIndex(format_index if format_index >= 0 else 0)
        form["format_custom_edit"].setText(config.get(f"{prefix}_tick_format_custom", ""))
        form["format_custom_edit"].setEnabled(tick_format == "custom")

        form["grid_toggle"].setChecked(config.get(f"show_grid_{prefix}", True))


    def _create_legend_tab(self) -> QWidget:
        """Create the legend configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        show_row = QHBoxLayout()
        show_row.addWidget(QLabel("Show legend"))
        self.show_legend_toggle = ToggleSwitch(checked=True)
        show_row.addWidget(self.show_legend_toggle)
        show_row.addStretch(1)
        layout.addLayout(show_row)

        legend_group = QGroupBox("Legend")
        legend_layout = QGridLayout(legend_group)

        legend_layout.addWidget(QLabel("Position:"), 0, 0)
        self.legend_position_combo = QComboBox()
        for position in LegendPosition:
            self.legend_position_combo.addItem(position.value.title(), position)
        legend_layout.addWidget(self.legend_position_combo, 0, 1)

        legend_layout.addWidget(QLabel("Font Size:"), 1, 0)
        self.legend_font_size_spin = QSpinBox()
        self.legend_font_size_spin.setRange(6, 18)
        self.legend_font_size_spin.setValue(10)
        legend_layout.addWidget(self.legend_font_size_spin, 1, 1)

        legend_layout.addWidget(QLabel("Columns:"), 2, 0)
        self.legend_columns_control = SegmentedControl([("1", 1), ("2", 2), ("3", 3)])
        legend_layout.addWidget(self.legend_columns_control, 2, 1)

        layout.addWidget(legend_group)

        frame_card = Card()
        frame_layout = QGridLayout(frame_card)
        frame_layout.addWidget(SectionHeader("Frame"), 0, 0)
        self.legend_show_frame_toggle = ToggleSwitch(checked=True)
        frame_layout.addWidget(self.legend_show_frame_toggle, 0, 1)
        frame_layout.addWidget(QLabel("Background:"), 1, 0)
        self.legend_bg_color_row = ColorSwatchRow(["#FFFFFF", "#F4F5F8", "#1C1E26"])
        frame_layout.addWidget(self.legend_bg_color_row, 1, 1)
        frame_layout.addWidget(QLabel("Opacity:"), 2, 0)
        self.legend_bg_opacity_slider = SliderWithSpinbox(minimum=0.0, maximum=1.0, decimals=2)
        frame_layout.addWidget(self.legend_bg_opacity_slider, 2, 1)
        layout.addWidget(frame_card)

        layout.addStretch()
        return widget

    def _on_show_legend_toggled(self, checked: bool):
        """Handle the Legend tab's master Show-legend toggle."""
        self._update_legend_controls_enabled()
        self._on_chart_config_changed()

    def _update_legend_controls_enabled(self):
        """Enable/disable every other Legend-tab widget based on the master toggle."""
        show_legend = self.show_legend_toggle.isChecked()
        for control in (
            self.legend_position_combo,
            self.legend_font_size_spin,
            self.legend_columns_control,
            self.legend_show_frame_toggle,
            self.legend_bg_color_row,
            self.legend_bg_opacity_slider,
        ):
            control.setEnabled(show_legend)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_changed)

        # Connect chart-level configuration changes
        self.chart_type_control.currentValueChanged.connect(self._on_chart_type_index_changed)
        self.hist_bins_spin.valueChanged.connect(self._on_chart_config_changed)
        self.title_edit.textChanged.connect(self._on_chart_config_changed)
        self.title_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.subtitle_edit.textChanged.connect(self._on_chart_config_changed)
        self.subtitle_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.chart_padding_spin.valueChanged.connect(self._on_chart_config_changed)
        self.chart_size_combo.currentIndexChanged.connect(self._on_chart_size_combo_changed)
        self.chart_dpi_combo.currentIndexChanged.connect(self._on_chart_dpi_combo_changed)
        self.chart_width_spin.valueChanged.connect(self._on_chart_config_changed)
        self.chart_height_spin.valueChanged.connect(self._on_chart_config_changed)
        self.chart_dpi_spin.valueChanged.connect(self._on_chart_config_changed)
        # Axes tab: each axis form's widgets are wired directly to shared
        # handlers in _build_axis_form_widgets, not here (the forms are
        # built dynamically per-prefix, so there are no static
        # self.x_*/self.y_*/self.y2_* attributes to hook up in one place).
        self.show_legend_toggle.toggled.connect(self._on_show_legend_toggled)
        self.legend_position_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.legend_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.legend_columns_control.currentValueChanged.connect(self._on_chart_config_changed)
        self.legend_show_frame_toggle.toggled.connect(self._on_chart_config_changed)
        self.legend_bg_color_row.colorChanged.connect(self._on_chart_config_changed)
        self.legend_bg_opacity_slider.valueChanged.connect(self._on_chart_config_changed)
        
        # Connect series configuration change signals
        self.x_column_combo.currentTextChanged.connect(self._on_series_config_changed)
        self.y_column_combo.currentTextChanged.connect(self._on_series_config_changed)
        self.series_y_axis_control.currentValueChanged.connect(self._on_series_config_changed)
        # Defer label persistence to editingFinished to avoid disruptive refresh while typing
        self.series_label_edit.textChanged.connect(self._on_label_typing)
        self.series_label_edit.editingFinished.connect(self._on_label_committed)
        
        # Connect style change signals (Style tab; chip row selection is
        # wired directly to _expand_series in _create_style_tab, not here)
        self.line_color_row.colorChanged.connect(self._on_style_changed)
        self.line_style_control.currentValueChanged.connect(self._on_style_changed)
        self.line_width_slider.valueChanged.connect(self._on_style_changed)
        self.line_opacity_slider.valueChanged.connect(self._on_style_changed)

        self.markers_enabled_toggle.toggled.connect(self._on_markers_enabled_toggled)
        self.marker_shape_control.currentValueChanged.connect(self._on_style_changed)
        self.marker_size_slider.valueChanged.connect(self._on_style_changed)
        self.marker_color_row.colorChanged.connect(self._on_style_changed)
        self.marker_match_line_toggle.toggled.connect(self._on_marker_match_line_toggled)
    
    def setup_event_subscriptions(self):
        """Set up event subscriptions for tab changes."""
        self.subscribe_to_event(UIEvents.TAB_CHANGED, self._on_tab_changed)
        self.subscribe_to_event(ChartEvents.CHART_UPDATED, self._on_chart_updated)
        # Ensure datasets populate after a project is loaded from file. AppState emits
        # 'project_loaded' (underscore) and 'first_project_loaded'. Also subscribe to the
        # canonical constant for forward compatibility.
        self.subscribe_to_event(ProjectEvents.PROJECT_LOADED, self._on_project_loaded)  # may not fire yet
        self.subscribe_to_event("project_loaded", self._on_project_loaded)
        self.subscribe_to_event("first_project_loaded", self._on_project_loaded)

    def _ensure_datasets_loaded(self):
        """Populate datasets if empty (idempotent)."""
        if not self.datasets and self.app_context.app_state.current_project:
            self.set_project(self.app_context.app_state.current_project)

    def _on_project_loaded(self, event_data):
        """Handle project loaded to refresh dataset list and any active chart context."""
        project = event_data.get("project") or self.app_context.app_state.current_project
        if project:
            self.set_project(project)
            # If a chart tab already active, re-load to bind series list correctly
            if self.current_chart:
                self.load_chart_object(self.current_chart)
    
    def _on_tab_changed(self, event_data):
        """Handle tab change events to update context."""
        current_tab_type = event_data.get("tab_type")
        chart_id = event_data.get("chart_id")
        
        # Check if current tab is a chart tab
        if current_tab_type == "chart" and chart_id:
            # Get the chart from the project using chart_id
            project = self.app_context.app_state.current_project
            self.set_project(project)
            if project is not None:
                chart = project.find_item(chart_id)
                if chart:
                    # Load the chart into the properties panel
                    self.load_chart_object(chart)
                    self.logger.info("Chart properties panel context set to chart %s", chart.name)
                else:
                    self.logger.warning("Chart properties panel: chart id %s not found in project", chart_id)
            else:
                self.logger.warning("Chart properties panel: no current project available while switching tab")
        else:
            # Clear chart properties panel context when no relevant tab is active
            self.load_chart_object(None)
            self.logger.debug("Chart properties panel context cleared")
    
    def _on_chart_updated(self, event_data):
        """Handle chart updated events to refresh the panel."""
        chart_id = event_data.get("chart_id")
        if not self.current_chart or chart_id != self.current_chart.id:
            return

        if "chart" in event_data:
            # Command-originated update (Apply execute/undo/redo, add/remove
            # series, fit added): the model changed outside this panel's live
            # edits, so re-sync all controls and re-capture the Cancel/Apply
            # baseline to match the new command boundary.
            # TODO: this branch always fires first (add/remove series and
            # fit-added events include both "chart" and "update_type"), so it
            # resets the expanded card back to index 0 via load_chart_object,
            # making the update_type branch below unreachable. Consider
            # preserving the selected row here too.
            self.load_chart_object(self.current_chart)
            self.logger.debug("Chart properties panel reloaded for command-originated update")
            return

        update_type = event_data.get("update_type", "")
        if update_type in ["fit_added", "series_added", "series_removed"]:
            self._rebuild_series_cards()
            self.logger.debug("Chart properties panel refreshed for update: %s", update_type)
    
    def _add_series(self):
        """Add a new data series."""
        if not self.current_chart:
            return

        # Create a new series with default values
        dataset_id = self.dataset_combo.currentData() if self.dataset_combo.count() > 0 else ""
        dataset_name = self.dataset_combo.currentText() if self.dataset_combo.count() > 0 else ""
        x_column = self.x_column_combo.currentText() if self.x_column_combo.count() > 0 else ""
        y_column = self.y_column_combo.currentText() if self.y_column_combo.count() > 0 else ""

        if dataset_id and x_column and y_column:
            command = AddSeriesCommand(
                self.app_context,
                chart_id=self.current_chart.id,
                dataset_id=dataset_id,
                x_column=x_column,
                y_column=y_column,
                label=f"{dataset_name}:{y_column}",
                color=self._get_next_series_color(),
            )
            self.command_executor.execute_command(command)

            # Select and expand the newly added series
            self._expanded_series_index = len(self.current_chart.data_series) - 1
            self._rebuild_series_cards()

    def _remove_series(self):
        """Remove the selected data series or fit data."""
        if not self.current_chart:
            return

        total_series = len(self.current_chart.data_series)
        total_items = total_series + len(self.current_chart.fit_data)

        current_row = self._expanded_series_index
        if current_row < 0 or current_row >= total_items:
            return

        if current_row < total_series:
            command = RemoveSeriesCommand(
                self.app_context,
                chart_id=self.current_chart.id,
                series_index=current_row,
            )
        else:
            command = RemoveFitDataCommand(
                self.app_context,
                chart_id=self.current_chart.id,
                fit_index=current_row - total_series,
            )
        self.command_executor.execute_command(command)

        # Expand the previous item (or stay at 0 if nothing's left) and rebuild.
        remaining_items = len(self.current_chart.data_series) + len(self.current_chart.fit_data)
        self._expanded_series_index = min(current_row, max(remaining_items - 1, 0))
        self._rebuild_series_cards()

    def _on_series_config_changed(self):
        """Handle dataset / column configuration changes for the selected series.

        Label changes are intentionally deferred to editingFinished handled by
        _on_label_committed to avoid disruptive list refresh while typing.
        """
        if self._updating_controls or not self.current_chart:
            return

        current_row = self._expanded_series_index
        if current_row < 0:
            return

        total_series = len(self.current_chart.data_series)
        if current_row < total_series:
            # Update data series (guard for safety)
            if current_row >= len(self.current_chart.data_series):
                return
            series = self.current_chart.data_series[current_row]
            if self.dataset_combo.currentData():
                series.dataset_id = self.dataset_combo.currentData()
            series.x_column = self.x_column_combo.currentText()
            series.y_column = self.y_column_combo.currentText()
            series.y_axis = self.series_y_axis_control.currentValue()

            # Refresh the Axes-tab Y2 chip immediately so switching a series
            # to the secondary axis is reflected without waiting for Apply
            # or a full chart reload. This only touches the axis_chips
            # SegmentedControl (not the Data-tab card list), so it's safe to
            # call from here.
            self._refresh_axis_chips()

            # Update the expanded card's own Y1/Y2 badge in place too.
            # Deliberately NOT calling `_rebuild_series_cards()` from this
            # handler: that tears down and rebuilds the Data-tab card list,
            # including detaching/reattaching `_series_form_widget` (which
            # hosts the very control that triggered this handler) - the same
            # reentrancy hazard already fixed once for live-edit handlers
            # touching the reparented series form widget. Updating the
            # existing badge label in place avoids that entirely.
            if getattr(self, "_expanded_card_y_axis_badge", None) is not None:
                self._apply_y_axis_badge_style(
                    self._expanded_card_y_axis_badge,
                    series.y_axis,
                    getattr(self, "_expanded_card_y_axis_badge_tokens", {}),
                )
        else:
            # Fit data: columns/dataset not editable, ignore
            return

        self._has_unsaved_changes = True
        self._update_status_indicator()

    def _on_markers_enabled_toggled(self, _checked: bool):
        """Handle the Markers section's on/off toggle."""
        self._update_marker_controls_enabled()
        self._on_style_changed()

    def _on_marker_match_line_toggled(self, _checked: bool):
        """Handle the 'Match line' toggle for marker color."""
        self._update_marker_controls_enabled()
        self._on_style_changed()

    def _update_marker_controls_enabled(self):
        """Enable/disable marker sub-controls based on the enable and
        match-line toggles (pure UI convenience; see _on_style_changed for
        how this maps onto the persisted `marker_style`/`marker_color`)."""
        markers_enabled = self.markers_enabled_toggle.isChecked()
        self.marker_shape_control.setEnabled(markers_enabled)
        self.marker_size_slider.setEnabled(markers_enabled)
        self.marker_match_line_toggle.setEnabled(markers_enabled)
        self.marker_color_row.setEnabled(
            markers_enabled and not self.marker_match_line_toggle.isChecked()
        )

    def _on_style_changed(self):
        """Handle style changes."""
        if self._updating_controls or not self.current_chart:
            return

        current_row = self._expanded_series_index
        if current_row < 0:
            return

        total_series = len(self.current_chart.data_series)

        if current_row < total_series:
            # Updating a data series
            if current_row >= len(self.current_chart.data_series):
                return
            series = self.current_chart.data_series[current_row]

            series.color = self.line_color_row.currentColor()
            series.line_style = self.line_style_control.currentValue().value
            series.line_width = self.line_width_slider.value()
            series.alpha = self.line_opacity_slider.value()

            # "Markers enabled" isn't a separate persisted flag: it maps onto
            # the existing MarkerType.NONE member (matching how the old combo
            # already let a user pick "None" as a marker type). "Match line"
            # reuses the existing marker_color == "" convention (already used
            # by _load_series_into_controls before this task).
            if self.markers_enabled_toggle.isChecked():
                series.marker_style = self.marker_shape_control.currentValue().value
                series.marker_size = self.marker_size_slider.value()
                series.marker_color = (
                    "" if self.marker_match_line_toggle.isChecked()
                    else self.marker_color_row.currentColor()
                )
            else:
                series.marker_style = MarkerType.NONE.value

        else:
            # Updating fit data
            fit_index = current_row - total_series
            if fit_index >= len(self.current_chart.fit_data):
                return

            fit = self.current_chart.fit_data[fit_index]
            fit.color = self.line_color_row.currentColor()
            fit.line_style = self.line_style_control.currentValue().value
            fit.line_width = self.line_width_slider.value()
            # Note: fit data doesn't use marker_size or marker colors

        # Emit update event so any open chart tab refreshes immediately
        if self.current_chart:
            self._has_unsaved_changes = True
            self._update_status_indicator()
            self.publish_event(ChartEvents.CHART_UPDATED, {
                "chart_id": self.current_chart.id,
                "update_type": "series_updated"
            })

    def _on_chart_type_index_changed(self):
        """Handle chart type combo changes, tracking explicit user intent.

        Distinguishes a user picking a chart type from the combo being set
        programmatically while loading a chart (see _loaded_chart_type_supported).
        """
        if not self._updating_controls:
            self._chart_type_touched_by_user = True
        self._update_hist_bins_visibility()
        self._on_chart_config_changed()

    def _update_hist_bins_visibility(self):
        """Show the Histogram Bins control only when the chart type is Histogram."""
        is_histogram = self.chart_type_control.currentValue() == ChartType.HISTOGRAM
        self.hist_bins_label.setVisible(is_histogram)
        self.hist_bins_spin.setVisible(is_histogram)

    def _app_chart_display_defaults(self):
        """Read the app-wide default chart width/height/dpi from Settings."""
        cfg_manager = self.app_context.get_manager(ConfigManager)
        display_cfg = getattr(getattr(cfg_manager, "config", None), "chart_display", None)
        default_width = getattr(display_cfg, "default_width_cm", 20.0) if display_cfg else 20.0
        default_height = getattr(display_cfg, "default_height_cm", 15.0) if display_cfg else 15.0
        default_dpi = getattr(display_cfg, "dpi", 100) if display_cfg else 100
        return default_width, default_height, default_dpi

    def _effective_chart_size_dpi(self):
        """Resolve the chart's current effective (width_cm, height_cm, dpi),
        preferring the chart's own saved values and falling back to the
        app-wide Settings defaults. Used to pre-fill the Custom fields the
        first time the user selects Custom for Size or DPI."""
        default_width, default_height, default_dpi = self._app_chart_display_defaults()
        if not self.current_chart:
            return default_width, default_height, default_dpi
        # Deferred import: chart_editor.py pulls in matplotlib, which must
        # stay lazy at app startup (see tests/test_startup_imports.py).
        from pandaplot.gui.components.tabs.chart.chart_editor import resolve_chart_size

        return resolve_chart_size(
            self.current_chart.config.get("width_cm"),
            self.current_chart.config.get("height_cm"),
            self.current_chart.config.get("dpi"),
            default_width, default_height, default_dpi,
        )

    def _size_from_controls(self):
        """Resolve (width_cm, height_cm) from chart_size_combo, reading the
        dedicated Custom spin boxes when that sentinel is selected."""
        data = self.chart_size_combo.currentData()
        if data == "custom":
            return self.chart_width_spin.value(), self.chart_height_spin.value()
        if data is None:
            return None, None
        return data

    def _dpi_from_controls(self):
        """Resolve dpi from chart_dpi_combo, reading the dedicated Custom
        spin box when that sentinel is selected."""
        data = self.chart_dpi_combo.currentData()
        if data == "custom":
            return self.chart_dpi_spin.value()
        return data

    def _on_chart_size_combo_changed(self):
        """Show/hide the Custom width/height row and pre-fill it the first
        time the user manually selects Custom for this loaded chart."""
        is_custom = self.chart_size_combo.currentData() == "custom"
        self.custom_size_row.setVisible(is_custom)
        if is_custom and not self._updating_controls and not self._custom_size_prefilled:
            width, height, _ = self._effective_chart_size_dpi()
            self.chart_width_spin.setValue(width)
            self.chart_height_spin.setValue(height)
            self._custom_size_prefilled = True
        self._on_chart_config_changed()

    def _on_chart_dpi_combo_changed(self):
        """Show/hide the Custom DPI row and pre-fill it the first time the
        user manually selects Custom for this loaded chart."""
        is_custom = self.chart_dpi_combo.currentData() == "custom"
        self.custom_dpi_row.setVisible(is_custom)
        if is_custom and not self._updating_controls and not self._custom_dpi_prefilled:
            _, _, dpi = self._effective_chart_size_dpi()
            self.chart_dpi_spin.setValue(dpi)
            self._custom_dpi_prefilled = True
        self._on_chart_config_changed()

    def _on_chart_config_changed(self):
        """Handle chart-level configuration changes."""
        if not self.current_chart or self._updating_controls:
            return
        
        # Update chart configuration from UI controls
        if hasattr(self, "title_edit"):
            self.current_chart.name = self.title_edit.text()

        config = self.current_chart.config
        if hasattr(self, "title_edit"):
            config["title"] = self.title_edit.text()
        if hasattr(self, "title_font_size_spin"):
            config["title_font_size"] = self.title_font_size_spin.value()
        if hasattr(self, "subtitle_edit"):
            config["subtitle"] = self.subtitle_edit.text()
        if hasattr(self, "subtitle_font_size_spin"):
            config["subtitle_font_size"] = self.subtitle_font_size_spin.value()
        if hasattr(self, "chart_padding_spin"):
            config["chart_padding"] = self.chart_padding_spin.value()
        if hasattr(self, "chart_size_combo"):
            config["width_cm"], config["height_cm"] = self._size_from_controls()
        if hasattr(self, "chart_dpi_combo"):
            config["dpi"] = self._dpi_from_controls()
        if hasattr(self, "axes_forms"):
            for prefix in ("x", "y", "y2"):
                self._write_axis_config(prefix, config)
        if hasattr(self, "show_legend_toggle"):
            config["show_legend"] = self.show_legend_toggle.isChecked()
        if hasattr(self, "legend_position_combo") and self.legend_position_combo.currentData():
            config["legend_position"] = self.legend_position_combo.currentData().value
        if hasattr(self, "legend_font_size_spin"):
            config["legend_font_size"] = self.legend_font_size_spin.value()
        if hasattr(self, "legend_columns_control"):
            config["legend_columns"] = self.legend_columns_control.currentValue()
        if hasattr(self, "legend_show_frame_toggle"):
            config["legend_show_frame"] = self.legend_show_frame_toggle.isChecked()
        if hasattr(self, "legend_bg_color_row"):
            config["legend_bg_color"] = self.legend_bg_color_row.currentColor()
        if hasattr(self, "legend_bg_opacity_slider"):
            config["legend_bg_alpha"] = self.legend_bg_opacity_slider.value()
        if hasattr(self, "hist_bins_spin"):
            config["hist_bins"] = self.hist_bins_spin.value()
        if hasattr(self, "chart_type_control") and self.chart_type_control.currentValue():
            chart_type_map = {
                ChartType.LINE: "line",
                ChartType.SCATTER: "scatter",
                ChartType.BAR: "bar",
                ChartType.HISTOGRAM: "hist",
            }
            chart_type = self.chart_type_control.currentValue()
            if chart_type in chart_type_map and (
                self._loaded_chart_type_supported or self._chart_type_touched_by_user
            ):
                self.current_chart.chart_type = chart_type_map[chart_type]
        
        # Emit update event so any open chart tab refreshes immediately
        if self.current_chart:
            self._has_unsaved_changes = True
            self._update_status_indicator()
            self.publish_event(ChartEvents.CHART_UPDATED, {
                "chart_id": self.current_chart.id,
                "update_type": "config_updated"
            })

    def _update_status_indicator(self):
        """Update the footer to reflect unsaved changes."""
        self.footer.setModified(
            self._has_unsaved_changes,
            change_count=1 if self._has_unsaved_changes else 0,
        )

    def _load_series_into_controls(self, series):
        """Load a data series into the configuration controls."""
        # Enable all controls for series editing
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self._reset_controls_for_series()

            # Set dataset
            for i in range(self.dataset_combo.count()):
                if self.dataset_combo.itemData(i) == series.dataset_id:
                    self.dataset_combo.setCurrentIndex(i)
                    break

            # Repopulate column combos from the (possibly changed) dataset before
            # selecting the series' columns, so stale entries from a previous
            # dataset/column state (e.g. after undo/redo of a column rename)
            # don't linger.
            self._populate_column_combos(series.dataset_id)

            # Set columns
            x_index = self.x_column_combo.findText(series.x_column)
            if x_index >= 0:
                self.x_column_combo.setCurrentIndex(x_index)

            y_index = self.y_column_combo.findText(series.y_column)
            if y_index >= 0:
                self.y_column_combo.setCurrentIndex(y_index)

            # Set Y axis (primary/secondary). SegmentedControl.setCurrentValue
            # doesn't emit currentValueChanged, so no signal-blocking needed.
            self.series_y_axis_control.setCurrentValue(series.y_axis)

            # Set label (block signals while populating)
            self.series_label_edit.blockSignals(True)
            self.series_label_edit.setText(series.label)
            self.series_label_edit.blockSignals(False)
            self._pending_label = series.label

            # Update style controls to reflect this series
            self.line_color_row.setCurrentColor(series.color)
            self.line_width_slider.setValue(series.line_width)
            self.line_opacity_slider.setValue(series.alpha)
            try:
                self.line_style_control.setCurrentValue(LineStyleType(series.line_style))
            except ValueError:
                self.line_style_control.setCurrentValue(LineStyleType.SOLID)

            # "Markers enabled" isn't a separate persisted flag: it's implied
            # by marker_style != MarkerType.NONE (see _on_style_changed). If
            # markers are off, the shape control keeps showing the last
            # remembered shape (defaulting to circle) rather than "none",
            # since "none" isn't offered as a selectable shape here.
            markers_enabled = series.marker_style != MarkerType.NONE.value
            self.markers_enabled_toggle.blockSignals(True)
            self.markers_enabled_toggle.setChecked(markers_enabled)
            self.markers_enabled_toggle.blockSignals(False)

            shape_value = series.marker_style if markers_enabled else MarkerType.CIRCLE.value
            try:
                self.marker_shape_control.setCurrentValue(MarkerType(shape_value))
            except ValueError:
                self.marker_shape_control.setCurrentValue(MarkerType.CIRCLE)

            self.marker_size_slider.setValue(series.marker_size)

            # marker_color == "" is the existing "match line color" convention.
            self.marker_color_row.setCurrentColor(series.marker_color or series.color)
            self.marker_match_line_toggle.blockSignals(True)
            self.marker_match_line_toggle.setChecked(series.marker_color == "")
            self.marker_match_line_toggle.blockSignals(False)

            self._update_marker_controls_enabled()
        finally:
            self._updating_controls = previous_guard

    def _load_fit_into_controls(self, fit):
        """Load fit data into the configuration controls."""
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            # For fit data, disable dataset/column controls since they're not editable
            self.dataset_combo.setEnabled(False)
            self.x_column_combo.setEnabled(False)
            self.y_column_combo.setEnabled(False)
            self.series_y_axis_control.setEnabled(False)

            # Show fit info in the label (block signals)
            self.series_label_edit.blockSignals(True)
            self.series_label_edit.setText(fit.label)
            self.series_label_edit.blockSignals(False)
            self._pending_label = fit.label

            # Update style controls to reflect this fit. Fit data has no
            # marker/opacity concept, so markers are forced off and locked.
            self.line_color_row.setCurrentColor(fit.color)
            self.line_width_slider.setValue(fit.line_width)
            self.line_opacity_slider.setValue(1.0)
            try:
                self.line_style_control.setCurrentValue(LineStyleType(fit.line_style))
            except ValueError:
                self.line_style_control.setCurrentValue(LineStyleType.SOLID)

            self.markers_enabled_toggle.blockSignals(True)
            self.markers_enabled_toggle.setChecked(False)
            self.markers_enabled_toggle.blockSignals(False)
            self.marker_size_slider.setValue(0.0)  # Fit lines typically don't have markers
            self._update_marker_controls_enabled()
        finally:
            self._updating_controls = previous_guard

    def _on_label_typing(self, text: str):
        """Buffer label text while user is typing without mutating the model."""
        self._pending_label = text

    def _on_label_committed(self):
        """Persist buffered label to model after editing finishes.

        Unlike the old QListWidget-backed list, the label text isn't shown
        anywhere else while this entry is expanded (its card's title header
        is only (re)built on the next _rebuild_series_cards call), so no
        rebuild is needed here to avoid disruptive focus loss while typing.
        """
        if self._updating_controls or not self.current_chart:
            return
        current_row = self._expanded_series_index
        if current_row < 0:
            return
        total_series = len(self.current_chart.data_series)
        new_label = self._pending_label or self.series_label_edit.text()
        if current_row < total_series:
            if current_row < len(self.current_chart.data_series):
                self.current_chart.data_series[current_row].label = new_label
        else:
            fit_index = current_row - total_series
            if 0 <= fit_index < len(self.current_chart.fit_data):
                self.current_chart.fit_data[fit_index].label = new_label
        self._pending_label = new_label

    def _reset_controls_for_series(self):
        """Reset controls for editing regular data series."""
        self.dataset_combo.setEnabled(True)
        self.x_column_combo.setEnabled(True)
        self.y_column_combo.setEnabled(True)
        self.series_y_axis_control.setEnabled(True)

    def _clear_controls(self):
        """Reset panel controls to neutral defaults without touching any chart."""
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self.title_edit.clear()
            self.title_font_size_spin.setValue(14)
            self.subtitle_edit.clear()
            self.subtitle_font_size_spin.setValue(12)
            self.chart_padding_spin.setValue(2.0)
            self.chart_type_control.setCurrentValue(ChartType.SCATTER)
            self.chart_size_combo.setCurrentIndex(self.chart_size_combo.count() - 1)
            self.chart_width_spin.setValue(20.0)
            self.chart_height_spin.setValue(15.0)
            self._custom_size_prefilled = False
            self.chart_dpi_combo.setCurrentIndex(self.chart_dpi_combo.count() - 1)
            self.chart_dpi_spin.setValue(100)
            self._custom_dpi_prefilled = False
            self.hist_bins_spin.setValue(20)
            self._update_hist_bins_visibility()
            for prefix in ("x", "y", "y2"):
                self._read_axis_config(prefix, {})
            self._refresh_axis_chips()
            self.show_legend_toggle.setChecked(True)
            self.legend_columns_control.setCurrentValue(1)
            self.legend_show_frame_toggle.setChecked(True)
            self.legend_bg_color_row.setCurrentColor("#ffffff")
            self.legend_bg_opacity_slider.setValue(1.0)
            self._update_legend_controls_enabled()
            self.series_label_edit.clear()
        finally:
            self._updating_controls = previous_guard

    def _get_next_series_color(self) -> str:
        """Get the next color for a new series."""
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
                 "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
        
        if not self.current_chart or not self.current_chart.data_series:
            return colors[0]
        
        return colors[len(self.current_chart.data_series) % len(colors)]

    def set_project(self, project):
        """Set the current project."""
        self.current_project = project
        self._update_datasets()
    
    def _update_datasets(self):
        """Update the available datasets."""
        self.dataset_combo.clear()
        self.datasets = []
        
        if self.current_project:
            # Iterate through all items in the project to find datasets
            for item in self.current_project.get_all_items():
                if isinstance(item, Dataset):
                    self.dataset_combo.addItem(item.name, item.id)
                    self.datasets.append(item)
    
    def _populate_column_combos(self, dataset_id):
        """Fill the x/y column combos with the columns of the given dataset.

        Signals are blocked while clearing/populating so this can safely be
        called from contexts that don't want side effects from
        currentTextChanged (e.g. while loading a series into controls).

        Returns the list of columns populated (empty list if none).
        """
        if not dataset_id or not self.current_project:
            return []
        dataset = self.current_project.find_item(dataset_id)
        if isinstance(dataset, Dataset) and dataset.data is not None:
            columns = list(dataset.data.columns)
            self.x_column_combo.blockSignals(True)
            self.y_column_combo.blockSignals(True)
            try:
                self.x_column_combo.clear()
                self.y_column_combo.clear()
                for column in columns:
                    self.x_column_combo.addItem(column)
                    self.y_column_combo.addItem(column)
            finally:
                self.x_column_combo.blockSignals(False)
                self.y_column_combo.blockSignals(False)
            return columns
        return []

    def _on_dataset_changed(self):
        """Handle dataset selection change."""
        dataset_id = self.dataset_combo.currentData()
        columns = self._populate_column_combos(dataset_id)

        # Set defaults if possible
        if columns:
            self.x_column_combo.setCurrentIndex(0)
            self.y_column_combo.setCurrentIndex(1 if len(columns) >= 2 else 0)

        # setCurrentIndex() only emits currentTextChanged when the index
        # actually changes, which it won't for indices auto-selected by
        # _populate_column_combos while signals were blocked. Sync
        # explicitly so the selected series' x_column/y_column never go
        # stale relative to the combos.
        self._on_series_config_changed()
    
    def _on_apply(self):
        """Handle apply button click."""
        if not self.current_chart:
            return
        command = ApplyChartPropertiesCommand(
            self.app_context,
            chart_id=self.current_chart.id,
            apply_fn=self.apply_to_chart,
            old_snapshot=self._loaded_snapshot,
        )
        self.command_executor.execute_command(command)

        # The applied state is the new baseline for Cancel / the next Apply.
        self._loaded_snapshot = snapshot_chart_state(self.current_chart)
        self._has_unsaved_changes = False
        self._update_status_indicator()
    
    def _on_reset(self):
        """Revert live edits back to the last loaded/applied state."""
        if not self.current_chart or self._loaded_snapshot is None:
            return
        restore_chart_state(self.current_chart, self._loaded_snapshot)
        self.load_chart_object(self.current_chart)
        self.publish_event(ChartEvents.CHART_UPDATED, {
            "chart_id": self.current_chart.id,
            "update_type": "config_updated",
        })
    
    def load_chart_object(self, chart):
        """Load a Chart object into the panel for editing.

        Args:
            chart: Chart object to load, or None to clear
        """
        self.current_chart = chart
        self._loaded_snapshot = snapshot_chart_state(chart) if chart else None
        self._has_unsaved_changes = False
        self._chart_type_touched_by_user = False
        self._update_status_indicator()

        if chart:
            # Ensure datasets are available (important after opening a project file)
            self._ensure_datasets_loaded()
            # Populate controls without letting their change signals write
            # half-loaded values back into chart.config (that feedback loop
            # corrupted chart settings on every tab switch).
            previous_guard = self._updating_controls
            self._updating_controls = True
            try:
                # Load basic info
                self.title_edit.setText(chart.config.get("title", chart.name))
                self.title_font_size_spin.setValue(chart.config.get("title_font_size", 14))
                self.subtitle_edit.setText(chart.config.get("subtitle", ""))
                self.subtitle_font_size_spin.setValue(chart.config.get("subtitle_font_size", 12))
                self.chart_padding_spin.setValue(chart.config.get("chart_padding", 2.0))

                # QComboBox.findData() is unreliable for tuple-valued itemData
                # (Qt's QVariant comparison doesn't match Python tuple equality
                # here), so look up the matching index manually.
                target_size = (chart.config.get("width_cm"), chart.config.get("height_cm"))
                size_index = -1
                for i in range(self.chart_size_combo.count()):
                    if self.chart_size_combo.itemData(i) == target_size:
                        size_index = i
                        break

                self._custom_size_prefilled = False
                if size_index >= 0:
                    self.chart_size_combo.setCurrentIndex(size_index)
                elif target_size[0] is not None and target_size[1] is not None:
                    self.chart_size_combo.setCurrentIndex(self.chart_size_combo.findData("custom"))
                    self.chart_width_spin.setValue(target_size[0])
                    self.chart_height_spin.setValue(target_size[1])
                    self._custom_size_prefilled = True
                else:
                    self.chart_size_combo.setCurrentIndex(self.chart_size_combo.count() - 1)

                self._custom_dpi_prefilled = False
                dpi_value = chart.config.get("dpi")
                dpi_index = self.chart_dpi_combo.findData(dpi_value)
                if dpi_index >= 0:
                    self.chart_dpi_combo.setCurrentIndex(dpi_index)
                elif dpi_value is not None:
                    self.chart_dpi_combo.setCurrentIndex(self.chart_dpi_combo.findData("custom"))
                    self.chart_dpi_spin.setValue(dpi_value)
                    self._custom_dpi_prefilled = True
                else:
                    self.chart_dpi_combo.setCurrentIndex(self.chart_dpi_combo.count() - 1)

                # Set chart type
                chart_type_map = {
                    "line": ChartType.LINE,
                    "scatter": ChartType.SCATTER,
                    "bar": ChartType.BAR,
                    "hist": ChartType.HISTOGRAM,
                }
                self._loaded_chart_type_supported = chart.chart_type in chart_type_map
                chart_type = chart_type_map.get(chart.chart_type, ChartType.LINE)
                self.chart_type_control.setCurrentValue(chart_type)
                self._update_hist_bins_visibility()

                # Expand the first series/fit entry and rebuild the card list
                # (this also (re)loads it into the config form controls).
                self._expanded_series_index = 0
                self._rebuild_series_cards()
                # (_rebuild_series_cards already loads series/fit 0's style
                # into the Style tab controls via _build_expanded_series_card.)

                # Load configuration
                config = chart.config
                for prefix in ("x", "y", "y2"):
                    self._read_axis_config(prefix, config)
                self._refresh_axis_chips()
                self._show_axis_form("x")
                self.axis_chips.setCurrentValue("x")

                self.show_legend_toggle.setChecked(config.get("show_legend", True))
                legend_position_value = config.get("legend_position", "upper right")
                for i in range(self.legend_position_combo.count()):
                    if (self.legend_position_combo.itemData(i)
                            and self.legend_position_combo.itemData(i).value == legend_position_value):
                        self.legend_position_combo.setCurrentIndex(i)
                        break
                self.legend_font_size_spin.setValue(config.get("legend_font_size", 10))
                self.legend_columns_control.setCurrentValue(config.get("legend_columns", 1))
                self.legend_show_frame_toggle.setChecked(config.get("legend_show_frame", True))
                self.legend_bg_color_row.setCurrentColor(config.get("legend_bg_color", "#ffffff"))
                self.legend_bg_opacity_slider.setValue(config.get("legend_bg_alpha", 1.0))
                self._update_legend_controls_enabled()
                self.hist_bins_spin.setValue(config.get("hist_bins", 20))
            finally:
                self._updating_controls = previous_guard

        else:
            # Clear/default values
            self._clear_controls()
            self._expanded_series_index = 0
            self._rebuild_series_cards()
    
    def apply_to_chart(self, chart):
        """Apply current panel settings to a Chart object.
        
        Args:
            chart: Chart object to update
        """
        if not chart:
            return
        
        # Update basic chart properties
        chart.config["title"] = self.title_edit.text()
        chart.config["title_font_size"] = self.title_font_size_spin.value()
        chart.config["subtitle"] = self.subtitle_edit.text()
        chart.config["subtitle_font_size"] = self.subtitle_font_size_spin.value()
        chart.config["chart_padding"] = self.chart_padding_spin.value()
        chart.config["width_cm"], chart.config["height_cm"] = self._size_from_controls()
        chart.config["dpi"] = self._dpi_from_controls()
        for prefix in ("x", "y", "y2"):
            self._write_axis_config(prefix, chart.config)
        chart.config["show_legend"] = self.show_legend_toggle.isChecked()
        if self.legend_position_combo.currentData():
            chart.config["legend_position"] = self.legend_position_combo.currentData().value
        chart.config["legend_font_size"] = self.legend_font_size_spin.value()
        chart.config["legend_columns"] = self.legend_columns_control.currentValue()
        chart.config["legend_show_frame"] = self.legend_show_frame_toggle.isChecked()
        chart.config["legend_bg_color"] = self.legend_bg_color_row.currentColor()
        chart.config["legend_bg_alpha"] = self.legend_bg_opacity_slider.value()
        chart.config["hist_bins"] = self.hist_bins_spin.value()

        # Update chart type
        chart_type_map = {
            ChartType.LINE: "line",
            ChartType.SCATTER: "scatter",
            ChartType.BAR: "bar",
            ChartType.HISTOGRAM: "hist",
        }
        chart_type = self.chart_type_control.currentValue()
        if chart_type in chart_type_map:
            chart.chart_type = chart_type_map[chart_type]
        
        # Apply style updates to the currently selected series or fit data
        current_row = self._expanded_series_index
        if current_row >= 0:
            total_series = len(chart.data_series)

            if current_row < total_series:
                # Update data series
                series = chart.data_series[current_row]

                series.color = self.line_color_row.currentColor()
                series.line_style = self.line_style_control.currentValue().value
                series.line_width = self.line_width_slider.value()
                series.y_axis = self.series_y_axis_control.currentValue()
                series.alpha = self.line_opacity_slider.value()

                if self.markers_enabled_toggle.isChecked():
                    series.marker_style = self.marker_shape_control.currentValue().value
                    series.marker_size = self.marker_size_slider.value()
                    series.marker_color = (
                        "" if self.marker_match_line_toggle.isChecked()
                        else self.marker_color_row.currentColor()
                    )
                else:
                    series.marker_style = MarkerType.NONE.value

                self.logger.debug(
                    "Applied style to data series %d: %s (color=%s, marker_color=%s)",
                    current_row, series.label, series.color, series.marker_color
                )
            else:
                # Update fit data
                fit_index = current_row - total_series
                if 0 <= fit_index < len(chart.fit_data):
                    fit = chart.fit_data[fit_index]
                    fit.color = self.line_color_row.currentColor()
                    fit.line_style = self.line_style_control.currentValue().value
                    fit.line_width = self.line_width_slider.value()

                    self.logger.debug(
                        "Applied style to fit data %d: %s (color=%s)",
                        fit_index, fit.label, fit.color
                    )
        
        # If no series exist but we have configuration, create a default series
        if not chart.data_series:
            dataset_id = self.dataset_combo.currentData()
            dataset_name = self.dataset_combo.currentText()
            x_column = self.x_column_combo.currentText()
            y_column = self.y_column_combo.currentText()
            
            if dataset_id and x_column and y_column:
                chart.add_data_series(
                    dataset_id=dataset_id,
                    x_column=x_column,
                    y_column=y_column,
                    color=self.line_color_row.currentColor(),
                    line_width=self.line_width_slider.value(),
                    marker_size=self.marker_size_slider.value(),
                    label=f"{dataset_name}:{y_column}",
                    y_axis=self.series_y_axis_control.currentValue()
                )
        
        chart.update_modified_time()
    
