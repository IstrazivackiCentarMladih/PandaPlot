"""Chart properties side panel for configuring chart appearance and data."""
from typing import List, Optional, override

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
from pandaplot.gui.components.common.dirty_footer import DirtyFooter
from pandaplot.gui.components.common.section_header import SectionHeader
from pandaplot.gui.components.common.segmented_control import SegmentedControl
from pandaplot.gui.components.sidebar.chart.tabs.axes_tab import AxesTab
from pandaplot.gui.components.sidebar.chart.tabs.chart_tab import ChartTab
from pandaplot.gui.components.sidebar.chart.tabs.legend_tab import LegendTab
from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.chart.chart_configuration import ChartType
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
        # Reference to the expanded Data-tab card's Y1/Y2 badge QLabel (and
        # the design tokens it was last styled with), so a live series
        # Y-axis edit can restyle it in place. See _on_series_config_changed.
        self._expanded_card_y_axis_badge: Optional[QLabel] = None
        self._expanded_card_y_axis_badge_tokens: dict = {}
        # Which entry (data series index, then fit-data index appended after
        # all series) is currently *selected* -- drives the Style tab's
        # editing target and the live configuration form shown on the Data
        # tab. Independent of `_expanded_card_indices` below: a card can be
        # expanded (accordion open) without being selected.
        self._expanded_series_index: int = 0
        # Purely-visual accordion state: which cards show their expanded
        # detail view. The selected card is always implicitly expanded (it
        # hosts the live form) even if its index isn't in this set.
        self._expanded_card_indices: set = {0}

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
        layout.addSpacing(6)

        # Tab widget for organizing chart properties. When the tab bar
        # doesn't fit the panel's width, `resizeEvent` swaps it for
        # `tab_selector_combo` (a dropdown driving the same pages) instead of
        # letting Qt shrink/elide/scroll the tab labels.
        self._tab_titles = ["Chart", "Data", "Style", "Axes", "Legend"]
        self.tab_selector_combo = QComboBox(self)
        self.tab_selector_combo.addItems(self._tab_titles)
        self.tab_selector_combo.setVisible(False)
        self.tab_selector_combo.currentIndexChanged.connect(self._on_tab_selector_combo_changed)
        layout.addWidget(self.tab_selector_combo)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.currentChanged.connect(self._on_tab_widget_current_changed)

        # Style tab is constructed before the Chart tab (though added to the
        # tab widget after Data, below) because ChartTab.chartTypeChanged
        # needs to connect directly to self.style_tab.set_chart_type here.
        self.style_tab = StyleTab(self.app_context, self)
        self.style_tab.configChanged.connect(self._on_any_tab_config_changed)
        self.style_tab.seriesChipSelected.connect(self._expand_series)

        # Chart tab: chart identity (title, chart type, histogram bins)
        self.chart_tab = ChartTab(self)
        self.chart_tab.configChanged.connect(self._on_any_tab_config_changed)
        self.chart_tab.chartTypeChanged.connect(self.style_tab.set_chart_type)
        self.tab_widget.addTab(self.chart_tab, "Chart")

        # Axes tab: constructed before the Data tab (though added to the tab
        # widget after Style, below) because building the Data tab's series
        # cards calls `_rebuild_series_cards`, which calls
        # `self.axes_tab.refresh_axis_chips` to sync the Y2 chip.
        self.axes_tab = AxesTab(self)
        self.axes_tab.configChanged.connect(self._on_any_tab_config_changed)

        # Data tab: series list + per-series dataset/X/Y/label configuration
        data_tab = QWidget()
        data_tab_layout = QVBoxLayout(data_tab)
        self._create_series_management_section(data_tab_layout)
        data_tab_layout.addStretch(1)
        self.data_tab = data_tab
        self.tab_widget.addTab(self.data_tab, "Data")

        # Style tab (line/marker style)
        self.tab_widget.addTab(self.style_tab, "Style")

        self.tab_widget.addTab(self.axes_tab, "Axes")

        # Legend tab
        self.legend_tab = LegendTab(self)
        self.legend_tab.configChanged.connect(self._on_any_tab_config_changed)
        self.tab_widget.addTab(self.legend_tab, "Legend")

        layout.addWidget(self.tab_widget, stretch=1)

        # Footer: dirty-state indicator + Revert/Apply
        self.footer = DirtyFooter(self)
        self.footer.applyClicked.connect(self._on_apply)
        self.footer.revertClicked.connect(self._on_reset)
        layout.addWidget(self.footer)

    def _on_tab_selector_combo_changed(self, index):
        if index >= 0:
            self.tab_widget.setCurrentIndex(index)

    def _on_tab_widget_current_changed(self, index):
        if self.tab_selector_combo.currentIndex() != index:
            self.tab_selector_combo.blockSignals(True)
            self.tab_selector_combo.setCurrentIndex(index)
            self.tab_selector_combo.blockSignals(False)

    def _update_tab_bar_responsive_mode(self):
        """Switch between the native tab bar and `tab_selector_combo` based on
        available width, so tab labels never get elided/scrolled -- this only
        affects this panel's own tabs, not tab widgets elsewhere in the app."""
        tab_bar = self.tab_widget.tabBar()
        available_width = self.tab_widget.width()
        fits = tab_bar.sizeHint().width() <= available_width if available_width > 0 else True
        tab_bar.setVisible(fits)
        self.tab_selector_combo.setVisible(not fits)

    @override
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_tab_bar_responsive_mode()

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
        self.chart_tab.apply_theme(tokens)

        # Style tab: shared widgets
        self.style_tab.apply_theme(tokens)

        # Data tab: cards/SegmentedControl are rebuilt with fresh tokens
        # every time _rebuild_series_cards runs, so re-running it here is
        # the simplest way to make a live theme change reach them.
        self._series_section_header.set_tokens(tokens)
        self.series_y_axis_control.set_tokens(tokens)
        self._rebuild_series_cards()

        # Axes tab: chip row plus each axis form's Card/SegmentedControl/
        # ToggleSwitch/SectionHeader widgets.
        self.axes_tab.apply_theme(tokens)

        # Legend tab: shared widgets
        self.legend_tab.apply_theme(tokens)

    def _apply_series_button_styling(self):
        """Apply theme styling to series management buttons."""
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()
        
        # Get colors with fallbacks
        accent = palette.get("accent", "#4CAF50")
        secondary_fg = palette.get("secondary_fg", "#666666")
        card_hover = palette.get("card_hover", "#e5f3ff")
        base_fg = palette.get("base_fg", "#333333")

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
        """Select `index` as the panel's live-edited entry: it drives the
        Data tab's configuration form, the Style tab's target, and the
        selected-card border highlight. Independent of any other card's
        accordion open/closed state (`_expanded_card_indices`) -- see
        `_toggle_card_expanded` for that purely-visual toggle."""
        self._expanded_series_index = index
        self._expanded_card_indices.add(index)
        self._rebuild_series_cards()
        if not self.current_chart:
            return
        if index < len(self.current_chart.data_series):
            self.style_tab.set_selected("series", self.current_chart.data_series[index])
        else:
            self.style_tab.set_selected(
                "fit", self.current_chart.fit_data[index - len(self.current_chart.data_series)]
            )

    def _toggle_card_expanded(self, index: int):
        """Purely-visual accordion toggle: show/hide a card's read-only
        detail view, independent of which card is *selected*."""
        if index in self._expanded_card_indices:
            self._expanded_card_indices.discard(index)
        else:
            self._expanded_card_indices.add(index)
        self._rebuild_series_cards()

    def _rebuild_series_cards(self):
        """Rebuild the Data tab's card list from `self.current_chart`.

        Each entry renders as one of three variants:
        - the *selected* entry (`self._expanded_series_index`) always gets
          the full configuration card (dataset/X/Y/Y-axis/label) -- it hosts
          the one shared, live-wired form widget;
        - other entries whose index is in `self._expanded_card_indices` get
          a read-only detail row (purely visual "accordion open" state,
          independent of selection);
        - everything else gets the single-line collapsed chip row.

        Safe to call at any point: fetches fresh theme tokens, so this
        doubles as the mechanism by which cards pick up a live theme change
        (see `_apply_theme`).
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
            if hasattr(self, "style_tab"):
                self.style_tab.style_series_chips.clear()
            self.axes_tab.refresh_axis_chips(self.current_chart)
            return

        total_series = len(self.current_chart.data_series)

        for index, series in enumerate(self.current_chart.data_series):
            if index == self._expanded_series_index:
                card = self._build_expanded_series_card(index, tokens)
            elif index in self._expanded_card_indices:
                card = self._build_series_detail_row(series, index, tokens)
            else:
                card = self._build_collapsed_series_row(series, index, tokens)
            self._series_cards_layout.addWidget(card)

        for fit_offset, fit in enumerate(self.current_chart.fit_data):
            index = total_series + fit_offset
            if index == self._expanded_series_index:
                card = self._build_expanded_series_card(index, tokens)
            elif index in self._expanded_card_indices:
                card = self._build_fit_detail_row(fit, index, tokens)
            else:
                card = self._build_collapsed_fit_row(fit, index, tokens)
            self._series_cards_layout.addWidget(card)

        self._refresh_style_chips()
        self.axes_tab.refresh_axis_chips(self.current_chart)

    def _refresh_style_chips(self):
        """Sync the Style tab's dropdown with the same series+fit list the
        Data tab's cards are built from, keeping its selection in lockstep
        with `self._expanded_series_index` (the single, panel-wide
        "currently edited entry" state also driven by Data-tab card expand)
        -- unless "Chart" is the currently selected entry, which is its own
        independent target and must survive a series/fit list refresh.

        Values are the combined index (int) for series/fit, or the "chart"
        sentinel, so selecting an entry can drive `_expand_series` directly
        without needing to search for the clicked object's index.
        """
        if not hasattr(self, "style_tab"):
            # The Data tab (built first) triggers an initial
            # _rebuild_series_cards() call before the Style tab (and its
            # dropdown) exists yet. There is no chart loaded yet at that
            # point either, so there is nothing to reflect; the dropdown is
            # populated for real the next time a chart is loaded.
            return
        style_chips = self.style_tab.style_series_chips
        previous_value = style_chips.currentValue()
        chip_items = [("Chart", "chart")]
        for index, series in enumerate(self.current_chart.data_series):
            label = series.label or f"{series.dataset_id}:{series.y_column}"
            chip_items.append((label, index))
        total_series = len(self.current_chart.data_series)
        for fit_offset, fit in enumerate(self.current_chart.fit_data):
            index = total_series + fit_offset
            chip_items.append((f"\U0001f527 {fit.label}", index))

        style_chips.blockSignals(True)
        style_chips.clear()
        for label, value in chip_items:
            style_chips.addItem(label, value)
        style_chips.blockSignals(False)

        if previous_value == "chart":
            style_chips.setCurrentValue("chart")
        else:
            style_chips.setCurrentValue(self._expanded_series_index)

        # Keep the Style tab's own selection tracking (`_current_target`) in
        # lockstep with the chip value set above, since `setCurrentValue`
        # doesn't emit `currentValueChanged` (see ValueComboBox).
        final_value = style_chips.currentValue()
        if final_value == "chart":
            self.style_tab._current_target = ("chart", None)
            self.style_tab._update_target_cards_visibility()
        elif final_value < len(self.current_chart.data_series):
            self.style_tab.set_selected("series", self.current_chart.data_series[final_value])
        else:
            self.style_tab.set_selected(
                "fit", self.current_chart.fit_data[final_value - len(self.current_chart.data_series)]
            )

    def _make_swatch(self, color: str, tokens: dict) -> QFrame:
        swatch = QFrame()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(
            f"background-color: {color}; "
            f"border: 1px solid {tokens.get('border_control', '#999')}; "
            f"border-radius: {tokens.get('radius_swatch', 4)}px;"
        )
        return swatch

    def _build_trash_button(self, index: int, tokens: dict) -> QPushButton:
        """Per-row delete icon (replaces the old single bottom Remove button
        so a specific series/fit can be removed regardless of which entry
        is selected/expanded)."""
        button = QPushButton("\U0001f5d1")  # wastebasket emoji
        button.setFlat(True)
        button.setFixedWidth(24)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip("Remove")
        button.setStyleSheet(
            "QPushButton { border: none; background: transparent; "
            f"color: {tokens.get('text_muted', '#666')}; }} "
            "QPushButton:hover { color: #dc3545; }"
        )
        button.clicked.connect(lambda _checked=False, i=index: self._remove_series_at(i))
        return button

    def _build_chevron_button(self, index: int, expanded: bool) -> QPushButton:
        """Accordion toggle: purely visual expand/collapse, independent of
        selection (see `_toggle_card_expanded`)."""
        chevron = QPushButton("▾" if expanded else "▸")
        chevron.setFlat(True)
        chevron.setFixedWidth(24)
        chevron.setCursor(Qt.CursorShape.PointingHandCursor)
        chevron.clicked.connect(lambda _checked=False, i=index: self._toggle_card_expanded(i))
        return chevron

    def _install_select_on_click(self, card: QWidget, index: int):
        """Clicking anywhere on a collapsed/detail card's background selects
        it (moves the live-edited entry there), without affecting its own or
        any other card's accordion open/closed state."""
        def _handler(event, i=index):
            if event.button() == Qt.MouseButton.LeftButton:
                self._expand_series(i)
            event.accept()
        card.mousePressEvent = _handler
        card.setCursor(Qt.CursorShape.PointingHandCursor)

    def _build_collapsed_series_row(self, series, index: int, tokens: dict) -> QWidget:
        """A chip-like collapsed row: color square, name, Y-axis badge, trash, chevron."""
        card = Card()
        card.set_tokens(tokens)
        self._install_select_on_click(card, index)
        row = QHBoxLayout(card)

        row.addWidget(self._make_swatch(series.color, tokens))

        name_label = QLabel(series.label or f"{series.dataset_id}:{series.y_column}")
        name_label.setStyleSheet(f"color: {tokens.get('text_primary', '#000')};")
        row.addWidget(name_label, 1)

        row.addWidget(self._build_y_axis_badge(series.y_axis, tokens))
        row.addWidget(self._build_trash_button(index, tokens))
        row.addWidget(self._build_chevron_button(index, expanded=False))

        return card

    def _build_collapsed_fit_row(self, fit, index: int, tokens: dict) -> QWidget:
        """Collapsed row for a fit-data entry (no Y-axis picker for fits)."""
        card = Card()
        card.set_tokens(tokens)
        self._install_select_on_click(card, index)
        row = QHBoxLayout(card)

        row.addWidget(self._make_swatch(fit.color, tokens))

        name_label = QLabel(f"\U0001f527 {fit.label}")  # wrench emoji
        name_label.setStyleSheet(f"color: {tokens.get('text_primary', '#000')};")
        row.addWidget(name_label, 1)

        row.addWidget(self._build_trash_button(index, tokens))
        row.addWidget(self._build_chevron_button(index, expanded=False))

        return card

    def _build_series_detail_row(self, series, index: int, tokens: dict) -> QWidget:
        """Read-only detail view for a series card that's accordion-expanded
        but not the currently *selected* entry -- purely visual, since the
        one shared live-editable form can only live on the selected card."""
        card = Card()
        card.set_tokens(tokens)
        self._install_select_on_click(card, index)
        outer = QVBoxLayout(card)

        header = QHBoxLayout()
        header.addWidget(self._make_swatch(series.color, tokens))
        name_label = QLabel(series.label or f"{series.dataset_id}:{series.y_column}")
        name_label.setStyleSheet(f"color: {tokens.get('text_primary', '#000')};")
        header.addWidget(name_label, 1)
        header.addWidget(self._build_y_axis_badge(series.y_axis, tokens))
        header.addWidget(self._build_trash_button(index, tokens))
        header.addWidget(self._build_chevron_button(index, expanded=True))
        outer.addLayout(header)

        detail = QLabel(f"Dataset: {series.dataset_id}   X: {series.x_column}   Y: {series.y_column}")
        detail.setStyleSheet(f"color: {tokens.get('text_muted', '#666')}; font-size: 10px;")
        outer.addWidget(detail)

        return card

    def _build_fit_detail_row(self, fit, index: int, tokens: dict) -> QWidget:
        """Read-only detail view for a fit card that's accordion-expanded but
        not the currently selected entry (see `_build_series_detail_row`)."""
        card = Card()
        card.set_tokens(tokens)
        self._install_select_on_click(card, index)
        outer = QVBoxLayout(card)

        header = QHBoxLayout()
        header.addWidget(self._make_swatch(fit.color, tokens))
        name_label = QLabel(f"\U0001f527 {fit.label}")
        name_label.setStyleSheet(f"color: {tokens.get('text_primary', '#000')};")
        header.addWidget(name_label, 1)
        header.addWidget(self._build_trash_button(index, tokens))
        header.addWidget(self._build_chevron_button(index, expanded=True))
        outer.addLayout(header)

        detail = QLabel(f"Fit: {fit.fit_type}   X: {fit.source_x_column}   Y: {fit.source_y_column}")
        detail.setStyleSheet(f"color: {tokens.get('text_muted', '#666')}; font-size: 10px;")
        outer.addWidget(detail)

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
        """The expanded card for the currently *selected* entry: title + the
        persistent config form, loaded with `index`'s values (a data-series
        index, or a fit-data index appended after all series, matching the
        combined indexing used throughout this panel). Rendered with an
        accent border (via the "selected" dynamic property) to distinguish
        it from unselected cards."""
        card = Card()
        card.set_tokens(tokens)
        card.setProperty("selected", True)
        card.style().unpolish(card)
        card.style().polish(card)
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
        header.addWidget(self._build_trash_button(index, tokens))
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

    def _connect_signals(self):
        """Connect widget signals."""
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_changed)

        # Chart tab's own fields (title/subtitle/chart type/hist bins) are
        # wired internally by ChartTab; Style tab's chart_style_card and
        # Line/Marker card fields are wired internally by StyleTab.
        # Axes tab: each axis form's widgets are wired directly to shared
        # handlers in _build_axis_form_widgets, not here (the forms are
        # built dynamically per-prefix, so there are no static
        # self.x_*/self.y_*/self.y2_* attributes to hook up in one place).
        # Connect series configuration change signals
        self.x_column_combo.currentTextChanged.connect(self._on_series_config_changed)
        self.y_column_combo.currentTextChanged.connect(self._on_series_config_changed)
        self.series_y_axis_control.currentValueChanged.connect(self._on_series_config_changed)
        # Defer label persistence to editingFinished to avoid disruptive refresh while typing
        self.series_label_edit.textChanged.connect(self._on_label_typing)
        self.series_label_edit.editingFinished.connect(self._on_label_committed)

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

            # Select the newly added series
            new_index = len(self.current_chart.data_series) - 1
            self._expanded_series_index = new_index
            self._expanded_card_indices.add(new_index)
            self._rebuild_series_cards()

    def _remove_series_at(self, index: int):
        """Remove the data series or fit-data entry at the combined `index`
        (data-series indices first, then fit-data indices appended after),
        adjusting selection and accordion state for the index shift."""
        if not self.current_chart:
            return

        total_series = len(self.current_chart.data_series)
        total_items = total_series + len(self.current_chart.fit_data)
        if index < 0 or index >= total_items:
            return

        if index < total_series:
            command = RemoveSeriesCommand(
                self.app_context,
                chart_id=self.current_chart.id,
                series_index=index,
            )
        else:
            command = RemoveFitDataCommand(
                self.app_context,
                chart_id=self.current_chart.id,
                fit_index=index - total_series,
            )
        self.command_executor.execute_command(command)

        def _shift(i):
            if i > index:
                return i - 1
            if i == index:
                return None
            return i

        self._expanded_card_indices = {
            shifted for shifted in (_shift(i) for i in self._expanded_card_indices)
            if shifted is not None
        }

        remaining_items = len(self.current_chart.data_series) + len(self.current_chart.fit_data)
        shifted_selected = _shift(self._expanded_series_index)
        if shifted_selected is None:
            shifted_selected = index
        self._expanded_series_index = max(0, min(shifted_selected, max(remaining_items - 1, 0)))
        self._expanded_card_indices.add(self._expanded_series_index)
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
            self.axes_tab.refresh_axis_chips(self.current_chart)

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

    def _on_any_tab_config_changed(self):
        if not self.current_chart:
            return
        self._has_unsaved_changes = True
        self._update_status_indicator()
        self.publish_event(ChartEvents.CHART_UPDATED, {
            "chart_id": self.current_chart.id,
            "update_type": "config_updated",
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

            self.style_tab.load_series_style(series)
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

            self.style_tab.load_fit_style(fit)
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
            self.style_tab.clear_chart_style()
            self.chart_tab.clear()
            self.axes_tab.clear()
            self.legend_tab.clear()
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
                self.style_tab.load_chart_style(chart)

                # Expand the first series/fit entry and rebuild the card list
                # (this also (re)loads it into the config form controls).
                self._expanded_series_index = 0
                self._expanded_card_indices = {0}
                self._rebuild_series_cards()
                # (_rebuild_series_cards already loads series/fit 0's style
                # into the Style tab controls via _build_expanded_series_card.)

                # Load configuration
                self.chart_tab.load(chart)
                self.axes_tab.load(chart)
                self.legend_tab.load(chart)
            finally:
                self._updating_controls = previous_guard

        else:
            # Clear/default values
            self._clear_controls()
            self._expanded_series_index = 0
            self._expanded_card_indices = {0}
            self._rebuild_series_cards()
    
    def apply_to_chart(self, chart):
        """Apply current panel settings to a Chart object.
        
        Args:
            chart: Chart object to update
        """
        if not chart:
            return

        # Update basic chart properties
        self.style_tab.apply_chart_style_to(chart)
        self.chart_tab.apply_to(chart)
        self.axes_tab.apply_to(chart)
        self.legend_tab.apply_to(chart)

        # Apply style updates to the currently selected series or fit data
        current_row = self._expanded_series_index
        if current_row >= 0:
            total_series = len(chart.data_series)

            if current_row < total_series:
                # Update data series
                series = chart.data_series[current_row]

                series.y_axis = self.series_y_axis_control.currentValue()
                self.style_tab.apply_series_style_to(series)

                self.logger.debug(
                    "Applied style to data series %d: %s (color=%s, marker_color=%s)",
                    current_row, series.label, series.color, series.marker_color
                )
            else:
                # Update fit data
                fit_index = current_row - total_series
                if 0 <= fit_index < len(chart.fit_data):
                    fit = chart.fit_data[fit_index]
                    self.style_tab.apply_fit_style_to(fit)

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
                    color=self.style_tab.line_color_row.currentColor(),
                    line_width=self.style_tab.line_width_slider.value(),
                    marker_size=self.style_tab.marker_size_slider.value(),
                    label=f"{dataset_name}:{y_column}",
                    y_axis=self.series_y_axis_control.currentValue()
                )

        chart.update_modified_time()
    
