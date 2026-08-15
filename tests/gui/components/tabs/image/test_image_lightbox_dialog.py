import pytest
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.tabs.image.image_lightbox_dialog import ImageLightboxDialog
from pandaplot.models.project.items import Image


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _colored_pixmap(color: str) -> QPixmap:
    pixmap = QPixmap(10, 10)
    pixmap.fill(QColor(color))
    return pixmap


class TestImageLightboxDialogNavigation:
    def test_starts_at_given_index_with_matching_title(self):
        images = [Image(name="First"), Image(name="Second"), Image(name="Third")]
        dialog = ImageLightboxDialog(images, 1, load_pixmap=lambda img: _colored_pixmap("red"))

        assert dialog.windowTitle() == "Second"

    def test_previous_disabled_at_first_index(self):
        images = [Image(name="First"), Image(name="Second")]
        dialog = ImageLightboxDialog(images, 0, load_pixmap=lambda img: _colored_pixmap("red"))

        assert dialog.previous_button.isEnabled() is False
        assert dialog.next_button.isEnabled() is True

    def test_next_disabled_at_last_index(self):
        images = [Image(name="First"), Image(name="Second")]
        dialog = ImageLightboxDialog(images, 1, load_pixmap=lambda img: _colored_pixmap("red"))

        assert dialog.previous_button.isEnabled() is True
        assert dialog.next_button.isEnabled() is False

    def test_next_advances_index_and_title(self):
        images = [Image(name="First"), Image(name="Second")]
        dialog = ImageLightboxDialog(images, 0, load_pixmap=lambda img: _colored_pixmap("red"))

        dialog._go_next()

        assert dialog.windowTitle() == "Second"
        assert dialog.next_button.isEnabled() is False

    def test_previous_after_next_returns_to_start(self):
        images = [Image(name="First"), Image(name="Second"), Image(name="Third")]
        dialog = ImageLightboxDialog(images, 0, load_pixmap=lambda img: _colored_pixmap("red"))

        dialog._go_next()
        dialog._go_previous()

        assert dialog.windowTitle() == "First"

    def test_failed_load_shows_broken_placeholder_without_crashing(self):
        images = [Image(name="Broken")]

        def _failing_load(img):
            return None

        dialog = ImageLightboxDialog(images, 0, load_pixmap=_failing_load)

        assert dialog.image_label.pixmap() is not None
        assert not dialog.image_label.pixmap().isNull()


class TestImageLightboxDialogFixedSize:
    def test_dialog_size_unchanged_across_images_of_different_dimensions(self):
        small_pixmap = _colored_pixmap("red")  # 10x10, from existing test helper
        big_pixmap = QPixmap(2000, 1500)
        big_pixmap.fill(QColor("blue"))

        images = [Image(name="Small"), Image(name="Big")]
        pixmaps = {images[0].id: small_pixmap, images[1].id: big_pixmap}

        dialog = ImageLightboxDialog(images, 0, load_pixmap=lambda img: pixmaps[img.id])
        size_before = dialog.size()

        dialog._go_next()

        assert dialog.size() == size_before

    def test_first_shown_image_scales_to_initial_frame_not_default_label_size(self):
        # Regression test: a freshly-constructed QLabel that hasn't been
        # shown/laid out yet reports Qt's default widget size, QSize(640, 480)
        # -- NOT (0, 0) -- so _content_area_size() must not rely on the
        # label's reported size to detect "not laid out yet" for the very
        # first image. A 2000x1500 (4:3) pixmap scaled with KeepAspectRatio
        # into the 1200x900 (4:3) initial content area lands exactly at
        # 1200x900; if the bug regresses, it would instead scale to fit
        # Qt's default pre-layout QLabel size of 640x480.
        big_pixmap = QPixmap(2000, 1500)
        big_pixmap.fill(QColor("blue"))
        images = [Image(name="Big")]

        dialog = ImageLightboxDialog(images, 0, load_pixmap=lambda img: big_pixmap)

        scaled = dialog.image_label.pixmap()
        assert scaled.width() == 1200
        assert scaled.height() == 900

    def test_long_title_is_elided(self):
        long_name = "vacation_photo_from_the_summer_trip_final_edited_version_2026_extra_long_suffix"
        images = [Image(name=long_name)]

        dialog = ImageLightboxDialog(images, 0, load_pixmap=lambda img: _colored_pixmap("red"))

        assert dialog.windowTitle() != long_name
        assert len(dialog.windowTitle()) < len(long_name)
