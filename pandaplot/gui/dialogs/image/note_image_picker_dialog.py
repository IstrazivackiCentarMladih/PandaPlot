"""Dialog for selecting an Image from project galleries to insert into a note."""

import os
from typing import Dict, Optional, override

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.components.common.image_thumbnail_tile import build_gallery_tile_icon
from pandaplot.gui.components.common.p_button import PButton
from pandaplot.gui.core.widget_extension import PDialog
from pandaplot.models.project.items import Image, ImageGallery, Item
from pandaplot.models.state.app_context import AppContext
from pandaplot.services.theme.theme_manager import ThemeManager

_ICON_SIZE = QSize(24, 24)


class NoteImagePickerDialog(PDialog):
    """
    Dialog displaying all gallery images in the project, allowing the user
    to pick an image to insert into a Markdown note.
    """

    def __init__(
        self,
        app_context: AppContext,
        project,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(app_context=app_context, parent=parent)
        self.project = project
        self._selected_image: Optional[Image] = None
        self._initialize()
        self._populate_tree()
        self._refresh_ok_enabled()

    @override
    def _init_ui(self):
        self.setWindowTitle("Insert Image from Gallery")
        self.resize(400, 350)
        layout = QVBoxLayout(self)

        self.empty_label = QLabel("No images found in the project gallery.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(_ICON_SIZE)
        self.tree.itemSelectionChanged.connect(self._refresh_ok_enabled)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        button_row = QHBoxLayout()
        self.cancel_button = PButton("Cancel", role="secondary", on_click=self.reject)
        self.ok_button = PButton("Insert Image", role="primary", on_click=self._on_ok_clicked, enabled=False)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.ok_button)
        layout.addLayout(button_row)

    @override
    def _apply_theme(self):
        pass

    def _get_tokens(self) -> dict:
        return self.app_context.get_manager(ThemeManager).get_design_tokens()

    def _load_pixmap_for_image(self, image: Image) -> Optional[QPixmap]:
        try:
            data = image.get_bytes()
            if data is None and image.storage_mode == "external":
                source = image.source_file
                if source.startswith("http://") or source.startswith("https://"):
                    import requests
                    resp = requests.get(source, timeout=5)
                    resp.raise_for_status()
                    data = resp.content
                elif os.path.isfile(source):
                    with open(source, "rb") as f:
                        data = f.read()
            if data:
                pix = QPixmap()
                if pix.loadFromData(data):
                    return pix
        except Exception:
            pass
        return None

    def _tile_icon_for(self, item) -> QIcon:
        tokens = self._get_tokens()
        if isinstance(item, ImageGallery):
            return build_gallery_tile_icon(None, "album", selected=False, tokens=tokens, size=_ICON_SIZE)
        if isinstance(item, Image):
            pix = self._load_pixmap_for_image(item)
            tile_type = "image" if pix is not None else "broken"
            return build_gallery_tile_icon(pix, tile_type, selected=False, tokens=tokens, size=_ICON_SIZE)
        return build_gallery_tile_icon(None, "broken", selected=False, tokens=tokens, size=_ICON_SIZE)

    def _populate_tree(self) -> None:
        self.tree.clear()
        if self.project is None:
            self.empty_label.setVisible(True)
            self.tree.setVisible(False)
            return

        all_items = self.project.get_all_items()
        all_images = [item for item in all_items if isinstance(item, Image)]
        if not all_images:
            self.empty_label.setVisible(True)
            self.tree.setVisible(False)
            return

        self.empty_label.setVisible(False)
        self.tree.setVisible(True)

        galleries = [item for item in all_items if isinstance(item, ImageGallery)]
        by_id: Dict[str, QTreeWidgetItem] = {}
        items_by_id: Dict[str, Item] = {i.id: i for i in all_items}

        # First, build gallery collection nodes
        for gallery in galleries:
            tree_item = QTreeWidgetItem([gallery.name])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, gallery.id)
            tree_item.setIcon(0, self._tile_icon_for(gallery))
            by_id[gallery.id] = tree_item

        # Attach nested galleries to parent gallery or root tree
        for gallery in galleries:
            tree_item = by_id[gallery.id]
            parent = items_by_id.get(gallery.parent_id) if gallery.parent_id else None
            if parent and parent.id in by_id:
                by_id[parent.id].addChild(tree_item)
            else:
                self.tree.addTopLevelItem(tree_item)

        # Attach image nodes
        for img in all_images:
            tree_item = QTreeWidgetItem([img.name])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, img.id)
            tree_item.setIcon(0, self._tile_icon_for(img))
            by_id[img.id] = tree_item

            parent = items_by_id.get(img.parent_id) if img.parent_id else None
            if parent and parent.id in by_id:
                by_id[parent.id].addChild(tree_item)
            else:
                self.tree.addTopLevelItem(tree_item)

        self.tree.expandAll()

    def _get_selected_item_object(self) -> Optional[object]:
        selected = self.tree.selectedItems()
        if not selected or self.project is None:
            return None
        item_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        return self.project.find_item(item_id)

    def _refresh_ok_enabled(self) -> None:
        item = self._get_selected_item_object()
        self.ok_button.setEnabled(isinstance(item, Image))

    def _on_item_double_clicked(self, tree_item: QTreeWidgetItem, column: int) -> None:
        item = self._get_selected_item_object()
        if isinstance(item, Image):
            self._selected_image = item
            self.accept()

    def _on_ok_clicked(self) -> None:
        item = self._get_selected_item_object()
        if isinstance(item, Image):
            self._selected_image = item
            self.accept()

    def get_selected_image(self) -> Optional[Image]:
        """Return the selected Image model, or None if dialog was cancelled/no selection."""
        return self._selected_image
