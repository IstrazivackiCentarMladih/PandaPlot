"""Step 3 of the chart creation wizard: chart title and X/Y axis labels."""
from typing import Optional

from PySide6.QtWidgets import QFormLayout, QLineEdit, QWidget

from pandaplot.gui.core.widget_extension import PWizardPage
from pandaplot.models.state.app_context import AppContext


class ChartLabelsPage(PWizardPage):
    def __init__(self, app_context: AppContext, parent: Optional[QWidget] = None):
        super().__init__(app_context=app_context, parent=parent)
        self._initialize()

    def _init_ui(self):
        self.setTitle("Title and axis labels")
        form = QFormLayout(self)

        self._title_touched = False
        self._x_touched = False
        self._y_touched = False

        self.title_edit = QLineEdit()
        self.title_edit.textChanged.connect(lambda: setattr(self, "_title_touched", True))
        form.addRow("Title:", self.title_edit)

        self.x_label_edit = QLineEdit()
        self.x_label_edit.textChanged.connect(lambda: setattr(self, "_x_touched", True))
        form.addRow("X-axis label:", self.x_label_edit)

        self.y_label_edit = QLineEdit()
        self.y_label_edit.textChanged.connect(lambda: setattr(self, "_y_touched", True))
        form.addRow("Y-axis label:", self.y_label_edit)

    def _apply_theme(self):
        # Themed via ChartWizard's stylesheet cascade -- see chart_wizard.py.
        pass

    def set_defaults(self, title: str, x_label: str, y_label: str) -> None:
        """Refresh whichever fields the user hasn't actually edited yet.

        Called every time the wizard's Labels page is entered (not just
        once) -- a field the user has typed into is never touched again
        regardless of what changed elsewhere in the wizard, but an
        untouched field always reflects the current Data-step state (e.g.
        after the user picks a different column for a series).
        """
        for edit, touched, value in (
            (self.title_edit, self._title_touched, title),
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

    def get_x_label(self) -> str:
        return self.x_label_edit.text()

    def get_y_label(self) -> str:
        return self.y_label_edit.text()
