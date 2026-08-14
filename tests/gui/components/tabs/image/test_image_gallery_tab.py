"""Tests for ImageGalleryTab."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.tabs.image.image_gallery_tab import ImageGalleryTab
from pandaplot.models.project.items import Image, ImageGallery
from pandaplot.models.state.app_context import AppContext
from pandaplot.services.theme.theme_manager import ThemeManager


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


_FAKE_TOKENS = {
    "text_muted": "#6B7280",
    "border_subtle": "#ECEEF2",
    "surface_white": "#FFFFFF",
    "accent": "#4A56C6",
    "accent_selected_bg": "#EEF0FB",
}


@pytest.fixture
def app_context():
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    ctx.get_app_state.return_value = Mock()

    theme_manager = Mock()
    theme_manager.get_design_tokens.return_value = dict(_FAKE_TOKENS)

    def _get_manager(manager_type, *args, **kwargs):
        if manager_type is ThemeManager:
            return theme_manager
        return Mock()

    ctx.get_manager.side_effect = _get_manager
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


class TestImageGalleryTabNavigation:
    def test_root_gallery_is_current_gallery_initially(self, app_context):
        gallery = ImageGallery(name="Trip")
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        assert tab.root_gallery is gallery
        assert tab.current_gallery is gallery

    def test_tab_title_stays_root_name_after_navigating(self, app_context):
        gallery = ImageGallery(name="Trip")
        album = ImageGallery(name="Day 1")
        gallery.add_item(album)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        tab._navigate_to(album)

        assert tab.get_tab_title() == "Trip"
        assert tab.current_gallery is album

    def test_navigate_to_repopulates_grid_for_new_current_gallery(self, app_context):
        gallery = ImageGallery(name="Trip")
        album = ImageGallery(name="Day 1")
        album.add_item(Image(name="Sunrise"))
        gallery.add_item(album)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)
        assert tab.grid.count() == 1  # just the album tile

        tab._navigate_to(album)

        assert tab.grid.count() == 1  # now the album's own child
        assert tab.grid.item(0).text() == "Sunrise"

    def test_back_and_forward_navigate_history(self, app_context):
        gallery = ImageGallery(name="Trip")
        album = ImageGallery(name="Day 1")
        gallery.add_item(album)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        tab._navigate_to(album)
        assert tab.current_gallery is album

        tab._go_back()
        assert tab.current_gallery is gallery

        tab._go_forward()
        assert tab.current_gallery is album

    def test_navigating_after_going_back_truncates_forward_history(self, app_context):
        gallery = ImageGallery(name="Trip")
        album_a = ImageGallery(name="Day 1")
        album_b = ImageGallery(name="Day 2")
        gallery.add_item(album_a)
        gallery.add_item(album_b)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        tab._navigate_to(album_a)
        tab._go_back()
        tab._navigate_to(album_b)

        # forward history from album_a's branch should be gone
        tab._go_back()
        assert tab.current_gallery is gallery
        tab._go_forward()
        assert tab.current_gallery is album_b

    def test_double_click_album_navigates_in_place_not_new_tab(self, app_context):
        gallery = ImageGallery(name="Trip")
        album = ImageGallery(name="Day 1")
        gallery.add_item(album)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        tab._on_item_double_clicked(tab.grid.item(0))

        assert tab.current_gallery is album
        app_context.get_app_state.return_value.event_bus.emit.assert_not_called()


class TestImageGalleryTabMovedEvent:
    def test_subscribes_to_project_item_moved(self, app_context):
        gallery = ImageGallery(name="Trip")
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)

        subscribed_events = [call.args[0] for call in app_context.event_bus.subscribe.call_args_list]
        from pandaplot.models.events.event_types import ProjectEvents
        assert ProjectEvents.PROJECT_ITEM_MOVED in subscribed_events

    def test_moved_event_matching_source_folder_repopulates(self, app_context):
        gallery = ImageGallery(name="Trip")
        image = Image(name="Beach")
        gallery.add_item(image)
        tab = ImageGalleryTab(app_context=app_context, gallery=gallery, parent=None)
        assert tab.grid.count() == 1

        # Simulate the move: image already removed from this gallery by the
        # time MoveItemCommand's event fires (mirrors PROJECT_ITEM_REMOVED's
        # existing timing in this codebase).
        gallery.remove_item(image)
        event_data = {
            "project": Mock(), "item_id": image.id, "item_type": "image",
            "source_folder": gallery.id, "target_folder": "some-album-id", "item": image,
        }

        assert tab._event_concerns_this_gallery(event_data) is True
        tab._on_project_item_changed(event_data)
        assert tab.grid.count() == 0
