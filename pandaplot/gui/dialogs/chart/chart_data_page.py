"""Step 2 of the chart creation wizard: one or more series, each configured
by a SeriesConfigCard, plus a 'Create empty plot' escape hatch.
"""
from typing import Callable, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from pandaplot.gui.core.widget_extension import PWizardPage
from pandaplot.gui.dialogs.chart.chart_role_spec import get_chart_role_spec
from pandaplot.gui.dialogs.chart.dataset_column_picker import DatasetColumnPicker
from pandaplot.gui.dialogs.chart.series_config_card import SeriesConfigCard
from pandaplot.models.state.app_context import AppContext


class ChartDataPage(PWizardPage):
    emptyRequested = Signal()

    def __init__(self, app_context: AppContext, parent: Optional[QWidget] = None):
        super().__init__(app_context=app_context, parent=parent)
        self.cards: list[SeriesConfigCard] = []
        self._chart_type: str = "line"
        self._datasets: list[tuple[str, str]] = []
        self._columns_provider: Optional[Callable[[str], list[tuple[str, str]]]] = None
        self._picker = DatasetColumnPicker(app_context)
        self._initialize()

    def _init_ui(self):
        self.setTitle("Configure your data")
        self._layout = QVBoxLayout(self)

        self.cards_container = QVBoxLayout()
        self._layout.addLayout(self.cards_container)

        self.add_series_button = QPushButton("+ Add series")
        self.add_series_button.clicked.connect(self._add_card)
        self._layout.addWidget(self.add_series_button)

        self.empty_button = QPushButton("Create empty plot")
        self.empty_button.clicked.connect(self.emptyRequested.emit)
        self._layout.addWidget(self.empty_button)

    def _apply_theme(self):
        pass

    def set_chart_type(self, chart_type: str) -> None:
        if chart_type == self._chart_type and self.cards:
            return
        self._chart_type = chart_type
        for card in list(self.cards):
            self._remove_card(card)
        self._add_card()

    def set_datasets(self, datasets: list[tuple[str, str]]) -> None:
        self._datasets = datasets
        for card in self.cards:
            card.set_datasets(datasets)

    def set_dataset_columns_provider(self, provider: Callable[[str], list[tuple[str, str]]]) -> None:
        self._columns_provider = provider
        for card in self.cards:
            self._refresh_card_columns(card)

    def _add_card(self) -> SeriesConfigCard:
        card = SeriesConfigCard(role_spec=get_chart_role_spec(self._chart_type))
        card.set_datasets(self._datasets)
        card.removeRequested.connect(lambda c=card: self._remove_card(c))
        card.datasetChanged.connect(lambda _dataset_id, c=card: self._refresh_card_columns(c))
        card.configChanged.connect(self.completeChanged.emit)
        card.pickRequested.connect(lambda role, c=card: self._start_pick(c, role))
        self.cards_container.addWidget(card)
        self.cards.append(card)
        self._refresh_card_columns(card)
        self.completeChanged.emit()
        return card

    def _remove_card(self, card: SeriesConfigCard) -> None:
        if card not in self.cards:
            return
        self.cards.remove(card)
        self.cards_container.removeWidget(card)
        card.setParent(None)
        card.deleteLater()
        self.completeChanged.emit()

    def _refresh_card_columns(self, card: SeriesConfigCard) -> None:
        dataset_id = card.dataset_combo.currentData()
        if dataset_id and self._columns_provider is not None:
            card.set_dataset_columns(dataset_id, self._columns_provider(dataset_id))

    def _start_pick(self, card: SeriesConfigCard, role: str) -> None:
        dataset_id = card.dataset_combo.currentData()
        if not dataset_id:
            return
        self._picker.start(
            self.wizard(), dataset_id, role,
            on_done=lambda column_ids, c=card, r=role: c.apply_picked_columns(r, column_ids),
        )

    def series_configs(self) -> list[dict]:
        return [card.get_series_config() for card in self.cards]

    def isComplete(self) -> bool:
        return bool(self.cards) and all(card.is_complete() for card in self.cards)
