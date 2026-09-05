from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

from pandaplot.app import build_app_context
from pandaplot.gui.dialogs.image.image_editor_dialog import ImageEditorDialog
from pandaplot.models.project.items import Image


def _make_test_image_bytes(width: int = 100, height: int = 80) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img = QImage(width, height, QImage.Format.Format_RGB32)
    img.fill(0x00FF00)
    img.save(buffer, "PNG")
    return bytes(buffer.data())


class TestImageEditorDialog:
    def test_dialog_init_and_operations(self, qapp):
        app_context = build_app_context()
        orig_bytes = _make_test_image_bytes(100, 80)
        image = Image(id="test-img", name="Test Photo", width=100, height=80, image_ext="png")

        dialog = ImageEditorDialog(app_context, image, orig_bytes)

        assert dialog.spin_width.value() == 100
        assert dialog.spin_height.value() == 80

        # Rotate 90
        dialog._rotate(90)
        assert dialog.working_qimage.width() == 80
        assert dialog.working_qimage.height() == 100

        # Crop
        dialog.spin_crop_x.setValue(10)
        dialog.spin_crop_y.setValue(10)
        dialog.spin_crop_w.setValue(40)
        dialog.spin_crop_h.setValue(30)
        dialog._apply_crop()

        assert dialog.working_qimage.width() == 40
        assert dialog.working_qimage.height() == 30

        # Resize
        dialog.chk_keep_aspect.setChecked(False)
        dialog.spin_width.setValue(200)
        dialog.spin_height.setValue(150)
        dialog._apply_resize()

        assert dialog.working_qimage.width() == 200
        assert dialog.working_qimage.height() == 150

        # Reset
        dialog._reset_edits()
        assert dialog.working_qimage.width() == 100
        assert dialog.working_qimage.height() == 80

        res_bytes = dialog.get_result_bytes()
        assert isinstance(res_bytes, bytes)
        assert len(res_bytes) > 0


class TestImageEditorDialogFormatPreservation:
    def test_preserves_supported_bmp_extension(self, qapp):
        app_context = build_app_context()
        image = Image(id="fmt-bmp", name="Photo", width=10, height=10, image_ext="bmp")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(10, 10))

        assert dialog.get_result_ext() == "bmp"
        assert len(dialog.get_result_bytes()) > 0

    def test_falls_back_to_png_for_unsupported_extension(self, qapp, monkeypatch):
        from PySide6.QtGui import QImageWriter

        monkeypatch.setattr(
            QImageWriter, "supportedImageFormats",
            staticmethod(lambda: [b"PNG", b"JPEG", b"BMP"]),
        )
        app_context = build_app_context()
        image = Image(id="fmt-webp", name="Photo", width=10, height=10, image_ext="webp")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(10, 10))

        assert dialog.get_result_ext() == "png"
        assert len(dialog.get_result_bytes()) > 0


class TestImageEditorDialogCropClamping:
    def test_out_of_bounds_crop_spinbox_values_are_clamped_back(self, qapp):
        app_context = build_app_context()
        image = Image(id="clamp-1", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog.spin_crop_x.setValue(90)
        dialog.spin_crop_w.setValue(50)  # would extend to x=140, past the 100px-wide image

        assert dialog.spin_crop_w.value() == 10  # clamped to what actually fits: 100 - 90
        assert dialog.spin_crop_x.value() == 90

    def test_sync_control_values_does_not_trigger_reentrant_crop_clamping(self, qapp):
        app_context = build_app_context()
        image = Image(id="clamp-2", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        # Leave the crop spinboxes holding a rect (x=10, y=10, w=40, h=30) that is
        # only valid for the *current* 100x80 image. When _apply_crop() shrinks the
        # working image down to 40x30 and calls _sync_control_values(), the method
        # writes the new full-image rect one field at a time (x, y, w, h). Without
        # the re-entrancy guard, the stale leftover values (y=10, h=30) momentarily
        # describe a rect (0, 10, 40, 30) that overflows the new 40x30 image,
        # spuriously triggering _on_crop_spinbox_changed's clamp-and-write-back.
        dialog.spin_crop_x.setValue(10)
        dialog.spin_crop_y.setValue(10)
        dialog.spin_crop_w.setValue(40)
        dialog.spin_crop_h.setValue(30)

        write_calls: list[object] = []
        original_write = dialog._write_crop_spinboxes

        def spy(rect):
            write_calls.append(rect)
            return original_write(rect)

        dialog._write_crop_spinboxes = spy

        dialog._apply_crop()

        assert write_calls == []  # no reentrant clamp write-back during the sync
        assert dialog.spin_crop_x.value() == 0
        assert dialog.spin_crop_y.value() == 0
        assert dialog.spin_crop_w.value() == 40
        assert dialog.spin_crop_h.value() == 30
