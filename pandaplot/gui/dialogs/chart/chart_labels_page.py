"""Step 3 of the chart creation wizard: title/subtitle, X/Y axis labels,
legend/grid toggles."""
from typing import Optional

from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.components.common.card import Card
from pandaplot.gui.components.common.toggle_switch import ToggleSwitch
from pandaplot.gui.core.widget_extension import PWizardPage
from pandaplot.models.state.app_context import AppContext


class ChartLabelsPage(PWizardPage):
    def __init__(self, app_context: AppContext, parent: Optional[QWidget] = None):
        super().__init__(app_context=app_context, parent=parent)
        self._initialize()

    def _init_ui(self):
        outer = QVBoxLayout(self)

        self._title_touched = False
        self._subtitle_touched = False
        self._x_touched = False
        self._y_touched = False

        form = QFormLayout()
        outer.addLayout(form)

        self.title_edit = QLineEdit()
        self.title_edit.textChanged.connect(lambda: setattr(self, "_title_touched", True))
        form.addRow("Title:", self.title_edit)

        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.textChanged.connect(lambda: setattr(self, "_subtitle_touched", True))
        form.addRow("Subtitle:", self.subtitle_edit)

        self.x_label_edit = QLineEdit()
        self.x_label_edit.textChanged.connect(lambda: setattr(self, "_x_touched", True))
        form.addRow("X-axis label:", self.x_label_edit)

        self.y_label_edit = QLineEdit()
        self.y_label_edit.textChanged.connect(lambda: setattr(self, "_y_touched", True))
        form.addRow("Y-axis label:", self.y_label_edit)

        toggles_card = Card()
        toggles_layout = QGridLayout(toggles_card)
        toggles_layout.addWidget(QLabel("Show legend"), 0, 0)
        self.show_legend_toggle = ToggleSwitch(checked=True)
        toggles_layout.addWidget(self.show_legend_toggle, 0, 1)
        toggles_layout.addWidget(QLabel("Show grid lines"), 1, 0)
        self.show_grid_toggle = ToggleSwitch(checked=True)
        toggles_layout.addWidget(self.show_grid_toggle, 1, 1)
        outer.addWidget(toggles_card)

    def _apply_theme(self):
        # Themed via ChartWizard's stylesheet cascade -- see chart_wizard.py.
        pass

    def set_defaults(self, title: str, x_label: str, y_label: str) -> None:
        """Refresh whichever fields the user hasn't actually edited yet.

        Called every time the wizard's Labels page is entered (not just
        once) -- a field the user has typed into is never touched again
        regardless of what changed elsewhere in the wizard, but an
        untouched field always reflects the current Data-step state (e.g.
        after the user picks a different column for a series). Subtitle has
        no data-derived default, so it's always seeded to "" the same way.
        """
        for edit, touched, value in (
            (self.title_edit, self._title_touched, title),
            (self.subtitle_edit, self._subtitle_touched, ""),
            (self.x_label_edit, self._x_touched, x_label),
            (self.y_label_edit, self._y_touched, y_label),
        ):
            if touched:
                continue
            edit.blockSignals(True)
            try:
                edit.setText(value)
            finally:
                edit.blockSignals(False)

    def get_title(self) -> str:
        return self.title_edit.text()

    def get_subtitle(self) -> str:
        return self.subtitle_edit.text()

    def get_x_label(self) -> str:
        return self.x_label_edit.text()

    def get_y_label(self) -> str:
        return self.y_label_edit.text()

    def get_show_legend(self) -> bool:
        return self.show_legend_toggle.isChecked()

    def get_show_grid(self) -> bool:
        return self.show_grid_toggle.isChecked()
