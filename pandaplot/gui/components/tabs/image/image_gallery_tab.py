"""
Grid-view tab for browsing an ImageGallery: thumbnails for Image children,
folder-style tiles for nested ImageGallery children (albums), with
multi-select rename/delete/group-into-album and a double-click lightbox.
"""

from typing import Optional, override

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from pandaplot.commands.project.image import CreateImageGalleryCommand, ImportImagesCommand
from pandaplot.commands.project.item import DeleteItemCommand, MoveItemCommand, RenameItemCommand
from pandaplot.gui.components.common.p_button import PButton
from pandaplot.gui.components.tabs.image.image_lightbox_dialog import ImageLightboxDialog
from pandaplot.gui.core.widget_extension import PWidget
from pandaplot.models.events.event_types import ProjectEvents
from pandaplot.models.project.items import Image, ImageGallery
from pandaplot.models.state.app_context import AppContext

_TILE_SIZE = QSize(120, 120)


class ImageGalleryTab(PWidget):
    """Thumbnail-grid tab for browsing and managing one ImageGallery's contents."""

    def __init__(self, app_context: AppContext, gallery: ImageGallery, parent: Optional[QWidget] = None):
        super().__init__(app_context=app_context, parent=parent)
        self.app_context = app_context
        self.app_state = app_context.get_app_state()
        self.gallery = gallery
        self._initialize()
        self._populate_grid()
        self.setup_connections()

    @override
    def _init_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.import_button = PButton("Import Images...", on_click=self._on_import_clicked)
        self.rename_button = PButton("Rename", on_click=self._on_rename_clicked, enabled=False)
        self.delete_button = PButton("Delete", role="destructive", on_click=self._on_delete_clicked, enabled=False)
        self.group_into_album_button = PButton("Group into Album", on_click=self._on_group_into_album_clicked, enabled=False)
        for button in (self.import_button, self.rename_button, self.delete_button, self.group_into_album_button):
            toolbar.addWidget(button)
        layout.addLayout(toolbar)

        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setIconSize(_TILE_SIZE)
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.grid)

        self.grid.itemSelectionChanged.connect(self._refresh_toolbar_state)
        self.grid.itemDoubleClicked.connect(self._on_item_double_clicked)

    @override
    def _apply_theme(self):
        pass

    def setup_connections(self):
        self.subscribe_to_event(ProjectEvents.PROJECT_ITEM_ADDED, self._on_project_item_changed)
        self.subscribe_to_event(ProjectEvents.PROJECT_ITEM_REMOVED, self._on_project_item_changed)
        self.subscribe_to_event(ProjectEvents.PROJECT_ITEM_RENAMED, self._on_project_item_changed)

    def get_tab_title(self) -> str:
        return self.gallery.name

    def _on_project_item_changed(self, event_data: dict):
        self._populate_grid()

    def _populate_grid(self):
        self.grid.clear()
        for child in self.gallery.get_items():
            item = QListWidgetItem(child.name)
            item.setData(Qt.ItemDataRole.UserRole, child.id)
            if isinstance(child, ImageGallery):
                item.setIcon(QIcon.fromTheme("folder"))
            elif isinstance(child, Image):
                item.setIcon(QIcon(self._thumbnail_for(child)))
            self.grid.addItem(item)
        self._refresh_toolbar_state()

    def _thumbnail_for(self, image: Image) -> QPixmap:
        """Load (or fetch) image bytes and downscale in memory; broken placeholder on any failure."""
        try:
            data = image.get_bytes()
            if data is None and image.storage_mode == "external":
                data = self._load_external_bytes(image.source_file)
            if data is None:
                raise ValueError("no image data")

            pixmap = QPixmap()
            if not pixmap.loadFromData(data):
                raise ValueError("could not decode image data")
            return pixmap.scaled(_TILE_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except Exception:
            self.logger.warning("Failed to load thumbnail for image '%s' (id=%s)", image.name, image.id)
            return self._broken_placeholder()

    def _load_external_bytes(self, source_file: str) -> Optional[bytes]:
        import os

        if source_file.startswith("http://") or source_file.startswith("https://"):
            import requests
            response = requests.get(source_file, timeout=10)
            response.raise_for_status()
            return response.content

        if os.path.isfile(source_file):
            with open(source_file, "rb") as f:
                return f.read()
        return None

    def _broken_placeholder(self) -> QPixmap:
        pixmap = QPixmap(_TILE_SIZE)
        pixmap.fill(Qt.GlobalColor.lightGray)
        return pixmap

    def _selected_ids(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.grid.selectedItems()]

    def _selected_children(self):
        selected_ids = set(self._selected_ids())
        return [child for child in self.gallery.get_items() if child.id in selected_ids]

    def _refresh_toolbar_state(self):
        selected = self._selected_children()
        self.rename_button.setEnabled(len(selected) == 1)
        self.delete_button.setEnabled(len(selected) >= 1)
        self.group_into_album_button.setEnabled(
            len(selected) >= 2 and all(isinstance(c, Image) for c in selected)
        )

    def _on_import_clicked(self):
        from PySide6.QtWidgets import QDialog

        from pandaplot.gui.dialogs.image.image_import_dialog import ImageImportDialog

        dialog = ImageImportDialog(self.app_context, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        command = ImportImagesCommand(
            self.app_context, gallery_id=self.gallery.id,
            sources=dialog.get_sources(), copy_into_project=dialog.get_copy_into_project(),
        )
        self.app_context.get_command_executor().execute_command(command)

    def _on_rename_clicked(self):
        selected = self._selected_children()
        if len(selected) != 1:
            return
        item = selected[0]
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=item.name)
        if not ok or not new_name.strip():
            return
        command = RenameItemCommand(self.app_context, item_id=item.id, new_name=new_name.strip())
        self.app_context.get_command_executor().execute_command(command)

    def _on_delete_clicked(self):
        selected = self._selected_children()
        if not selected:
            return
        names = ", ".join(c.name for c in selected)
        confirmed = QMessageBox.question(
            self, "Delete", f"Delete {len(selected)} item(s)? ({names})"
        ) == QMessageBox.StandardButton.Yes
        if not confirmed:
            return
        for item in selected:
            command = DeleteItemCommand(self.app_context, item_id=item.id)
            self.app_context.get_command_executor().execute_command(command)

    def _on_group_into_album_clicked(self):
        selected = [c for c in self._selected_children() if isinstance(c, Image)]
        if len(selected) < 2:
            return
        album_name, ok = QInputDialog.getText(self, "Group into Album", "Album name:")
        if not ok or not album_name.strip():
            return

        create_command = CreateImageGalleryCommand(
            self.app_context, gallery_name=album_name.strip(), parent_id=self.gallery.id
        )
        if not self.app_context.get_command_executor().execute_command(create_command):
            return
        album_id = create_command.created_gallery_id

        for image in selected:
            move_command = MoveItemCommand(
                self.app_context, item_id=image.id, item_type="image",
                source_folder_id=self.gallery.id, target_folder_id=album_id,
            )
            self.app_context.get_command_executor().execute_command(move_command)

    def _on_item_double_clicked(self, list_item: QListWidgetItem):
        child_id = list_item.data(Qt.ItemDataRole.UserRole)
        child = self.gallery.get_item_by_id(child_id)
        if child is None:
            return

        if isinstance(child, ImageGallery):
            from pandaplot.models.events.event_data import TabOpenRequestedData
            from pandaplot.models.events.event_types import UIEvents

            self.app_state.event_bus.emit(UIEvents.TAB_OPEN_REQUESTED, TabOpenRequestedData(
                item_id=child.id, item_name=child.name
            ).to_dict())
        elif isinstance(child, Image):
            pixmap = QPixmap()
            data = child.get_bytes() or self._load_external_bytes(child.source_file)
            if data and pixmap.loadFromData(data):
                ImageLightboxDialog(pixmap, child.name, parent=self).exec()
