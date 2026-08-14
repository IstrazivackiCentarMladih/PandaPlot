import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.image_thumbnail_tile import build_gallery_tile_icon

_TOKENS = {
    "accent": "#4A56C6",
    "surface_white": "#FFFFFF",
    "text_muted": "#6B7280",
    "border_subtle": "#ECEEF2",
}


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _sample_pixmap() -> QPixmap:
    pixmap = QPixmap(QSize(40, 30))
    pixmap.fill(QColor("blue"))
    return pixmap


class TestBuildGalleryTileIcon:
    def test_image_type_returns_non_null_icon(self):
        icon = build_gallery_tile_icon(_sample_pixmap(), "image", False, _TOKENS)

        assert not icon.isNull()

    def test_album_type_returns_non_null_icon_without_a_pixmap(self):
        icon = build_gallery_tile_icon(None, "album", False, _TOKENS)

        assert not icon.isNull()

    def test_broken_type_returns_non_null_icon_without_a_pixmap(self):
        icon = build_gallery_tile_icon(None, "broken", False, _TOKENS)

        assert not icon.isNull()

    def test_selected_and_unselected_icons_differ(self):
        unselected = build_gallery_tile_icon(_sample_pixmap(), "image", False, _TOKENS)
        selected = build_gallery_tile_icon(_sample_pixmap(), "image", True, _TOKENS)

        unselected_pixmap = unselected.pixmap(QSize(120, 120))
        selected_pixmap = selected.pixmap(QSize(120, 120))
        assert unselected_pixmap.toImage() != selected_pixmap.toImage()

    def test_respects_custom_size(self):
        icon = build_gallery_tile_icon(_sample_pixmap(), "image", False, _TOKENS, size=QSize(64, 64))

        pixmap = icon.pixmap(QSize(64, 64))
        assert pixmap.size() == QSize(64, 64)
