"""
Grid-view tab for browsing an ImageGallery: thumbnails for Image children,
folder-style tiles for nested ImageGallery children (albums), with
multi-select rename/delete/group-into-album and a double-click lightbox.
"""

from typing import Optional, override

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from pandaplot.commands.project.image import CreateImageGalleryCommand, ImportImagesCommand
from pandaplot.commands.project.item import DeleteItemCommand, MoveItemCommand, RenameItemCommand
from pandaplot.gui.components.common.image_thumbnail_tile import build_gallery_tile_icon
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
        self.root_gallery = gallery
        self.current_gallery = gallery
        # Browser-style single history list + pointer. Navigating (breadcrumb
        # click or album double-click) truncates anything past the pointer
        # before appending, then moves the pointer to the new entry.
        self._history: list[str] = [gallery.id]
        self._history_index: int = 0
        # Session-lifetime cache of already-loaded/scaled thumbnails, keyed by
        # image id. A cached value of None means "failed to load this
        # session, don't retry" -- this avoids re-downloading external URL
        # images (or re-decoding bytes) on every grid repopulation, which
        # otherwise happens on every PROJECT_ITEM_ADDED/REMOVED/RENAMED/MOVED
        # event anywhere in the project.
        self._thumbnail_cache: dict[str, Optional[QPixmap]] = {}
        # Ids of the CURRENT gallery's children as of the last successful
        # _populate_grid() call. Some PROJECT_ITEM_REMOVED events (e.g.
        # undo of an import or of a gallery creation) fire *after* the item
        # has already been removed from self.current_gallery, carrying only
        # the removed item's own id and no parent_id -- so matching against
        # current children alone would miss them. Keeping this snapshot
        # lets _event_concerns_this_gallery still recognize such ids as
        # "was ours as of last populate". Reset whenever current_gallery
        # changes (a stale snapshot from a different gallery level must not
        # leak into this one's filter).
        self._last_child_ids: set[str] = set()
        self._initialize()
        self._populate_grid()
        self.setup_connections()

    @override
    def _init_ui(self):
        layout = QVBoxLayout(self)

        breadcrumb_row = QHBoxLayout()
        self.back_button = PButton("◀", on_click=self._go_back, enabled=False)
        self.forward_button = PButton("▶", on_click=self._go_forward, enabled=False)
        self.breadcrumb_label = QLabel()
        breadcrumb_row.addWidget(self.back_button)
        breadcrumb_row.addWidget(self.forward_button)
        breadcrumb_row.addWidget(self.breadcrumb_label)
        breadcrumb_row.addStretch()
        layout.addLayout(breadcrumb_row)

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
        self.subscribe_to_event(ProjectEvents.PROJECT_ITEM_MOVED, self._on_project_item_changed)

    def get_tab_title(self) -> str:
        return self.root_gallery.name

    def _navigate_to(self, gallery: ImageGallery) -> None:
        """Drill into (or jump to) `gallery` within this same tab, pushing
        onto history and truncating any stale forward branch."""
        self._history = self._history[: self._history_index + 1]
        self._history.append(gallery.id)
        self._history_index = len(self._history) - 1
        self._set_current_gallery(gallery)

    def _go_back(self) -> None:
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._set_current_gallery_by_id(self._history[self._history_index])

    def _go_forward(self) -> None:
        if self._history_index >= len(self._history) - 1:
            return
        self._history_index += 1
        self._set_current_gallery_by_id(self._history[self._history_index])

    def _set_current_gallery_by_id(self, gallery_id: str) -> None:
        found = self.root_gallery if gallery_id == self.root_gallery.id else self._find_gallery(self.root_gallery, gallery_id)
        if found is not None:
            self._set_current_gallery(found)

    def _find_gallery(self, root: ImageGallery, gallery_id: str) -> Optional[ImageGallery]:
        for child in root.get_items():
            if isinstance(child, ImageGallery):
                if child.id == gallery_id:
                    return child
                found = self._find_gallery(child, gallery_id)
                if found is not None:
                    return found
        return None

    def _set_current_gallery(self, gallery: ImageGallery) -> None:
        self.current_gallery = gallery
        self._last_child_ids = set()
        self._rebuild_breadcrumb()
        self._populate_grid()

    def _rebuild_breadcrumb(self) -> None:
        chain: list[ImageGallery] = [self.current_gallery]
        cursor = self.current_gallery
        project = self.app_state.current_project
        while cursor.id != self.root_gallery.id and project is not None:
            parent = project.find_item(cursor.parent_id) if cursor.parent_id else None
            if not isinstance(parent, ImageGallery):
                break
            chain.append(parent)
            cursor = parent
        chain.reverse()
        self.breadcrumb_label.setText(" > ".join(g.name for g in chain))
        self.back_button.setEnabled(self._history_index > 0)
        self.forward_button.setEnabled(self._history_index < len(self._history) - 1)

    def _on_project_item_changed(self, event_data: dict):
        if self._event_concerns_this_gallery(event_data):
            self._populate_grid()

    def _event_concerns_this_gallery(self, event_data: dict) -> bool:
        """
        Best-effort filter so this tab only repopulates for events that
        actually affect its currently-displayed gallery level, rather than
        on every project item add/remove/rename/move anywhere in the
        project (event payloads vary by command, so this checks every key
        we know commands use).
        """
        for key in ("source_folder", "target_folder"):
            value = event_data.get(key)
            if value is not None and value == self.current_gallery.id:
                return True

        parent_id = event_data.get("parent_id")
        if parent_id is not None:
            return parent_id == self.current_gallery.id

        item_data = event_data.get("item_data")
        if isinstance(item_data, dict) and "parent_id" in item_data:
            return item_data.get("parent_id") == self.current_gallery.id

        candidate_ids = {
            event_data.get(key)
            for key in ("item_id", "gallery_id", "image_id")
            if event_data.get(key)
        }
        if not candidate_ids:
            # No usable identifying info at all -- fall back to repopulating,
            # since we can't safely rule the event out.
            return True
        if self.current_gallery.id in candidate_ids:
            return True
        current_child_ids = {child.id for child in self.current_gallery.get_items()}
        return bool(candidate_ids & (current_child_ids | self._last_child_ids))

    def _populate_grid(self):
        self.grid.clear()
        tokens = self._current_tokens()
        for child in self.current_gallery.get_items():
            item = QListWidgetItem(child.name)
            item.setData(Qt.ItemDataRole.UserRole, child.id)
            if isinstance(child, ImageGallery):
                item.setIcon(build_gallery_tile_icon(None, "album", False, tokens))
            elif isinstance(child, Image):
                item.setIcon(build_gallery_tile_icon(self._thumbnail_for(child), "image", False, tokens))
            self.grid.addItem(item)
        self._last_child_ids = {child.id for child in self.current_gallery.get_items()}
        self._refresh_toolbar_state()

    def _current_tokens(self) -> dict:
        from pandaplot.services.theme.theme_manager import ThemeManager

        return self.app_context.get_manager(ThemeManager).get_design_tokens()

    def _thumbnail_for(self, image: Image) -> QPixmap:
        """Load (or fetch) image bytes and downscale in memory; broken placeholder on any failure.

        Results (including failures) are cached for the tab's lifetime, keyed
        by image id, so external URL images in particular are not
        re-downloaded on every grid repopulation within the same session.
        """
        if image.id in self._thumbnail_cache:
            cached = self._thumbnail_cache[image.id]
            return cached if cached is not None else self._broken_placeholder()

        try:
            data = image.get_bytes()
            if data is None and image.storage_mode == "external":
                data = self._load_external_bytes(image.source_file)
            if data is None:
                raise ValueError("no image data")

            pixmap = QPixmap()
            if not pixmap.loadFromData(data):
                raise ValueError("could not decode image data")
            scaled = pixmap.scaled(_TILE_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._thumbnail_cache[image.id] = scaled
            return scaled
        except Exception:
            self.logger.warning("Failed to load thumbnail for image '%s' (id=%s)", image.name, image.id)
            self._thumbnail_cache[image.id] = None
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
        return [child for child in self.current_gallery.get_items() if child.id in selected_ids]

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
            self.app_context, gallery_id=self.current_gallery.id,
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
            command = DeleteItemCommand(self.app_context, item_id=item.id, confirm=False)
            self.app_context.get_command_executor().execute_command(command)

    def _on_group_into_album_clicked(self):
        selected = [c for c in self._selected_children() if isinstance(c, Image)]
        if len(selected) < 2:
            return
        album_name, ok = QInputDialog.getText(self, "Group into Album", "Album name:")
        if not ok or not album_name.strip():
            return

        create_command = CreateImageGalleryCommand(
            self.app_context, gallery_name=album_name.strip(), parent_id=self.current_gallery.id
        )
        self.app_context.get_command_executor().execute_command(create_command)
        album_id = create_command.created_gallery_id
        if album_id is None:
            return

        for image in selected:
            move_command = MoveItemCommand(
                self.app_context, item_id=image.id, item_type="image",
                source_folder_id=self.current_gallery.id, target_folder_id=album_id,
            )
            self.app_context.get_command_executor().execute_command(move_command)

    def _on_item_double_clicked(self, list_item: QListWidgetItem):
        child_id = list_item.data(Qt.ItemDataRole.UserRole)
        child = self.current_gallery.get_item_by_id(child_id)
        if child is None:
            return

        if isinstance(child, ImageGallery):
            self._navigate_to(child)
        elif isinstance(child, Image):
            pixmap = QPixmap()
            data = child.get_bytes() or self._load_external_bytes(child.source_file)
            if data and pixmap.loadFromData(data):
                ImageLightboxDialog(pixmap, child.name, parent=self).exec()
