"""Style tab: chart-style card (title/subtitle font, padding, size, dpi) plus
the Line/Marker cards for whichever series/fit entry is currently selected.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.components.common.card import Card
from pandaplot.gui.components.common.color_swatch_row import ColorSwatchRow
from pandaplot.gui.components.common.line_style_icons import build_line_style_icon
from pandaplot.gui.components.common.section_header import SectionHeader
from pandaplot.gui.components.common.slider_with_spinbox import SliderWithSpinbox
from pandaplot.gui.components.common.toggle_switch import ToggleSwitch
from pandaplot.gui.components.common.value_combo_box import ValueComboBox
from pandaplot.models.chart.chart_configuration import (
    ChartType,
    LineStyleType,
    MarkerType,
)
from pandaplot.models.project.items.chart import ErrorDirection
from pandaplot.models.state.config import (
    MAX_CHART_HEIGHT_CM,
    MAX_CHART_WIDTH_CM,
    MIN_CHART_HEIGHT_CM,
    MIN_CHART_WIDTH_CM,
)
from pandaplot.services.config.config_manager import ConfigManager

# Preset swatch palette offered by the Style tab's line/marker color pickers.
STYLE_SWATCH_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


class StyleTab(QWidget):
    """Chart-style settings plus per-entry Line/Marker style controls.

    There is deliberately no independent series selector here: the chip row
    at the top mirrors the same "currently selected entry" state the Data
    tab's expand/collapse cards drive -- until Data tab migrates (Task 5),
    the panel is the source of truth for that selection and calls
    `set_selected` directly; a non-"chart" chip click is relayed back to the
    panel (which still owns `_expand_series`) via `seriesChipSelected`.

    A literal rendered line/marker preview (as sketched in the original
    design brief) is intentionally omitted here: this panel has no chart
    canvas of its own to paint into, and the live chart view already
    re-renders immediately on every change, so a second, redundant
    mini-renderer wasn't worth the complexity.
    """

    configChanged = Signal()
    # Emitted when a non-"chart" chip (an int combined series/fit index) is
    # clicked. "chart" is handled internally since the Data tab has no
    # "chart" entry of its own.
    seriesChipSelected = Signal(object)

    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self._chart = None
        self._updating_controls = False
        # (kind, obj) where kind is "chart", "series", or "fit".
        self._current_target = ("chart", None)
        # Whether `set_series_list` has ever run a real population (i.e. the
        # Data tab has emitted `seriesListChanged` at least once for an
        # actual chart). `style_series_chips` starts life pre-seeded with
        # only a "Chart" placeholder item (see below) purely so the
        # ValueComboBox constructor has a non-empty initial item list --
        # that is NOT a genuine user selection of "Chart" and must not be
        # mistaken for one on the very first real population, or the
        # newly-loaded chart's first series would wrongly appear to have
        # "Chart" as the sticky previously-selected target.
        self._series_list_initialized: bool = False
        self._chart_type = None
        # Whether the Custom size/DPI fields have already been pre-filled
        # for the currently loaded chart (reset on every load_chart_style/
        # clear_chart_style call). Prevents re-filling with defaults if the
        # user toggles back and forth between Custom and a preset.
        self._custom_size_prefilled: bool = False
        self._custom_dpi_prefilled: bool = False

        layout = QVBoxLayout(self)

        self.style_series_chips = ValueComboBox([("Chart", "chart")])
        self.style_series_chips.currentValueChanged.connect(self._on_chip_selected)
        layout.addWidget(self.style_series_chips)

        # CHART-level rendering settings -- shown instead of the Line/Marker/
        # Error Bars cards when the "Chart" chip is selected. Split into
        # bordered sections (Font Size/Padding/Size/DPI), matching the
        # Line/Marker/Error Bars pattern below, rather than one big indented
        # card -- each section's own border does the visual grouping that
        # indentation used to, freeing up width for the input fields.
        self.chart_style_cards: list[Card] = []

        def _field_row(grid: QGridLayout, row: int, label_text: str, field: QWidget, tooltip: str | None = None):
            label = QLabel(label_text)
            if tooltip:
                label.setToolTip(tooltip)
            grid.addWidget(label, row, 0)
            grid.addWidget(field, row, 1)

        def _make_bold_italic_checks() -> tuple[QCheckBox, QCheckBox]:
            bold_check = QCheckBox("Bold")
            bold_check.setStyleSheet("QCheckBox { font-weight: bold; }")
            italic_check = QCheckBox("Italic")
            italic_check.setStyleSheet("QCheckBox { font-style: italic; }")
            return bold_check, italic_check

        def _bold_italic_widget(bold_check: QCheckBox, italic_check: QCheckBox) -> QWidget:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(bold_check)
            row.addWidget(italic_check)
            row.addStretch(1)
            widget = QWidget()
            widget.setLayout(row)
            return widget

        # -- Font Size card --
        self.font_size_card = Card()
        self.chart_style_cards.append(self.font_size_card)
        font_size_layout = QGridLayout(self.font_size_card)
        font_size_layout.addWidget(SectionHeader("Font Size"), 0, 0, 1, 2)

        self.title_font_size_spin = QSpinBox()
        self.title_font_size_spin.setRange(8, 32)
        self.title_font_size_spin.setValue(14)
        _field_row(font_size_layout, 1, "Title", self.title_font_size_spin)
        self.title_bold_check, self.title_italic_check = _make_bold_italic_checks()
        self.title_bold_check.setChecked(True)
        font_size_layout.addWidget(
            _bold_italic_widget(self.title_bold_check, self.title_italic_check), 2, 1,
        )

        self.subtitle_font_size_spin = QSpinBox()
        self.subtitle_font_size_spin.setRange(8, 32)
        self.subtitle_font_size_spin.setValue(12)
        _field_row(font_size_layout, 3, "Subtitle", self.subtitle_font_size_spin)
        self.subtitle_bold_check, self.subtitle_italic_check = _make_bold_italic_checks()
        font_size_layout.addWidget(
            _bold_italic_widget(self.subtitle_bold_check, self.subtitle_italic_check), 4, 1,
        )

        layout.addWidget(self.font_size_card)

        # -- Padding card --
        self.padding_card = Card()
        self.chart_style_cards.append(self.padding_card)
        padding_layout = QGridLayout(self.padding_card)
        padding_layout.addWidget(SectionHeader("Padding"), 0, 0, 1, 2)

        self.chart_padding_spin = QDoubleSpinBox()
        self.chart_padding_spin.setRange(0.0, 10.0)
        self.chart_padding_spin.setSingleStep(0.5)
        self.chart_padding_spin.setValue(2.0)
        _field_row(padding_layout, 1, "Figure", self.chart_padding_spin)

        self.chart_padding_w_spin = QDoubleSpinBox()
        self.chart_padding_w_spin.setRange(0.0, 10.0)
        self.chart_padding_w_spin.setSingleStep(0.5)
        self.chart_padding_w_spin.setValue(2.0)
        _field_row(padding_layout, 2, "Width", self.chart_padding_w_spin)

        self.chart_padding_h_spin = QDoubleSpinBox()
        self.chart_padding_h_spin.setRange(0.0, 10.0)
        self.chart_padding_h_spin.setSingleStep(0.5)
        self.chart_padding_h_spin.setValue(2.0)
        _field_row(padding_layout, 3, "Height", self.chart_padding_h_spin)

        self.main_title_padding_spin = QDoubleSpinBox()
        self.main_title_padding_spin.setRange(0.0, 100.0)
        self.main_title_padding_spin.setSingleStep(1.0)
        self.main_title_padding_spin.setValue(10.0)
        _field_row(
            padding_layout, 4, "Title", self.main_title_padding_spin,
            tooltip="Gap between the top edge of the figure and the main title",
        )

        self.title_padding_spin = QDoubleSpinBox()
        self.title_padding_spin.setRange(0.0, 50.0)
        self.title_padding_spin.setSingleStep(1.0)
        self.title_padding_spin.setValue(6.0)
        _field_row(
            padding_layout, 5, "Subtitle", self.title_padding_spin,
            tooltip="Gap between the plot area and the subtitle text",
        )

        self.top_margin_spin = QDoubleSpinBox()
        self.top_margin_spin.setRange(0.5, 1.0)
        self.top_margin_spin.setSingleStep(0.01)
        self.top_margin_spin.setDecimals(2)
        self.top_margin_spin.setValue(1.0)
        _field_row(
            padding_layout, 6, "Top margin", self.top_margin_spin,
            tooltip=(
                "Fraction of the figure height reserved above the plot "
                "(1.0 = no reservation, let it auto-size). Unlike the "
                "Title/Subtitle padding above, this is a fixed reservation "
                "independent of whether a title/subtitle is present -- "
                "lower it manually to reclaim space when you remove one."
            ),
        )

        layout.addWidget(self.padding_card)

        # -- Size card --
        self.size_card = Card()
        self.chart_style_cards.append(self.size_card)
        size_layout = QGridLayout(self.size_card)
        size_layout.addWidget(SectionHeader("Size"), 0, 0, 1, 2)

        self.chart_size_combo = QComboBox()
        self.chart_size_combo.addItem("15 × 8 cm", (15.0, 8.0))
        self.chart_size_combo.addItem("20 × 15 cm", (20.0, 15.0))
        self.chart_size_combo.addItem("Custom", "custom")
        self.chart_size_combo.addItem("Use app default", None)
        _field_row(size_layout, 1, "Size", self.chart_size_combo)

        self.custom_size_row = QWidget()
        custom_size_layout = QGridLayout(self.custom_size_row)
        custom_size_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_width_spin = QDoubleSpinBox()
        self.chart_width_spin.setRange(MIN_CHART_WIDTH_CM, MAX_CHART_WIDTH_CM)
        self.chart_width_spin.setSuffix(" cm")
        _field_row(custom_size_layout, 0, "Width", self.chart_width_spin)
        self.chart_height_spin = QDoubleSpinBox()
        self.chart_height_spin.setRange(MIN_CHART_HEIGHT_CM, MAX_CHART_HEIGHT_CM)
        self.chart_height_spin.setSuffix(" cm")
        _field_row(custom_size_layout, 1, "Height", self.chart_height_spin)
        size_layout.addWidget(self.custom_size_row, 2, 0, 1, 2)
        self.custom_size_row.setVisible(False)

        hint = QLabel("Size affects export & default fonts")
        hint.setStyleSheet("font-size: 10.5px;")
        size_layout.addWidget(hint, 3, 0, 1, 2)

        layout.addWidget(self.size_card)

        # -- DPI card --
        self.dpi_card = Card()
        self.chart_style_cards.append(self.dpi_card)
        dpi_layout = QGridLayout(self.dpi_card)
        dpi_layout.addWidget(SectionHeader("DPI"), 0, 0, 1, 2)

        self.chart_dpi_combo = QComboBox()
        self.chart_dpi_combo.addItem("100 dpi", 100)
        self.chart_dpi_combo.addItem("150 dpi", 150)
        self.chart_dpi_combo.addItem("300 dpi", 300)
        self.chart_dpi_combo.addItem("Custom", "custom")
        self.chart_dpi_combo.addItem("Use app default", None)
        _field_row(dpi_layout, 1, "DPI", self.chart_dpi_combo)

        self.custom_dpi_row = QWidget()
        custom_dpi_layout = QGridLayout(self.custom_dpi_row)
        custom_dpi_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_dpi_spin = QSpinBox()
        self.chart_dpi_spin.setRange(50, 600)
        _field_row(custom_dpi_layout, 0, "DPI", self.chart_dpi_spin)
        dpi_layout.addWidget(self.custom_dpi_row, 2, 0, 1, 2)
        self.custom_dpi_row.setVisible(False)

        layout.addWidget(self.dpi_card)

        # -- Background card --
        self.background_card = Card()
        self.chart_style_cards.append(self.background_card)
        bg_layout = QGridLayout(self.background_card)
        bg_layout.addWidget(SectionHeader("Background"), 0, 0, 1, 4)

        bg_layout.addWidget(QLabel("Figure:"), 1, 0)
        self.figure_bg_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        bg_layout.addWidget(self.figure_bg_color_row, 1, 1)
        bg_layout.addWidget(QLabel("Transparent:"), 1, 2)
        self.figure_bg_transparent_toggle = ToggleSwitch()
        bg_layout.addWidget(self.figure_bg_transparent_toggle, 1, 3)

        bg_layout.addWidget(QLabel("Plot area:"), 2, 0)
        self.axes_bg_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        bg_layout.addWidget(self.axes_bg_color_row, 2, 1)
        bg_layout.addWidget(QLabel("Transparent:"), 2, 2)
        self.axes_bg_transparent_toggle = ToggleSwitch()
        bg_layout.addWidget(self.axes_bg_transparent_toggle, 2, 3)

        layout.addWidget(self.background_card)

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

        # Edge width is independent of "Match line" (below) -- that only
        # controls fill/edge *color*, not the edge line's thickness -- so it
        # lives with the other always-visible marker fields, not the
        # color-picker group that Match line hides.
        self.marker_edge_width_label = QLabel("Edge width:")
        marker_layout.addWidget(self.marker_edge_width_label, 3, 0)
        self.marker_edge_width_slider = SliderWithSpinbox(minimum=0.0, maximum=5.0, decimals=1)
        marker_layout.addWidget(self.marker_edge_width_slider, 3, 1)

        self.marker_color_label = QLabel("Color:")
        marker_layout.addWidget(self.marker_color_label, 4, 0)
        self.marker_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        marker_layout.addWidget(self.marker_color_row, 4, 1)

        marker_layout.addWidget(QLabel("Match line:"), 5, 0)
        self.marker_match_line_toggle = ToggleSwitch(checked=True)
        marker_layout.addWidget(self.marker_match_line_toggle, 5, 1)

        self.marker_edge_color_label = QLabel("Edge color:")
        marker_layout.addWidget(self.marker_edge_color_label, 6, 0)
        self.marker_edge_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        marker_layout.addWidget(self.marker_edge_color_row, 6, 1)

        layout.addWidget(marker_card)

        # ERROR BARS group -- which columns feed the error bars is configured
        # on the Data tab (including the Asymmetric Error Bars checkbox);
        # this group only controls how they render.
        self.error_bars_card = Card()
        error_bars_card = self.error_bars_card
        error_layout = QGridLayout(error_bars_card)
        error_layout.addWidget(SectionHeader("Error Bars"), 0, 0, 1, 2)

        error_layout.addWidget(QLabel("Direction:"), 1, 0)
        self.error_direction_control = ValueComboBox(
            [
                ("Both", ErrorDirection.BOTH),
                ("Above (+)", ErrorDirection.PLUS),
                ("Below (-)", ErrorDirection.MINUS),
            ]
        )
        error_layout.addWidget(self.error_direction_control, 1, 1)

        self.error_color_label = QLabel("Color:")
        error_layout.addWidget(self.error_color_label, 2, 0)
        self.error_color_row = ColorSwatchRow(STYLE_SWATCH_PALETTE)
        error_layout.addWidget(self.error_color_row, 2, 1)

        error_layout.addWidget(QLabel("Match line:"), 3, 0)
        self.error_match_line_toggle = ToggleSwitch(checked=True)
        error_layout.addWidget(self.error_match_line_toggle, 3, 1)

        error_layout.addWidget(QLabel("Cap Size:"), 4, 0)
        self.error_cap_size_slider = SliderWithSpinbox(minimum=0.0, maximum=20.0, decimals=1)
        error_layout.addWidget(self.error_cap_size_slider, 4, 1)

        layout.addWidget(error_bars_card)

        layout.addStretch()
        for card in self.chart_style_cards:
            card.setVisible(False)

        # Series/fit style field connections.
        self.line_color_row.colorChanged.connect(self._on_field_changed)
        self.line_style_control.currentValueChanged.connect(self._on_field_changed)
        self.line_width_slider.valueChanged.connect(self._on_field_changed)
        self.line_opacity_slider.valueChanged.connect(self._on_field_changed)
        self.markers_enabled_toggle.toggled.connect(self._on_markers_enabled_toggled)
        self.marker_shape_control.currentValueChanged.connect(self._on_field_changed)
        self.marker_size_slider.valueChanged.connect(self._on_field_changed)
        self.marker_color_row.colorChanged.connect(self._on_field_changed)
        self.marker_match_line_toggle.toggled.connect(self._on_marker_match_line_toggled)
        self.marker_edge_color_row.colorChanged.connect(self._on_field_changed)
        self.marker_edge_width_slider.valueChanged.connect(self._on_field_changed)
        self.error_direction_control.currentValueChanged.connect(self._on_field_changed)
        self.error_color_row.colorChanged.connect(self._on_field_changed)
        self.error_match_line_toggle.toggled.connect(self._on_error_match_line_toggled)
        self.error_cap_size_slider.valueChanged.connect(self._on_field_changed)

        # chart_style_card field connections.
        self.title_font_size_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.subtitle_font_size_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.chart_padding_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.chart_padding_w_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.chart_padding_h_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.title_padding_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.main_title_padding_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.top_margin_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.title_bold_check.toggled.connect(self._on_chart_style_field_changed)
        self.title_italic_check.toggled.connect(self._on_chart_style_field_changed)
        self.subtitle_bold_check.toggled.connect(self._on_chart_style_field_changed)
        self.subtitle_italic_check.toggled.connect(self._on_chart_style_field_changed)
        self.chart_size_combo.currentIndexChanged.connect(self._on_chart_size_combo_changed)
        self.chart_dpi_combo.currentIndexChanged.connect(self._on_chart_dpi_combo_changed)
        self.chart_width_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.chart_height_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.chart_dpi_spin.valueChanged.connect(self._on_chart_style_field_changed)
        self.figure_bg_color_row.colorChanged.connect(self._on_chart_style_field_changed)
        self.figure_bg_transparent_toggle.toggled.connect(self._on_bg_transparent_toggled)
        self.axes_bg_color_row.colorChanged.connect(self._on_chart_style_field_changed)
        self.axes_bg_transparent_toggle.toggled.connect(self._on_bg_transparent_toggled)

    # -- Chip selection / target routing -----------------------------------

    def _on_chip_selected(self, value):
        if value == "chart":
            self._current_target = ("chart", None)
            self._update_target_cards_visibility()
        elif value is not None:
            # The panel (until Task 5) or DataTab (after Task 5) is the
            # source of truth for series/fit selection -- this tab does not
            # self-select a series; it only reacts to set_selected(). `None`
            # is the transient value QComboBox reports mid-`clear()` (no
            # current item yet) and isn't a real selection to relay.
            self.seriesChipSelected.emit(value)

    def _update_target_cards_visibility(self):
        """Show the Chart card XOR the Line/Marker cards, matching whichever
        Style-tab chip is currently selected.

        The Line card is additionally hidden for Scatter charts: a scatter
        plot draws independent markers with no connecting line (unlike
        Line's ordered, connected points), so line color/style/width/opacity
        have nothing to apply to there.
        """
        kind, _obj = self._current_target
        is_chart = kind == "chart"
        for card in self.chart_style_cards:
            card.setVisible(is_chart)
        is_scatter = self._chart_type == ChartType.SCATTER
        self.line_card.setVisible(not is_chart and not is_scatter)
        self.marker_card.setVisible(not is_chart)
        # Fit data has no error-bar fields (DataSeries-only), so the Error
        # Bars card only applies to a selected series.
        self.error_bars_card.setVisible(kind == "series")

    def set_chart_type(self, chart_type):
        self._chart_type = chart_type
        self._update_target_cards_visibility()

    def set_series_list(self, data_series, fit_data, selected_index: int = 0):
        """Sync `style_series_chips` with the same series+fit list the Data
        tab's cards are built from, keeping its selection in lockstep with
        `selected_index` (the Data tab's own combined series/fit index,
        `DataTab.selected_index`) -- unless "Chart" is the currently selected
        target, which is independent of the series/fit list and must survive
        a refresh.

        Values are the combined index (int) for series/fit, or the "chart"
        sentinel, so selecting an entry can drive `set_selected` directly.

        `DataTab.seriesListChanged` itself is a plain `(data_series,
        fit_data)` two-arg signal (this tab has no direct reference to
        DataTab), so the panel's connection wraps it to also pass
        `self.data_tab.selected_index` as `selected_index` here -- this tab
        does not otherwise track that index itself (unlike the pre-Task-5
        panel's single `_expanded_series_index` shared by both concerns).

        The "was Chart explicitly selected" check is intentionally based on
        `style_series_chips.currentValue()` (this widget's own previous
        state), not `self._current_target`: `_current_target` gets
        reflexively reassigned to the currently-expanded series/fit on every
        Data-tab card rebuild (via `seriesSelected`, emitted regardless of
        whether the user actually changed anything, e.g. a purely-visual
        accordion toggle or a live theme refresh) and so cannot reliably
        answer "did the user deliberately choose Chart" by the time this
        runs. The chip widget's own value is untouched by any of that -- it
        only ever changes via a direct chip click (`_on_chip_selected`) or
        this method's own prior conclusion -- so it survives those
        reflexive reassignments correctly.
        """
        previous_value = self.style_series_chips.currentValue()
        chip_items = [("Chart", "chart")]
        for index, series in enumerate(data_series):
            label = series.label or f"{series.dataset_id}:{series.y_column}"
            chip_items.append((label, index))
        total_series = len(data_series)
        for fit_offset, fit in enumerate(fit_data):
            index = total_series + fit_offset
            chip_items.append((f"\U0001f527 {fit.label}", index))

        self.style_series_chips.blockSignals(True)
        self.style_series_chips.clear()
        for label, value in chip_items:
            self.style_series_chips.addItem(label, value)
        self.style_series_chips.blockSignals(False)

        # Before any real population has happened, `previous_value` is just
        # the ValueComboBox constructor's placeholder ("chart") -- not a
        # genuine prior user selection -- so it must not be treated as one.
        # `_series_list_initialized` only latches True once this has run for
        # an actual chart with at least one series/fit entry (a call with
        # both empty -- e.g. a theme refresh before any chart is loaded, or a
        # chart with zero series -- has nothing real to remember a selection
        # from, so it must not count as "initialized" either, or it would
        # make the *next* call's placeholder "chart" look like a genuine
        # prior selection).
        if self._series_list_initialized and previous_value == "chart":
            self.style_series_chips.setCurrentValue("chart")
        else:
            self.style_series_chips.setCurrentValue(selected_index)
        if data_series or fit_data:
            self._series_list_initialized = True

        final_value = self.style_series_chips.currentValue()
        if final_value == "chart":
            self._current_target = ("chart", None)
            self._update_target_cards_visibility()
        elif final_value < len(data_series):
            self.set_selected("series", data_series[final_value])
        else:
            self.set_selected("fit", fit_data[final_value - len(data_series)])

    def set_selected(self, kind: str, obj):
        self._current_target = (kind, obj)
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            if kind == "series":
                self.load_series_style(obj)
            elif kind == "fit":
                self.load_fit_style(obj)
        finally:
            self._updating_controls = previous_guard
        self._update_target_cards_visibility()

    # -- Marker enable/match-line toggles ------------------------------------

    def _on_markers_enabled_toggled(self, _checked: bool):
        """Handle the Markers section's on/off toggle."""
        self._update_marker_controls_enabled()
        self._on_field_changed()

    def _on_marker_match_line_toggled(self, _checked: bool):
        """Handle the 'Match line' toggle for marker color."""
        self._update_marker_controls_enabled()
        self._on_field_changed()

    def _update_marker_controls_enabled(self):
        """Enable/disable marker sub-controls based on the enable toggle, and
        show/hide the fill/edge color pickers based on the match-line toggle
        (pure UI convenience; see apply_series_style_to for how this maps
        onto the persisted `marker_style`/`marker_color`/`marker_edge_color`).

        "Match line" hides only the color pickers (not just disables them):
        once matching, there's nothing for the user to set -- both colors
        track `series.color` until unchecked. Edge width is a separate
        concern (line thickness, not color) and stays visible/enabled
        whenever markers are on, regardless of the match-line state.
        """
        markers_enabled = self.markers_enabled_toggle.isChecked()
        self.marker_shape_control.setEnabled(markers_enabled)
        self.marker_size_slider.setEnabled(markers_enabled)
        self.marker_match_line_toggle.setEnabled(markers_enabled)
        self.marker_edge_width_label.setVisible(markers_enabled)
        self.marker_edge_width_slider.setVisible(markers_enabled)

        show_colors = markers_enabled and not self.marker_match_line_toggle.isChecked()
        for widget in (
            self.marker_color_label, self.marker_color_row,
            self.marker_edge_color_label, self.marker_edge_color_row,
        ):
            widget.setVisible(show_colors)

    # -- Error-bar match-line toggle ------------------------------------

    def _on_error_match_line_toggled(self, _checked: bool):
        """Handle the Error Bars 'Match line' toggle."""
        self._update_error_controls_visibility()
        self._on_field_changed()

    def _update_error_controls_visibility(self):
        """Hide the error-bar color picker while it matches the line color
        (see _update_marker_controls_enabled for the same convention)."""
        show_color = not self.error_match_line_toggle.isChecked()
        self.error_color_label.setVisible(show_color)
        self.error_color_row.setVisible(show_color)

    # -- Background transparent toggles ----------------------------------

    def _on_bg_transparent_toggled(self, _checked: bool):
        """Grey out the paired color swatch while its 'Transparent' toggle
        is on; the swatch keeps its last color underneath so re-enabling
        restores it (mirrors _update_marker_controls_enabled's convention)."""
        self.figure_bg_color_row.setEnabled(not self.figure_bg_transparent_toggle.isChecked())
        self.axes_bg_color_row.setEnabled(not self.axes_bg_transparent_toggle.isChecked())
        self._on_chart_style_field_changed()

    # -- Series/fit style: load / apply --------------------------------------

    def _on_field_changed(self):
        if self._updating_controls:
            return
        kind, obj = self._current_target
        if kind == "series":
            self.apply_series_style_to(obj)
        elif kind == "fit":
            self.apply_fit_style_to(obj)
        else:
            return
        self.configChanged.emit()

    def apply_series_style_to(self, series):
        series.color = self.line_color_row.currentColor()
        series.line_style = self.line_style_control.currentValue().value
        series.line_width = self.line_width_slider.value()
        series.alpha = self.line_opacity_slider.value()

        # "Markers enabled" isn't a separate persisted flag: it maps onto
        # the existing MarkerType.NONE member. "Match line" reuses the
        # existing "" == inherit-series.color convention for both
        # marker_color and marker_edge_color (rendering already falls back
        # to series.color for either field when empty -- see chart_editor.py).
        if self.markers_enabled_toggle.isChecked():
            series.marker_style = self.marker_shape_control.currentValue().value
            series.marker_size = self.marker_size_slider.value()
            match_line = self.marker_match_line_toggle.isChecked()
            series.marker_color = "" if match_line else self.marker_color_row.currentColor()
            series.marker_edge_color = "" if match_line else self.marker_edge_color_row.currentColor()
            series.marker_edge_width = self.marker_edge_width_slider.value()
        else:
            series.marker_style = MarkerType.NONE.value

        series.error_direction = self.error_direction_control.currentValue()
        series.error_color = (
            "" if self.error_match_line_toggle.isChecked()
            else self.error_color_row.currentColor()
        )
        series.error_cap_size = self.error_cap_size_slider.value()

    def apply_fit_style_to(self, fit):
        fit.color = self.line_color_row.currentColor()
        fit.line_style = self.line_style_control.currentValue().value
        fit.line_width = self.line_width_slider.value()
        # Note: fit data doesn't use marker_size or marker colors.

    def load_series_style(self, series):
        """Populate the Line/Marker cards from a data series' style fields."""
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self.line_color_row.setCurrentColor(series.color)
            self.line_width_slider.setValue(series.line_width)
            self.line_opacity_slider.setValue(series.alpha)
            try:
                self.line_style_control.setCurrentValue(LineStyleType(series.line_style))
            except ValueError:
                self.line_style_control.setCurrentValue(LineStyleType.SOLID)

            # "Markers enabled" isn't a separate persisted flag: it's implied
            # by marker_style != MarkerType.NONE. If markers are off, the
            # shape control keeps showing the last remembered shape
            # (defaulting to circle) rather than "none", since "none" isn't
            # offered as a selectable shape here.
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

            # marker_color == "" is the existing "match line color"
            # convention, now shared by marker_edge_color too.
            self.marker_color_row.setCurrentColor(series.marker_color or series.color)
            self.marker_match_line_toggle.blockSignals(True)
            self.marker_match_line_toggle.setChecked(series.marker_color == "")
            self.marker_match_line_toggle.blockSignals(False)
            self.marker_edge_color_row.setCurrentColor(series.marker_edge_color or series.color)
            self.marker_edge_width_slider.setValue(series.marker_edge_width)

            self._update_marker_controls_enabled()

            try:
                self.error_direction_control.setCurrentValue(ErrorDirection(series.error_direction))
            except ValueError:
                self.error_direction_control.setCurrentValue(ErrorDirection.BOTH)
            self.error_color_row.setCurrentColor(series.error_color or series.color)
            self.error_match_line_toggle.blockSignals(True)
            self.error_match_line_toggle.setChecked(series.error_color == "")
            self.error_match_line_toggle.blockSignals(False)
            self._update_error_controls_visibility()
            self.error_cap_size_slider.setValue(series.error_cap_size)
        finally:
            self._updating_controls = previous_guard

    def load_fit_style(self, fit):
        """Populate the Line/Marker cards from a fit-data entry's style
        fields. Fit data has no marker/opacity concept, so markers are
        forced off and locked."""
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
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

    # -- Chart-style card: load / apply / clear ------------------------------

    def load_chart_style(self, chart):
        self._chart = chart
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self.title_font_size_spin.setValue(chart.config.get("title_font_size", 14))
            self.subtitle_font_size_spin.setValue(chart.config.get("subtitle_font_size", 12))
            self.chart_padding_spin.setValue(chart.config.get("chart_padding", 2.0))
            self.chart_padding_w_spin.setValue(chart.config.get("chart_padding_w", 2.0))
            self.chart_padding_h_spin.setValue(chart.config.get("chart_padding_h", 2.0))
            self.title_padding_spin.setValue(chart.config.get("title_padding", 6.0))
            self.main_title_padding_spin.setValue(chart.config.get("main_title_padding", 10.0))
            self.top_margin_spin.setValue(chart.config.get("top_margin", 1.0))
            self.title_bold_check.setChecked(chart.config.get("title_bold", True))
            self.title_italic_check.setChecked(chart.config.get("title_italic", False))
            self.subtitle_bold_check.setChecked(chart.config.get("subtitle_bold", False))
            self.subtitle_italic_check.setChecked(chart.config.get("subtitle_italic", False))

            fig_bg = chart.style.get("figure_background_color", "#ffffff")
            self.figure_bg_transparent_toggle.setChecked(fig_bg is None)
            self.figure_bg_color_row.setCurrentColor(fig_bg or "#ffffff")
            self.figure_bg_color_row.setEnabled(fig_bg is not None)

            axes_bg = chart.style.get("axes_background_color", "#ffffff")
            self.axes_bg_transparent_toggle.setChecked(axes_bg is None)
            self.axes_bg_color_row.setCurrentColor(axes_bg or "#ffffff")
            self.axes_bg_color_row.setEnabled(axes_bg is not None)

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
        finally:
            self._updating_controls = previous_guard

    def apply_chart_style_to(self, chart):
        chart.config["title_font_size"] = self.title_font_size_spin.value()
        chart.config["subtitle_font_size"] = self.subtitle_font_size_spin.value()
        chart.config["chart_padding"] = self.chart_padding_spin.value()
        chart.config["chart_padding_w"] = self.chart_padding_w_spin.value()
        chart.config["chart_padding_h"] = self.chart_padding_h_spin.value()
        chart.config["title_padding"] = self.title_padding_spin.value()
        chart.config["main_title_padding"] = self.main_title_padding_spin.value()
        chart.config["top_margin"] = self.top_margin_spin.value()
        chart.config["title_bold"] = self.title_bold_check.isChecked()
        chart.config["title_italic"] = self.title_italic_check.isChecked()
        chart.config["subtitle_bold"] = self.subtitle_bold_check.isChecked()
        chart.config["subtitle_italic"] = self.subtitle_italic_check.isChecked()
        chart.style["figure_background_color"] = (
            None if self.figure_bg_transparent_toggle.isChecked()
            else self.figure_bg_color_row.currentColor()
        )
        chart.style["axes_background_color"] = (
            None if self.axes_bg_transparent_toggle.isChecked()
            else self.axes_bg_color_row.currentColor()
        )
        chart.config["width_cm"], chart.config["height_cm"] = self._size_from_controls()
        chart.config["dpi"] = self._dpi_from_controls()

    def clear_chart_style(self):
        self._chart = None
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self.title_font_size_spin.setValue(14)
            self.subtitle_font_size_spin.setValue(12)
            self.chart_padding_spin.setValue(2.0)
            self.chart_padding_w_spin.setValue(2.0)
            self.chart_padding_h_spin.setValue(2.0)
            self.title_padding_spin.setValue(6.0)
            self.main_title_padding_spin.setValue(10.0)
            self.top_margin_spin.setValue(1.0)
            self.title_bold_check.setChecked(True)
            self.title_italic_check.setChecked(False)
            self.subtitle_bold_check.setChecked(False)
            self.subtitle_italic_check.setChecked(False)
            self.figure_bg_transparent_toggle.setChecked(False)
            self.figure_bg_color_row.setCurrentColor("#ffffff")
            self.figure_bg_color_row.setEnabled(True)
            self.axes_bg_transparent_toggle.setChecked(False)
            self.axes_bg_color_row.setCurrentColor("#ffffff")
            self.axes_bg_color_row.setEnabled(True)
            self.chart_size_combo.setCurrentIndex(self.chart_size_combo.count() - 1)
            self.chart_width_spin.setValue(20.0)
            self.chart_height_spin.setValue(15.0)
            self._custom_size_prefilled = False
            self.chart_dpi_combo.setCurrentIndex(self.chart_dpi_combo.count() - 1)
            self.chart_dpi_spin.setValue(100)
            self._custom_dpi_prefilled = False
        finally:
            self._updating_controls = previous_guard

    # -- Chart size/dpi combo helpers -----------------------------------------

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
        if not self._chart:
            return default_width, default_height, default_dpi
        # Deferred import: chart_editor.py pulls in matplotlib, which must
        # stay lazy at app startup (see tests/test_startup_imports.py).
        from pandaplot.gui.components.tabs.chart.chart_editor import resolve_chart_size

        return resolve_chart_size(
            self._chart.config.get("width_cm"),
            self._chart.config.get("height_cm"),
            self._chart.config.get("dpi"),
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
        self._on_chart_style_field_changed()

    def _on_chart_dpi_combo_changed(self):
        """Show/hide the Custom DPI row and pre-fill it the first time the
        user manually selects Custom for this loaded chart."""
        is_custom = self.chart_dpi_combo.currentData() == "custom"
        self.custom_dpi_row.setVisible(is_custom)
        if is_custom and not self._updating_controls and not self._custom_dpi_prefilled:
            _, _, dpi = self._effective_chart_size_dpi()
            self.chart_dpi_spin.setValue(dpi)
            self._custom_dpi_prefilled = True
        self._on_chart_style_field_changed()

    def _on_chart_style_field_changed(self):
        if self._chart is None or self._updating_controls:
            return
        config = self._chart.config
        config["title_font_size"] = self.title_font_size_spin.value()
        config["subtitle_font_size"] = self.subtitle_font_size_spin.value()
        config["chart_padding"] = self.chart_padding_spin.value()
        config["chart_padding_w"] = self.chart_padding_w_spin.value()
        config["chart_padding_h"] = self.chart_padding_h_spin.value()
        config["title_padding"] = self.title_padding_spin.value()
        config["main_title_padding"] = self.main_title_padding_spin.value()
        config["top_margin"] = self.top_margin_spin.value()
        config["title_bold"] = self.title_bold_check.isChecked()
        config["title_italic"] = self.title_italic_check.isChecked()
        config["subtitle_bold"] = self.subtitle_bold_check.isChecked()
        config["subtitle_italic"] = self.subtitle_italic_check.isChecked()
        self._chart.style["figure_background_color"] = (
            None if self.figure_bg_transparent_toggle.isChecked()
            else self.figure_bg_color_row.currentColor()
        )
        self._chart.style["axes_background_color"] = (
            None if self.axes_bg_transparent_toggle.isChecked()
            else self.axes_bg_color_row.currentColor()
        )
        config["width_cm"], config["height_cm"] = self._size_from_controls()
        config["dpi"] = self._dpi_from_controls()
        self.configChanged.emit()

    # -- Theme ----------------------------------------------------------------

    def apply_theme(self, tokens: dict):
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
        self.marker_edge_color_row.set_tokens(tokens)
        self.marker_edge_width_slider.set_tokens(tokens)
        self.error_direction_control.set_tokens(tokens)
        self.error_color_row.set_tokens(tokens)
        self.error_match_line_toggle.set_tokens(tokens)
        self.error_cap_size_slider.set_tokens(tokens)
        self.figure_bg_color_row.set_tokens(tokens)
        self.figure_bg_transparent_toggle.set_tokens(tokens)
        self.axes_bg_color_row.set_tokens(tokens)
        self.axes_bg_transparent_toggle.set_tokens(tokens)
