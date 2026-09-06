"""Version History dialog for viewing, creating, and reverting snapshots."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pandaplot.commands.project.versioning.create_version_snapshot_command import (
    CreateVersionSnapshotCommand,
)
from pandaplot.commands.project.versioning.revert_to_version_command import (
    RevertToVersionCommand,
)
from pandaplot.gui.core.widget_extension import PDialog
from pandaplot.models.state.app_context import AppContext
from pandaplot.storage.version_manager import VersionManager


class VersionHistoryDialog(PDialog):
    """Dialog displaying historical version snapshots and allowing snapshot creation/reversion."""

    def __init__(
        self,
        app_context: AppContext,
        parent: Optional[QWidget] = None,
        item_id: Optional[str] = None,
    ):
        super().__init__(app_context=app_context, parent=parent)
        self.item_id = item_id
        self.setWindowTitle("Version History")
        self.resize(600, 400)

        self._init_dialog_ui()
        self._refresh_snapshots()

    def _init_dialog_ui(self):
        layout = QVBoxLayout(self)

        title_text = "Project Version History" if self.item_id is None else "Item Version History"
        title_label = QLabel(f"<h3>{title_text}</h3>", self)
        layout.addWidget(title_label)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Label", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        self.create_btn = QPushButton("Create Snapshot...", self)
        self.create_btn.clicked.connect(self._on_create_snapshot)
        btn_layout.addWidget(self.create_btn)

        self.revert_btn = QPushButton("Revert to Selected", self)
        self.revert_btn.clicked.connect(self._on_revert_snapshot)
        btn_layout.addWidget(self.revert_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _get_version_manager(self) -> Optional[VersionManager]:
        app_state = self.app_context.get_app_state()
        version_manager = self.app_context.get_manager(VersionManager) if hasattr(self.app_context, "get_manager") else None
        if version_manager is None and hasattr(app_state, "_version_manager"):
            version_manager = app_state._version_manager
        return version_manager

    def _refresh_snapshots(self):
        version_manager = self._get_version_manager()

        snapshots = []
        if version_manager:
            if self.item_id is None:
                snapshots = version_manager.get_snapshots_for_project()
            else:
                snapshots = version_manager.get_snapshots_for_item(self.item_id)

        self.table.setRowCount(len(snapshots))
        self.snapshots = snapshots

        for row, s in enumerate(snapshots):
            time_item = QTableWidgetItem(s.created_at)
            label_item = QTableWidgetItem(s.label)
            type_item = QTableWidgetItem(s.version_type)

            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            label_item.setFlags(label_item.flags() & ~Qt.ItemIsEditable)
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row, 0, time_item)
            self.table.setItem(row, 1, label_item)
            self.table.setItem(row, 2, type_item)

    def _on_create_snapshot(self):
        text, ok = QInputDialog.getText(self, "Create Snapshot", "Snapshot Description/Label:")
        if ok and text:
            cmd = CreateVersionSnapshotCommand(self.app_context, label=text, item_id=self.item_id)
            self.app_context.get_command_executor().execute_command(cmd)
            self._refresh_snapshots()

    def _on_revert_snapshot(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.snapshots):
            return

        snapshot = self.snapshots[row]
        cmd = RevertToVersionCommand(self.app_context, version_id=snapshot.version_id)
        self.app_context.get_command_executor().execute_command(cmd)
        self.accept()
