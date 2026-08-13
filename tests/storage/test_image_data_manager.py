import io
from zipfile import ZipFile

from pandaplot.models.project.items.image import Image
from pandaplot.storage.image_data_manager import ImageDataManager


def _round_trip(image: Image) -> Image:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zf:
        ImageDataManager().save(image, zf, "items/test-image")

    buffer.seek(0)
    with ZipFile(buffer, "r") as zf:
        return ImageDataManager().load(Image, zf, "items/test-image")


class TestImageDataManagerCopied:
    def test_round_trip_stores_bytes_and_metadata(self):
        image = Image(id="img-1", name="Cat", storage_mode="copied", image_ext="png",
                       width=64, height=32, source_file="/tmp/cat.png")
        image.set_bytes(b"fake-png-bytes")

        loaded = _round_trip(image)

        assert loaded.id == "img-1"
        assert loaded.name == "Cat"
        assert loaded.storage_mode == "copied"
        assert loaded.image_ext == "png"
        assert loaded.width == 64
        assert loaded.height == 32
        assert loaded.get_bytes() == b"fake-png-bytes"

    def test_zip_contains_blob_entry(self):
        image = Image(id="img-2", name="Dog", storage_mode="copied", image_ext="jpg")
        image.set_bytes(b"jpeg-bytes")

        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as zf:
            ImageDataManager().save(image, zf, "items/img-2")
            names = zf.namelist()

        assert "items/img-2.jpg" in names
        assert "items/img-2.json" in names


class TestImageDataManagerExternal:
    def test_round_trip_stores_only_metadata(self):
        image = Image(id="img-3", name="Linked", storage_mode="external",
                       source_file="https://example.com/pic.png", image_ext="png",
                       width=10, height=10)

        loaded = _round_trip(image)

        assert loaded.storage_mode == "external"
        assert loaded.source_file == "https://example.com/pic.png"
        assert loaded.get_bytes() is None

    def test_zip_contains_no_blob_entry(self):
        image = Image(id="img-4", name="Linked", storage_mode="external",
                       source_file="/tmp/pic.png", image_ext="png")

        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as zf:
            ImageDataManager().save(image, zf, "items/img-4")
            names = zf.namelist()

        assert names == ["items/img-4.json"]


class TestImageRegisteredInFactory:
    def test_image_and_gallery_types_are_registered(self):
        from pandaplot.app import create_project_data_manager
        from pandaplot.models.project.items import Image, ImageGallery

        manager = create_project_data_manager()
        factory = manager.data_factory

        assert factory.resolve_item_class("image") is Image
        assert factory.resolve_item_class("imagegallery") is ImageGallery
