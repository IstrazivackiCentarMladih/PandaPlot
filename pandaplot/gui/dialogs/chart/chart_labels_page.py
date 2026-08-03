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

        self.title_edit = QLineEdit()
        form.addRow("Title:", self.title_edit)

        self.x_label_edit = QLineEdit()
        form.addRow("X-axis label:", self.x_label_edit)

        self.y_label_edit = QLineEdit()
        form.addRow("Y-axis label:", self.y_label_edit)

    def _apply_theme(self):
        # Themed via ChartWizard's stylesheet cascade -- see chart_wizard.py.
        pass

    def set_defaults(self, title: str, x_label: str, y_label: str) -> None:
        self.title_edit.setText(title)
        self.x_label_edit.setText(x_label)
        self.y_label_edit.setText(y_label)

    def get_title(self) -> str:
        return self.title_edit.text()

    def get_x_label(self) -> str:
        return self.x_label_edit.text()

    def get_y_label(self) -> str:
        return self.y_label_edit.text()
