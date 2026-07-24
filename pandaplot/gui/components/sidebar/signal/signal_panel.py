from typing import Optional, override

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from pandaplot.analysis import SIGNAL_ANALYSES, SignalAnalysisType
from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.state.app_context import AppContext


class SignalPanel(PWidget):
    """Sidebar panel for signal analysis."""

    def __init__(
        self,
        app_context: AppContext,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(app_context=app_context, parent=parent)

        self._initialize()

    @override
    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("📡 Signal Analysis")
        layout.addWidget(title)

        group = QGroupBox("Analysis")
        form = QFormLayout()

        self.analysis_combo = QComboBox()

        for analysis_type, info in SIGNAL_ANALYSES.items():
            self.analysis_combo.addItem(info.label, analysis_type)

        self.analysis_combo.currentIndexChanged.connect(
            self._on_analysis_changed
        )

        form.addRow("Method:", self.analysis_combo)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)

        form.addRow("", self.description_label)

        group.setLayout(form)

        layout.addWidget(group)

        layout.addStretch()

        self._on_analysis_changed()

    def _on_analysis_changed(self):
        analysis_type = self.analysis_combo.currentData()

        if analysis_type is None:
            return

        info = SIGNAL_ANALYSES[analysis_type]

        self.description_label.setText(info.description)

    @override
    def _apply_theme(self):
        pass

    @override
    def setup_event_subscriptions(self):
        pass