"""Top-level chart creation wizard: Type step, then Data step."""
from typing import Callable, Optional

from pandaplot.gui.core.widget_extension import PWizard
from pandaplot.gui.dialogs.chart.chart_data_page import ChartDataPage
from pandaplot.gui.dialogs.chart.chart_type_page import ChartTypePage
from pandaplot.models.state.app_context import AppContext


class ChartWizard(PWizard):
    def __init__(
        self,
        app_context: AppContext,
        parent=None,
        initial_dataset_id: Optional[str] = None,
        initial_column_ids: Optional[list[str]] = None,
        datasets: Optional[list[tuple[str, str]]] = None,
        columns_provider: Optional[Callable[[str], list[tuple[str, str]]]] = None,
    ):
        self._initial_dataset_id = initial_dataset_id
        self._initial_column_ids = initial_column_ids or []
        self._datasets = datasets or []
        self._columns_provider = columns_provider or (lambda _dataset_id: [])
        self._is_empty = False
        super().__init__(app_context=app_context, parent=parent)
        self._initialize()

    def _init_ui(self):
        self.setWindowTitle("Create Chart")

        self.type_page = ChartTypePage(app_context=self.app_context)
        self.type_page.emptyRequested.connect(self._finish_empty)
        self._type_page_id = self.addPage(self.type_page)

        self.data_page = ChartDataPage(app_context=self.app_context)
        self.data_page.emptyRequested.connect(self._finish_empty)
        self.data_page.set_datasets(self._datasets)
        self.data_page.set_dataset_columns_provider(self._columns_provider)
        self._data_page_id = self.addPage(self.data_page)

        self.currentIdChanged.connect(self._on_page_changed)
        # QWizard only assigns a currentId (and instantiates page state) once it
        # is shown or restarted; since this wizard is driven headlessly in
        # tests (and may be constructed before `show()`/`exec()`), force that
        # initialization now so `next()`/`currentId()` behave correctly even
        # before the wizard is displayed.
        self.restart()

    def _apply_theme(self):
        pass

    def _on_page_changed(self, page_id: int) -> None:
        if page_id == self._data_page_id:
            self.data_page.set_chart_type(self.type_page.selected_chart_type() or "line")
            self._apply_initial_selection()

    def _apply_initial_selection(self) -> None:
        if not self._initial_dataset_id or not self.data_page.cards:
            return
        card = self.data_page.cards[0]
        dataset_index = card.dataset_combo.findData(self._initial_dataset_id)
        if dataset_index >= 0:
            card.dataset_combo.setCurrentIndex(dataset_index)
        self.data_page._refresh_card_columns(card)
        column_ids = self._initial_column_ids
        roles = [role for role in ("x", "y") if role in card._role_combos] or ["values"]
        if len(column_ids) == 1:
            card.apply_picked_columns("y" if "y" in card._role_combos else "values", column_ids)
        else:
            for role, column_id in zip(roles, column_ids):
                card.apply_picked_columns(role, [column_id])
        self._initial_dataset_id = None
        self._initial_column_ids = []

    def _finish_empty(self) -> None:
        self._is_empty = True
        self.accept()

    def get_chart_type(self) -> str:
        return self.type_page.selected_chart_type() or "line"

    def is_empty(self) -> bool:
        return self._is_empty

    def get_series_configs(self) -> list[dict]:
        if self._is_empty:
            return []
        return self.data_page.series_configs()
