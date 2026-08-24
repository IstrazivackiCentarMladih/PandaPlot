from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.image.gallery_destination_picker_dialog import (
    GalleryDestinationPickerDialog,
)
from pandaplot.models.project.items import ImageGallery
from pandaplot.models.state.app_context import AppContext


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def app_context():
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    ctx.get_app_state.return_value = Mock()
    return ctx


class _ProjectStub:
    """Minimal Project stand-in: a root id plus a flat list of ImageGallery items."""
    def __init__(self, root_id: str, items):
        self.root = Mock()
        self.root.id = root_id
        self._items = items

    def get_all_items(self):
        return self._items


class TestGalleryDestinationPickerDialogTreePopulation:
    def test_shows_multiple_top_level_galleries(self, app_context):
        gallery_a = ImageGallery(name="Trip")
        gallery_b = ImageGallery(name="Work")
        project = _ProjectStub(root_id="root", items=[])
        gallery_a.parent_id = project.root.id
        gallery_b.parent_id = project.root.id
        project._items = [gallery_a, gallery_b]

        dialog = GalleryDestinationPickerDialog(app_context, project)

        top_level_names = {dialog.tree.topLevelItem(i).text(0) for i in range(dialog.tree.topLevelItemCount())}
        assert top_level_names == {"Trip", "Work"}

    def test_shows_nested_album_under_its_gallery(self, app_context):
        gallery = ImageGallery(name="Trip")
        album = ImageGallery(name="Day 1")
        project = _ProjectStub(root_id="root", items=[])
        gallery.parent_id = project.root.id
        album.parent_id = gallery.id
        project._items = [gallery, album]

        dialog = GalleryDestinationPickerDialog(app_context, project)

        assert dialog.tree.topLevelItemCount() == 1
        gallery_item = dialog.tree.topLevelItem(0)
        assert gallery_item.text(0) == "Trip"
        assert gallery_item.childCount() == 1
        assert gallery_item.child(0).text(0) == "Day 1"

    def test_get_selected_gallery_id_returns_none_when_nothing_selected(self, app_context):
        gallery = ImageGallery(name="Trip")
        project = _ProjectStub(root_id="root", items=[])
        gallery.parent_id = project.root.id
        project._items = [gallery]

        dialog = GalleryDestinationPickerDialog(app_context, project)

        assert dialog.get_selected_gallery_id() is None


class TestGalleryDestinationPickerDialogPreselection:
    def test_preselects_current_gallery(self, app_context):
        gallery = ImageGallery(name="Trip")
        album = ImageGallery(name="Day 1")
        project = _ProjectStub(root_id="root", items=[])
        gallery.parent_id = project.root.id
        album.parent_id = gallery.id
        project._items = [gallery, album]

        dialog = GalleryDestinationPickerDialog(app_context, project, current_gallery_id=album.id)

        assert dialog.get_selected_gallery_id() == album.id

    def test_ok_button_enabled_when_a_gallery_is_selected(self, app_context):
        gallery = ImageGallery(name="Trip")
        project = _ProjectStub(root_id="root", items=[])
        gallery.parent_id = project.root.id
        project._items = [gallery]

        dialog = GalleryDestinationPickerDialog(app_context, project, current_gallery_id=gallery.id)

        assert dialog.ok_button.isEnabled() is True

    def test_ok_button_disabled_when_nothing_selected(self, app_context):
        gallery = ImageGallery(name="Trip")
        project = _ProjectStub(root_id="root", items=[])
        gallery.parent_id = project.root.id
        project._items = [gallery]

        dialog = GalleryDestinationPickerDialog(app_context, project)

        assert dialog.ok_button.isEnabled() is False
