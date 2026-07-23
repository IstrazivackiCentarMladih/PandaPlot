"""Chart properties side panel for configuring chart appearance and data."""
from typing import List, Optional, override

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
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
from pandaplot.gui.components.common.section_header import SectionHeader
from pandaplot.gui.components.common.segmented_control import SegmentedControl
from pandaplot.gui.components.common.slider_with_spinbox import SliderWithSpinbox
from pandaplot.gui.components.common.toggle_switch import ToggleSwitch
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


class ColorButton(QPushButton):
    """A button that displays and allows selection of colors."""
    
    colorChanged = Signal(str)

    def __init__(self, app_context: AppContext, parent=None, color: str = "#1f77b4"):
        super().__init__(parent)
        self.app_context = app_context
        self._color = color
        self.setFixedSize(30, 25)
        self.clicked.connect(self._select_color)
        self._update_appearance()
    
    def set_color(self, color: str):
        """Set the button color."""
        self._color = color
        self._update_appearance()
        if not self.signalsBlocked():
            self.colorChanged.emit(color)
    
    def get_color(self) -> str:
        """Get the current color."""
        return self._color
    
    def _select_color(self):
        """Open color dialog to select a new color."""
        color = QColorDialog.getColor(QColor(self._color), self, "Select Color")
        if color.isValid():
            self.set_color(color.name())
    
    def _update_appearance(self):
        """Trigger a repaint with theme-aware button styling."""
        # Get theme colors if parent has app_context
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        bg_color = palette.get("card_hover", "#f5f5f5")
        border_color = palette.get("card_border", "#888")
        hover_color = palette.get("card_bg", "#eaeaea")
        pressed_color = palette.get("card_border", "#e0e0e0")
        
        self.setStyleSheet(f"""
            QPushButton {{ 
                background: {bg_color}; 
                border: 1px solid {border_color}; 
                border-radius: 4px; 
            }}
            QPushButton:hover {{ 
                background: {hover_color}; 
            }}
            QPushButton:pressed {{ 
                background: {pressed_color}; 
            }}
        """)
        self.update()

    def paintEvent(self, event):  # noqa: D401 (Qt override)
        super().paintEvent(event)
        # Draw inner color swatch
        painter = QPainter(self)
        swatch_rect = self.rect().adjusted(6, 6, -6, -6)
        painter.setPen(QColor("#555555"))
        painter.setBrush(QColor(self._color))
        painter.drawRect(swatch_rect)


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

        # Update all color buttons
        self._update_color_buttons()

        # Footer (DirtyFooter) theme token propagation
        tokens = theme_manager.get_design_tokens()
        self.footer.set_tokens(tokens)
        self.chart_type_control.set_tokens(tokens)

        # Style tab: shared widgets
        self.style_series_chips.set_tokens(tokens)
        self.line_color_row.set_tokens(tokens)
        self.line_style_control.set_tokens(tokens)
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

    def _update_color_buttons(self):
        """Update all ColorButton instances with current theme."""
        color_buttons = [
            getattr(self, "legend_bg_color_button", None)
        ]
        
        for button in color_buttons:
            if button and isinstance(button, ColorButton):
                button._update_appearance()
    
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
        info_layout.addWidget(self.title_edit, 0, 1)
        self.title_font_size_spin = QSpinBox()
        self.title_font_size_spin.setRange(8, 32)
        self.title_font_size_spin.setValue(14)
        info_layout.addWidget(self.title_font_size_spin, 0, 2)

        info_layout.addWidget(QLabel("Subtitle:"), 1, 0)
        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("Optional")
        info_layout.addWidget(self.subtitle_edit, 1, 1, 1, 2)

        info_layout.addWidget(QLabel("Type:"), 2, 0)
        self.chart_type_control = SegmentedControl(
            [
                ("Scatter", ChartType.SCATTER),
                ("Line", ChartType.LINE),
                ("Bar", ChartType.BAR),
                ("Histogram", ChartType.HISTOGRAM),
            ]
        )
        info_layout.addWidget(self.chart_type_control, 2, 1, 1, 2)

        self.hist_bins_label = QLabel("Histogram Bins:")
        info_layout.addWidget(self.hist_bins_label, 3, 0)
        self.hist_bins_spin = QSpinBox()
        self.hist_bins_spin.setRange(2, 200)
        self.hist_bins_spin.setValue(20)
        self.hist_bins_spin.setToolTip("Number of bins used when chart type is Histogram")
        info_layout.addWidget(self.hist_bins_spin, 3, 1)
        self._update_hist_bins_visibility()

        info_layout.addWidget(QLabel("Size:"), 4, 0)
        self.chart_size_combo = QComboBox()
        self.chart_size_combo.addItem("15 × 8 cm", (15.0, 8.0))
        self.chart_size_combo.addItem("20 × 15 cm", (20.0, 15.0))
        self.chart_size_combo.addItem("Use app default", None)
        info_layout.addWidget(self.chart_size_combo, 4, 1, 1, 2)

        info_layout.addWidget(QLabel("DPI:"), 5, 0)
        self.chart_dpi_combo = QComboBox()
        self.chart_dpi_combo.addItem("100 dpi", 100)
        self.chart_dpi_combo.addItem("150 dpi", 150)
        self.chart_dpi_combo.addItem("300 dpi", 300)
        self.chart_dpi_combo.addItem("Use app default", None)
        info_layout.addWidget(self.chart_dpi_combo, 5, 1, 1, 2)

        hint = QLabel("Size affects export & default fonts")
        hint.setStyleSheet("font-size: 10.5px;")
        info_layout.addWidget(hint, 6, 0, 1, 3)

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

    def _refresh_style_chips(self):
        """Sync the Style tab's chip row with the same series+fit list the
        Data tab's cards are built from, keeping the chip row's selection in
        lockstep with `self._expanded_series_index` (the single, panel-wide
        "currently edited entry" state also driven by Data-tab card expand).

        Chip values are the combined index (int), not the series/fit object
        itself, so selecting a chip can drive `_expand_series` directly
        without needing to search for the clicked object's index.
        """
        if not hasattr(self, "style_series_chips"):
            # The Data tab (built first) triggers an initial
            # _rebuild_series_cards() call before the Style tab (and its chip
            # row) exists yet. There is no chart loaded yet at that point
            # either, so there is nothing to reflect; the chip row is
            # populated for real the next time a chart is loaded.
            return
        chip_items = []
        for index, series in enumerate(self.current_chart.data_series):
            label = series.label or f"{series.dataset_id}:{series.y_column}"
            chip_items.append((label, index))
        total_series = len(self.current_chart.data_series)
        for fit_offset, fit in enumerate(self.current_chart.fit_data):
            index = total_series + fit_offset
            chip_items.append((f"\U0001f527 {fit.label}", index))

        # Neither setItems nor setCurrentValue emits currentValueChanged (only
        # a user click on a chip does), so no signal-blocking is needed here
        # to avoid re-entering _expand_series.
        self.style_series_chips.setItems(chip_items)
        self.style_series_chips.setCurrentValue(self._expanded_series_index)

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
        is_secondary = y_axis == YAxis.SECONDARY
        badge = QLabel("Y₂" if is_secondary else "Y₁")
        bg = tokens.get("y2_accent_bg") if is_secondary else tokens.get("surface_inset", "#eee")
        fg = tokens.get("y2_accent") if is_secondary else tokens.get("text_muted", "#666")
        badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            f"border-radius: {tokens.get('radius_chip', 12)}px; "
            "padding: 1px 8px; font-size: 10px; font-weight: 600;"
        )
        return badge

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
        if not is_fit:
            header.addWidget(self._build_y_axis_badge(series.y_axis, tokens))
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
        self.style_series_chips.currentValueChanged.connect(self._expand_series)
        layout.addWidget(self.style_series_chips)

        # LINE group
        line_card = Card()
        line_layout = QGridLayout(line_card)
        line_layout.addWidget(SectionHeader("Line"), 0, 0, 1, 2)

        line_layout.addWidget(QLabel("Color:"), 1, 0)
        self.line_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        line_layout.addWidget(self.line_color_row, 1, 1)

        line_layout.addWidget(QLabel("Style:"), 2, 0)
        self.line_style_control = SegmentedControl(
            [
                ("Solid", LineStyleType.SOLID),
                ("Dashed", LineStyleType.DASHED),
                ("Dotted", LineStyleType.DOTTED),
                ("Dash-Dot", LineStyleType.DASHDOT),
                ("None", LineStyleType.NONE),
            ]
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
        marker_card = Card()
        marker_layout = QGridLayout(marker_card)

        marker_header_row = QHBoxLayout()
        marker_header_row.addWidget(SectionHeader("Markers"))
        marker_header_row.addStretch(1)
        self.markers_enabled_toggle = ToggleSwitch()
        marker_header_row.addWidget(self.markers_enabled_toggle)
        marker_layout.addLayout(marker_header_row, 0, 0, 1, 2)

        marker_layout.addWidget(QLabel("Shape:"), 1, 0)
        self.marker_shape_control = SegmentedControl(
            [
                ("●", MarkerType.CIRCLE),
                ("■", MarkerType.SQUARE),
                ("▲", MarkerType.TRIANGLE),
                ("◆", MarkerType.DIAMOND),
                ("★", MarkerType.STAR),
                ("+", MarkerType.PLUS),
                ("✕", MarkerType.CROSS),
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
        return widget
    
    def _create_axes_tab(self) -> QWidget:
        """Create the axes configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # X Axis group
        x_axis_group = QGroupBox("X Axis")
        x_axis_layout = QGridLayout(x_axis_group)
        
        x_axis_layout.addWidget(QLabel("Label:"), 0, 0)
        self.x_label_edit = QLineEdit()
        x_axis_layout.addWidget(self.x_label_edit, 0, 1)
        
        x_axis_layout.addWidget(QLabel("Font Size:"), 1, 0)
        self.x_font_size_spin = QSpinBox()
        self.x_font_size_spin.setRange(6, 24)
        self.x_font_size_spin.setValue(12)
        x_axis_layout.addWidget(self.x_font_size_spin, 1, 1)
        
        x_axis_layout.addWidget(QLabel("Scale:"), 2, 0)
        self.x_scale_combo = QComboBox()
        for scale in ScaleType:
            self.x_scale_combo.addItem(scale.value.title(), scale)
        x_axis_layout.addWidget(self.x_scale_combo, 2, 1)

        x_axis_layout.addWidget(QLabel("Limits:"), 3, 0)
        self.x_auto_limits_check = QCheckBox("Auto")
        self.x_auto_limits_check.setChecked(True)
        x_axis_layout.addWidget(self.x_auto_limits_check, 3, 1)

        x_axis_layout.addWidget(QLabel("Min:"), 4, 0)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1e9, 1e9)
        self.x_min_spin.setValue(0.0)
        self.x_min_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_min_spin, 4, 1)

        x_axis_layout.addWidget(QLabel("Max:"), 5, 0)
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1e9, 1e9)
        self.x_max_spin.setValue(1.0)
        self.x_max_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_max_spin, 5, 1)

        x_axis_layout.addWidget(QLabel("Tick Mode:"), 6, 0)
        self.x_tick_mode_combo = QComboBox()
        self.x_tick_mode_combo.addItem("Auto", "auto")
        self.x_tick_mode_combo.addItem("Fixed Count", "count")
        self.x_tick_mode_combo.addItem("Fixed Step", "step")
        x_axis_layout.addWidget(self.x_tick_mode_combo, 6, 1)

        x_axis_layout.addWidget(QLabel("Tick Count:"), 7, 0)
        self.x_tick_count_spin = QSpinBox()
        self.x_tick_count_spin.setRange(2, 50)
        self.x_tick_count_spin.setValue(5)
        self.x_tick_count_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_tick_count_spin, 7, 1)

        x_axis_layout.addWidget(QLabel("Tick Step:"), 8, 0)
        self.x_tick_step_spin = QDoubleSpinBox()
        self.x_tick_step_spin.setRange(0.001, 1e9)
        self.x_tick_step_spin.setValue(1.0)
        self.x_tick_step_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_tick_step_spin, 8, 1)

        x_axis_layout.addWidget(QLabel("Tick Format:"), 9, 0)
        self.x_tick_format_combo = QComboBox()
        self.x_tick_format_combo.addItem("Auto", "auto")
        self.x_tick_format_combo.addItem("Integer", "integer")
        self.x_tick_format_combo.addItem("1 Decimal", "1decimal")
        self.x_tick_format_combo.addItem("2 Decimals", "2decimal")
        self.x_tick_format_combo.addItem("Scientific", "scientific")
        self.x_tick_format_combo.addItem("Custom...", "custom")
        x_axis_layout.addWidget(self.x_tick_format_combo, 9, 1)

        x_axis_layout.addWidget(QLabel("Custom Format:"), 10, 0)
        self.x_tick_format_custom_edit = QLineEdit()
        self.x_tick_format_custom_edit.setPlaceholderText("e.g. {:.2f} units")
        self.x_tick_format_custom_edit.setEnabled(False)
        x_axis_layout.addWidget(self.x_tick_format_custom_edit, 10, 1)

        self.x_grid_check = QCheckBox("Show Grid")
        self.x_grid_check.setChecked(True)
        x_axis_layout.addWidget(self.x_grid_check, 11, 0, 1, 2)

        layout.addWidget(x_axis_group)
        
        # Y Axis group
        y_axis_group = QGroupBox("Y Axis")
        y_axis_layout = QGridLayout(y_axis_group)
        
        y_axis_layout.addWidget(QLabel("Label:"), 0, 0)
        self.y_label_edit = QLineEdit()
        y_axis_layout.addWidget(self.y_label_edit, 0, 1)
        
        y_axis_layout.addWidget(QLabel("Font Size:"), 1, 0)
        self.y_font_size_spin = QSpinBox()
        self.y_font_size_spin.setRange(6, 24)
        self.y_font_size_spin.setValue(12)
        y_axis_layout.addWidget(self.y_font_size_spin, 1, 1)
        
        y_axis_layout.addWidget(QLabel("Scale:"), 2, 0)
        self.y_scale_combo = QComboBox()
        for scale in ScaleType:
            self.y_scale_combo.addItem(scale.value.title(), scale)
        y_axis_layout.addWidget(self.y_scale_combo, 2, 1)

        y_axis_layout.addWidget(QLabel("Limits:"), 3, 0)
        self.y_auto_limits_check = QCheckBox("Auto")
        self.y_auto_limits_check.setChecked(True)
        y_axis_layout.addWidget(self.y_auto_limits_check, 3, 1)

        y_axis_layout.addWidget(QLabel("Min:"), 4, 0)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1e9, 1e9)
        self.y_min_spin.setValue(0.0)
        self.y_min_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_min_spin, 4, 1)

        y_axis_layout.addWidget(QLabel("Max:"), 5, 0)
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1e9, 1e9)
        self.y_max_spin.setValue(1.0)
        self.y_max_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_max_spin, 5, 1)

        y_axis_layout.addWidget(QLabel("Tick Mode:"), 6, 0)
        self.y_tick_mode_combo = QComboBox()
        self.y_tick_mode_combo.addItem("Auto", "auto")
        self.y_tick_mode_combo.addItem("Fixed Count", "count")
        self.y_tick_mode_combo.addItem("Fixed Step", "step")
        y_axis_layout.addWidget(self.y_tick_mode_combo, 6, 1)

        y_axis_layout.addWidget(QLabel("Tick Count:"), 7, 0)
        self.y_tick_count_spin = QSpinBox()
        self.y_tick_count_spin.setRange(2, 50)
        self.y_tick_count_spin.setValue(5)
        self.y_tick_count_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_tick_count_spin, 7, 1)

        y_axis_layout.addWidget(QLabel("Tick Step:"), 8, 0)
        self.y_tick_step_spin = QDoubleSpinBox()
        self.y_tick_step_spin.setRange(0.001, 1e9)
        self.y_tick_step_spin.setValue(1.0)
        self.y_tick_step_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_tick_step_spin, 8, 1)

        y_axis_layout.addWidget(QLabel("Tick Format:"), 9, 0)
        self.y_tick_format_combo = QComboBox()
        self.y_tick_format_combo.addItem("Auto", "auto")
        self.y_tick_format_combo.addItem("Integer", "integer")
        self.y_tick_format_combo.addItem("1 Decimal", "1decimal")
        self.y_tick_format_combo.addItem("2 Decimals", "2decimal")
        self.y_tick_format_combo.addItem("Scientific", "scientific")
        self.y_tick_format_combo.addItem("Custom...", "custom")
        y_axis_layout.addWidget(self.y_tick_format_combo, 9, 1)

        y_axis_layout.addWidget(QLabel("Custom Format:"), 10, 0)
        self.y_tick_format_custom_edit = QLineEdit()
        self.y_tick_format_custom_edit.setPlaceholderText("e.g. {:.2f} units")
        self.y_tick_format_custom_edit.setEnabled(False)
        y_axis_layout.addWidget(self.y_tick_format_custom_edit, 10, 1)

        self.y_grid_check = QCheckBox("Show Grid")
        self.y_grid_check.setChecked(True)
        y_axis_layout.addWidget(self.y_grid_check, 11, 0, 1, 2)

        layout.addWidget(y_axis_group)

        # Secondary Y Axis group - only used by series set to "Secondary" in
        # the Data Series section.
        y2_axis_group = QGroupBox("Secondary Y Axis")
        y2_axis_layout = QGridLayout(y2_axis_group)

        y2_axis_layout.addWidget(QLabel("Label:"), 0, 0)
        self.y2_label_edit = QLineEdit()
        y2_axis_layout.addWidget(self.y2_label_edit, 0, 1)

        layout.addWidget(y2_axis_group)

        layout.addStretch()
        return widget
    
    def _create_legend_tab(self) -> QWidget:
        """Create the legend configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Legend group
        legend_group = QGroupBox("Legend")
        legend_layout = QGridLayout(legend_group)
        
        self.legend_show_check = QCheckBox("Show Legend")
        self.legend_show_check.setChecked(True)
        legend_layout.addWidget(self.legend_show_check, 0, 0, 1, 2)
        
        legend_layout.addWidget(QLabel("Position:"), 1, 0)
        self.legend_position_combo = QComboBox()
        for position in LegendPosition:
            self.legend_position_combo.addItem(position.value.title(), position)
        legend_layout.addWidget(self.legend_position_combo, 1, 1)
        
        legend_layout.addWidget(QLabel("Font Size:"), 2, 0)
        self.legend_font_size_spin = QSpinBox()
        self.legend_font_size_spin.setRange(6, 18)
        self.legend_font_size_spin.setValue(10)
        legend_layout.addWidget(self.legend_font_size_spin, 2, 1)
        
        legend_layout.addWidget(QLabel("Background:"), 3, 0)
        self.legend_bg_color_button = ColorButton(self.app_context, None, "#ffffff")
        legend_layout.addWidget(self.legend_bg_color_button, 3, 1)

        self.legend_show_frame_check = QCheckBox("Show Frame")
        self.legend_show_frame_check.setChecked(True)
        legend_layout.addWidget(self.legend_show_frame_check, 4, 0, 1, 2)

        layout.addWidget(legend_group)
        
        layout.addStretch()
        return widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_changed)

        # Connect chart-level configuration changes
        self.chart_type_control.currentValueChanged.connect(self._on_chart_type_index_changed)
        self.hist_bins_spin.valueChanged.connect(self._on_chart_config_changed)
        self.title_edit.textChanged.connect(self._on_chart_config_changed)
        self.title_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.subtitle_edit.textChanged.connect(self._on_chart_config_changed)
        self.chart_size_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.chart_dpi_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.x_label_edit.textChanged.connect(self._on_chart_config_changed)
        self.y_label_edit.textChanged.connect(self._on_chart_config_changed)
        self.y2_label_edit.textChanged.connect(self._on_chart_config_changed)
        self.x_grid_check.toggled.connect(self._on_chart_config_changed)
        self.y_grid_check.toggled.connect(self._on_chart_config_changed)
        self.x_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_scale_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.y_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_scale_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.x_auto_limits_check.toggled.connect(self._on_x_auto_limits_toggled)
        self.x_min_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_max_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_auto_limits_check.toggled.connect(self._on_y_auto_limits_toggled)
        self.y_min_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_max_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_tick_mode_combo.currentIndexChanged.connect(self._on_x_tick_mode_changed)
        self.x_tick_count_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_tick_step_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_tick_format_combo.currentIndexChanged.connect(self._on_x_tick_format_changed)
        self.x_tick_format_custom_edit.textChanged.connect(self._on_chart_config_changed)
        self.y_tick_mode_combo.currentIndexChanged.connect(self._on_y_tick_mode_changed)
        self.y_tick_count_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_tick_step_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_tick_format_combo.currentIndexChanged.connect(self._on_y_tick_format_changed)
        self.y_tick_format_custom_edit.textChanged.connect(self._on_chart_config_changed)
        self.legend_show_check.toggled.connect(self._on_chart_config_changed)
        self.legend_position_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.legend_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.legend_bg_color_button.colorChanged.connect(self._on_chart_config_changed)
        self.legend_show_frame_check.toggled.connect(self._on_chart_config_changed)
        
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

    def _on_x_auto_limits_toggled(self, checked):
        self.x_min_spin.setEnabled(not checked)
        self.x_max_spin.setEnabled(not checked)
        self._on_chart_config_changed()

    def _on_y_auto_limits_toggled(self, checked):
        self.y_min_spin.setEnabled(not checked)
        self.y_max_spin.setEnabled(not checked)
        self._on_chart_config_changed()

    def _on_x_tick_mode_changed(self):
        mode = self.x_tick_mode_combo.currentData()
        self.x_tick_count_spin.setEnabled(mode == "count")
        self.x_tick_step_spin.setEnabled(mode == "step")
        self._on_chart_config_changed()

    def _on_x_tick_format_changed(self):
        self.x_tick_format_custom_edit.setEnabled(self.x_tick_format_combo.currentData() == "custom")
        self._on_chart_config_changed()

    def _on_y_tick_mode_changed(self):
        mode = self.y_tick_mode_combo.currentData()
        self.y_tick_count_spin.setEnabled(mode == "count")
        self.y_tick_step_spin.setEnabled(mode == "step")
        self._on_chart_config_changed()

    def _on_y_tick_format_changed(self):
        self.y_tick_format_custom_edit.setEnabled(self.y_tick_format_combo.currentData() == "custom")
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
        if hasattr(self, "chart_size_combo"):
            size = self.chart_size_combo.currentData()
            config["width_cm"] = size[0] if size else None
            config["height_cm"] = size[1] if size else None
        if hasattr(self, "chart_dpi_combo"):
            config["dpi"] = self.chart_dpi_combo.currentData()
        if hasattr(self, "x_label_edit"):
            config["x_label"] = self.x_label_edit.text()
        if hasattr(self, "y_label_edit"):
            config["y_label"] = self.y_label_edit.text()
        if hasattr(self, "y2_label_edit"):
            config["y2_label"] = self.y2_label_edit.text()
        if hasattr(self, "x_grid_check"):
            config["show_grid_x"] = self.x_grid_check.isChecked()
        if hasattr(self, "y_grid_check"):
            config["show_grid_y"] = self.y_grid_check.isChecked()
        if hasattr(self, "x_font_size_spin"):
            config["x_font_size"] = self.x_font_size_spin.value()
        if hasattr(self, "y_font_size_spin"):
            config["y_font_size"] = self.y_font_size_spin.value()
        if hasattr(self, "x_scale_combo") and self.x_scale_combo.currentData():
            config["x_scale"] = self.x_scale_combo.currentData().value
        if hasattr(self, "y_scale_combo") and self.y_scale_combo.currentData():
            config["y_scale"] = self.y_scale_combo.currentData().value
        if hasattr(self, "x_auto_limits_check"):
            config["x_auto_limits"] = self.x_auto_limits_check.isChecked()
            config["x_min"] = self.x_min_spin.value()
            config["x_max"] = self.x_max_spin.value()
        if hasattr(self, "y_auto_limits_check"):
            config["y_auto_limits"] = self.y_auto_limits_check.isChecked()
            config["y_min"] = self.y_min_spin.value()
            config["y_max"] = self.y_max_spin.value()
        if hasattr(self, "x_tick_mode_combo"):
            config["x_tick_mode"] = self.x_tick_mode_combo.currentData()
            config["x_tick_count"] = self.x_tick_count_spin.value()
            config["x_tick_step"] = self.x_tick_step_spin.value()
            config["x_tick_format"] = self.x_tick_format_combo.currentData()
            config["x_tick_format_custom"] = self.x_tick_format_custom_edit.text()
        if hasattr(self, "y_tick_mode_combo"):
            config["y_tick_mode"] = self.y_tick_mode_combo.currentData()
            config["y_tick_count"] = self.y_tick_count_spin.value()
            config["y_tick_step"] = self.y_tick_step_spin.value()
            config["y_tick_format"] = self.y_tick_format_combo.currentData()
            config["y_tick_format_custom"] = self.y_tick_format_custom_edit.text()
        if hasattr(self, "legend_show_check"):
            config["show_legend"] = self.legend_show_check.isChecked()
        if hasattr(self, "legend_position_combo") and self.legend_position_combo.currentData():
            config["legend_position"] = self.legend_position_combo.currentData().value
        if hasattr(self, "legend_font_size_spin"):
            config["legend_font_size"] = self.legend_font_size_spin.value()
        if hasattr(self, "legend_bg_color_button"):
            config["legend_bg_color"] = self.legend_bg_color_button.get_color()
        if hasattr(self, "legend_show_frame_check"):
            config["legend_show_frame"] = self.legend_show_frame_check.isChecked()
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
            self.chart_type_control.setCurrentValue(ChartType.SCATTER)
            self.chart_size_combo.setCurrentIndex(self.chart_size_combo.count() - 1)
            self.chart_dpi_combo.setCurrentIndex(self.chart_dpi_combo.count() - 1)
            self.hist_bins_spin.setValue(20)
            self._update_hist_bins_visibility()
            self.x_label_edit.clear()
            self.y_label_edit.clear()
            self.x_grid_check.setChecked(True)
            self.y_grid_check.setChecked(True)
            self.x_auto_limits_check.setChecked(True)
            self.y_auto_limits_check.setChecked(True)
            self.legend_show_check.setChecked(True)
            self.legend_show_frame_check.setChecked(True)
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
                # QComboBox.findData() is unreliable for tuple-valued itemData
                # (Qt's QVariant comparison doesn't match Python tuple equality
                # here), so look up the matching index manually.
                target_size = (chart.config.get("width_cm"), chart.config.get("height_cm"))
                size_index = -1
                for i in range(self.chart_size_combo.count()):
                    if self.chart_size_combo.itemData(i) == target_size:
                        size_index = i
                        break
                self.chart_size_combo.setCurrentIndex(
                    size_index if size_index >= 0 else self.chart_size_combo.count() - 1
                )
                dpi_index = self.chart_dpi_combo.findData(chart.config.get("dpi"))
                self.chart_dpi_combo.setCurrentIndex(
                    dpi_index if dpi_index >= 0 else self.chart_dpi_combo.count() - 1
                )

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
                self.x_label_edit.setText(config.get("x_label", ""))
                self.y_label_edit.setText(config.get("y_label", ""))
                self.y2_label_edit.setText(config.get("y2_label", ""))
                self.x_grid_check.setChecked(config.get("show_grid_x", True))
                self.y_grid_check.setChecked(config.get("show_grid_y", True))
                self.x_font_size_spin.setValue(config.get("x_font_size", 12))
                self.y_font_size_spin.setValue(config.get("y_font_size", 12))
                x_scale_value = config.get("x_scale", "linear")
                for i in range(self.x_scale_combo.count()):
                    if self.x_scale_combo.itemData(i) and self.x_scale_combo.itemData(i).value == x_scale_value:
                        self.x_scale_combo.setCurrentIndex(i)
                        break
                y_scale_value = config.get("y_scale", "linear")
                for i in range(self.y_scale_combo.count()):
                    if self.y_scale_combo.itemData(i) and self.y_scale_combo.itemData(i).value == y_scale_value:
                        self.y_scale_combo.setCurrentIndex(i)
                        break

                self.x_auto_limits_check.setChecked(config.get("x_auto_limits", True))
                self.x_min_spin.setValue(config.get("x_min", 0.0))
                self.x_max_spin.setValue(config.get("x_max", 1.0))
                self.x_min_spin.setEnabled(not self.x_auto_limits_check.isChecked())
                self.x_max_spin.setEnabled(not self.x_auto_limits_check.isChecked())

                self.y_auto_limits_check.setChecked(config.get("y_auto_limits", True))
                self.y_min_spin.setValue(config.get("y_min", 0.0))
                self.y_max_spin.setValue(config.get("y_max", 1.0))
                self.y_min_spin.setEnabled(not self.y_auto_limits_check.isChecked())
                self.y_max_spin.setEnabled(not self.y_auto_limits_check.isChecked())

                x_tick_mode = config.get("x_tick_mode", "auto")
                for i in range(self.x_tick_mode_combo.count()):
                    if self.x_tick_mode_combo.itemData(i) == x_tick_mode:
                        self.x_tick_mode_combo.setCurrentIndex(i)
                        break
                self.x_tick_count_spin.setValue(config.get("x_tick_count", 5))
                self.x_tick_step_spin.setValue(config.get("x_tick_step", 1.0))
                self.x_tick_count_spin.setEnabled(x_tick_mode == "count")
                self.x_tick_step_spin.setEnabled(x_tick_mode == "step")

                x_tick_format = config.get("x_tick_format", "auto")
                for i in range(self.x_tick_format_combo.count()):
                    if self.x_tick_format_combo.itemData(i) == x_tick_format:
                        self.x_tick_format_combo.setCurrentIndex(i)
                        break
                self.x_tick_format_custom_edit.setText(config.get("x_tick_format_custom", ""))
                self.x_tick_format_custom_edit.setEnabled(x_tick_format == "custom")

                y_tick_mode = config.get("y_tick_mode", "auto")
                for i in range(self.y_tick_mode_combo.count()):
                    if self.y_tick_mode_combo.itemData(i) == y_tick_mode:
                        self.y_tick_mode_combo.setCurrentIndex(i)
                        break
                self.y_tick_count_spin.setValue(config.get("y_tick_count", 5))
                self.y_tick_step_spin.setValue(config.get("y_tick_step", 1.0))
                self.y_tick_count_spin.setEnabled(y_tick_mode == "count")
                self.y_tick_step_spin.setEnabled(y_tick_mode == "step")

                y_tick_format = config.get("y_tick_format", "auto")
                for i in range(self.y_tick_format_combo.count()):
                    if self.y_tick_format_combo.itemData(i) == y_tick_format:
                        self.y_tick_format_combo.setCurrentIndex(i)
                        break
                self.y_tick_format_custom_edit.setText(config.get("y_tick_format_custom", ""))
                self.y_tick_format_custom_edit.setEnabled(y_tick_format == "custom")

                self.legend_show_check.setChecked(config.get("show_legend", True))
                legend_position_value = config.get("legend_position", "upper right")
                for i in range(self.legend_position_combo.count()):
                    if (self.legend_position_combo.itemData(i)
                            and self.legend_position_combo.itemData(i).value == legend_position_value):
                        self.legend_position_combo.setCurrentIndex(i)
                        break
                self.legend_font_size_spin.setValue(config.get("legend_font_size", 10))
                self.legend_bg_color_button.set_color(config.get("legend_bg_color", "#ffffff"))
                self.legend_show_frame_check.setChecked(config.get("legend_show_frame", True))
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
        size = self.chart_size_combo.currentData()
        chart.config["width_cm"] = size[0] if size else None
        chart.config["height_cm"] = size[1] if size else None
        chart.config["dpi"] = self.chart_dpi_combo.currentData()
        chart.config["x_label"] = self.x_label_edit.text()
        chart.config["y_label"] = self.y_label_edit.text()
        chart.config["y2_label"] = self.y2_label_edit.text()
        chart.config["show_grid_x"] = self.x_grid_check.isChecked()
        chart.config["show_grid_y"] = self.y_grid_check.isChecked()
        chart.config["x_font_size"] = self.x_font_size_spin.value()
        chart.config["y_font_size"] = self.y_font_size_spin.value()
        if self.x_scale_combo.currentData():
            chart.config["x_scale"] = self.x_scale_combo.currentData().value
        if self.y_scale_combo.currentData():
            chart.config["y_scale"] = self.y_scale_combo.currentData().value
        chart.config["x_auto_limits"] = self.x_auto_limits_check.isChecked()
        chart.config["x_min"] = self.x_min_spin.value()
        chart.config["x_max"] = self.x_max_spin.value()
        chart.config["y_auto_limits"] = self.y_auto_limits_check.isChecked()
        chart.config["y_min"] = self.y_min_spin.value()
        chart.config["y_max"] = self.y_max_spin.value()
        chart.config["x_tick_mode"] = self.x_tick_mode_combo.currentData()
        chart.config["x_tick_count"] = self.x_tick_count_spin.value()
        chart.config["x_tick_step"] = self.x_tick_step_spin.value()
        chart.config["x_tick_format"] = self.x_tick_format_combo.currentData()
        chart.config["x_tick_format_custom"] = self.x_tick_format_custom_edit.text()
        chart.config["y_tick_mode"] = self.y_tick_mode_combo.currentData()
        chart.config["y_tick_count"] = self.y_tick_count_spin.value()
        chart.config["y_tick_step"] = self.y_tick_step_spin.value()
        chart.config["y_tick_format"] = self.y_tick_format_combo.currentData()
        chart.config["y_tick_format_custom"] = self.y_tick_format_custom_edit.text()
        chart.config["show_legend"] = self.legend_show_check.isChecked()
        if self.legend_position_combo.currentData():
            chart.config["legend_position"] = self.legend_position_combo.currentData().value
        chart.config["legend_font_size"] = self.legend_font_size_spin.value()
        chart.config["legend_bg_color"] = self.legend_bg_color_button.get_color()
        chart.config["legend_show_frame"] = self.legend_show_frame_check.isChecked()
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
    
