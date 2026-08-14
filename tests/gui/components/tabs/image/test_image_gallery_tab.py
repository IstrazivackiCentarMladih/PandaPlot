"""Tests for ImageGalleryTab."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.tabs.image.image_gallery_tab import ImageGalleryTab
from pandaplot.models.project.items import Image, ImageGallery
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


class TestImageGalleryTab:
    def test_tab_title_is_gallery_name(self, app_context):
        gallery = ImageGallery(name="Trip Photos")
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        assert tab.get_tab_title() == "Trip Photos"

    def test_grid_has_one_tile_per_child(self, app_context):
        gallery = ImageGallery(name="Trip")
        gallery.add_item(Image(name="Beach"))
        gallery.add_item(Image(name="Mountain"))
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        assert tab.grid.count() == 2

    def test_album_child_gets_a_tile_too(self, app_context):
        gallery = ImageGallery(name="Trip")
        gallery.add_item(ImageGallery(name="Day 1"))
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        assert tab.grid.count() == 1
        assert tab.grid.item(0).text() == "Day 1"

    def test_selecting_tile_enables_delete_button(self, app_context):
        gallery = ImageGallery(name="Trip")
        gallery.add_item(Image(name="Beach"))
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        assert tab.delete_button.isEnabled() is False

        tab.grid.item(0).setSelected(True)
        tab.grid.itemSelectionChanged.emit()

        assert tab.delete_button.isEnabled() is True

    def test_group_into_album_button_enabled_only_for_multi_image_selection(self, app_context):
        gallery = ImageGallery(name="Trip")
        gallery.add_item(Image(name="Beach"))
        gallery.add_item(Image(name="Mountain"))
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        assert tab.group_into_album_button.isEnabled() is False

        tab.grid.item(0).setSelected(True)
        tab.grid.item(1).setSelected(True)
        tab.grid.itemSelectionChanged.emit()

        assert tab.group_into_album_button.isEnabled() is True


class TestEventConcernsThisGallery:
    def test_removed_item_no_longer_in_gallery_still_matches_last_populate(self, app_context):
        """Regression: undo of ImportImagesCommand removes the image from the
        gallery *then* emits PROJECT_ITEM_REMOVED with only
        {"project", "image_id"} (no parent_id). By the time the event
        arrives, gallery.get_items() no longer contains it, so matching
        against current children alone would miss it and leave a stale
        tile. The filter must still recognize it via the last-populate
        snapshot.
        """
        gallery = ImageGallery(name="Trip")
        image = Image(name="Beach")
        gallery.add_item(image)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)
        assert tab.grid.count() == 1

        # Simulate the undo: item already removed from the gallery by the
        # time the event fires.
        gallery.remove_item(image)
        event_data = {"project": Mock(), "image_id": image.id}

        assert tab._event_concerns_this_gallery(event_data) is True

    def test_unrelated_removed_item_does_not_match(self, app_context):
        gallery = ImageGallery(name="Trip")
        image = Image(name="Beach")
        gallery.add_item(image)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        event_data = {"project": Mock(), "image_id": "some-other-id-never-in-this-gallery"}

        assert tab._event_concerns_this_gallery(event_data) is False
