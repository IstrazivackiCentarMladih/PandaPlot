import pytest
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
        from PySide6.QtCore import QRect

        app_context = build_app_context()
        image = Image(id="clamp-2", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        # Leave the crop spinboxes holding a rect (x=10, y=10, w=40, h=30) that is
        # only valid for the *current* 100x80 image. When _apply_crop() shrinks the
        # working image down to 40x30 and calls _sync_control_values(), the ranges
        # are updated (spin_crop_w/h's max drops to 40/30) before the values are
        # rewritten. Without the re-entrancy guard around that setRange step, the
        # stale leftover values (x=10, w=40 momentarily exceeds the new 40-wide
        # range) get silently clamped by setRange() itself, which emits
        # valueChanged and would re-enter _on_crop_spinbox_changed with a stale,
        # partially-updated rect -- producing an extra, spurious write-back before
        # the one legitimate write _sync_control_values() itself makes at the end.
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

        # Exactly the one legitimate write _sync_control_values() makes at the
        # end, with the correct final rect -- no earlier, spurious reentrant
        # write-back triggered by setRange() clamping stale values.
        assert write_calls == [QRect(0, 0, 40, 30)]
        assert dialog.spin_crop_x.value() == 0
        assert dialog.spin_crop_y.value() == 0
        assert dialog.spin_crop_w.value() == 40
        assert dialog.spin_crop_h.value() == 30


class TestImageEditorDialogCropCanvasSync:
    def test_dragging_canvas_rect_updates_spinboxes(self, qapp):
        from PySide6.QtCore import QRect

        app_context = build_app_context()
        image = Image(id="sync-1", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog.crop_canvas.cropRectChanged.emit(QRect(10, 5, 40, 30))

        assert dialog.spin_crop_x.value() == 10
        assert dialog.spin_crop_y.value() == 5
        assert dialog.spin_crop_w.value() == 40
        assert dialog.spin_crop_h.value() == 30

    def test_editing_spinbox_updates_canvas_rect(self, qapp):
        from PySide6.QtCore import QRect

        app_context = build_app_context()
        image = Image(id="sync-2", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog.spin_crop_x.setValue(15)
        dialog.spin_crop_w.setValue(20)

        assert dialog.crop_canvas.crop_rect() == QRect(15, 0, 20, 80)

    def test_rotate_resets_canvas_crop_rect_to_new_full_bounds(self, qapp):
        from PySide6.QtCore import QRect

        app_context = build_app_context()
        image = Image(id="sync-3", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog._rotate(90)

        assert dialog.crop_canvas.crop_rect() == QRect(0, 0, 80, 100)

    def test_aspect_preset_locks_canvas_and_reflows_current_rect(self, qapp):
        app_context = build_app_context()
        image = Image(id="sync-4", name="Photo", width=200, height=200, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(200, 200))
        dialog.spin_crop_w.setValue(100)
        dialog.spin_crop_h.setValue(100)

        index = dialog.aspect_combo.findText("1:1")
        dialog.aspect_combo.setCurrentIndex(index)

        assert dialog.crop_canvas._aspect_lock == pytest.approx(1.0)

        index_16_9 = dialog.aspect_combo.findText("16:9")
        dialog.aspect_combo.setCurrentIndex(index_16_9)

        assert dialog.crop_canvas._aspect_lock == pytest.approx(16 / 9)
        assert dialog.spin_crop_h.value() == round(dialog.spin_crop_w.value() / (16 / 9))


class TestImageEditorDialogUndoRedo:
    def test_undo_reverts_last_rotate(self, qapp):
        app_context = build_app_context()
        image = Image(id="undo-1", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog._rotate(90)
        assert dialog.working_qimage.width() == 80

        dialog._undo()

        assert dialog.working_qimage.width() == 100
        assert dialog.working_qimage.height() == 80

    def test_redo_reapplies_undone_rotate(self, qapp):
        app_context = build_app_context()
        image = Image(id="undo-2", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog._rotate(90)
        dialog._undo()
        dialog._redo()

        assert dialog.working_qimage.width() == 80
        assert dialog.working_qimage.height() == 100

    def test_new_op_after_undo_clears_redo_stack(self, qapp):
        app_context = build_app_context()
        image = Image(id="undo-3", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog._rotate(90)
        dialog._undo()
        dialog._rotate(180)

        assert dialog.btn_redo.isEnabled() is False

    def test_undo_button_disabled_with_empty_stack(self, qapp):
        app_context = build_app_context()
        image = Image(id="undo-4", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        assert dialog.btn_undo.isEnabled() is False

        dialog._rotate(90)

        assert dialog.btn_undo.isEnabled() is True

    def test_reset_all_edits_is_itself_undoable(self, qapp):
        app_context = build_app_context()
        image = Image(id="undo-5", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog._rotate(90)
        dialog._reset_edits()
        assert dialog.working_qimage.width() == 100

        dialog._undo()

        assert dialog.working_qimage.width() == 80
        assert dialog.working_qimage.height() == 100


class TestImageEditorDialogAspectLockSurvivesCommitsAndRotation:
    def test_lock_survives_a_commit_that_resets_canvas_to_full_bounds(self, qapp):
        """Finding #3a: every commit calls _sync_control_values(), which
        resets the canvas rect to full bounds via set_image() -- an active
        aspect lock must be reflowed back onto that reset rect rather than
        silently dropped."""
        from PySide6.QtCore import QRect

        app_context = build_app_context()
        image = Image(id="lock-1", name="Photo", width=200, height=100, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(200, 100))

        index = dialog.aspect_combo.findText("1:1")
        dialog.aspect_combo.setCurrentIndex(index)
        assert dialog.crop_canvas.aspect_lock() == pytest.approx(1.0)

        dialog._apply_resize()  # a resize with the same 200x100 size is a no-op commit

        rect = dialog.crop_canvas.crop_rect()
        assert rect.width() / rect.height() == pytest.approx(1.0)
        assert rect != QRect(0, 0, 200, 100)  # actually reflowed, not just full (non-square) bounds

    def test_original_lock_re_resolves_to_new_ratio_after_rotate(self, qapp):
        """Finding #3b: "Original" must mean "the current working image's
        ratio" even after a rotate changes that ratio, not the ratio at the
        moment "Original" was selected."""
        app_context = build_app_context()
        image = Image(id="lock-2", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        index = dialog.aspect_combo.findText("Original")
        dialog.aspect_combo.setCurrentIndex(index)
        assert dialog.crop_canvas.aspect_lock() == pytest.approx(100 / 80)

        dialog._rotate(90)  # working image is now 80x100

        assert dialog.crop_canvas.aspect_lock() == pytest.approx(80 / 100)

    def test_spinbox_edit_while_locked_reflows_to_lock(self, qapp):
        """Finding #3c: editing a crop spinbox while a lock is active must
        reflow the result back onto the lock, not just clamp to bounds."""
        app_context = build_app_context()
        image = Image(id="lock-3", name="Photo", width=200, height=200, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(200, 200))

        index = dialog.aspect_combo.findText("1:1")
        dialog.aspect_combo.setCurrentIndex(index)

        # Editing height alone to a value that would violate the 1:1 lock.
        dialog.spin_crop_h.setValue(50)

        rect = dialog.crop_canvas.crop_rect()
        assert rect.width() / rect.height() == pytest.approx(1.0)
        assert dialog.spin_crop_w.value() == dialog.spin_crop_h.value()


class TestImageEditorDialogNoOpCropSkipsUndoAndCopy:
    def test_apply_crop_with_full_bounds_rect_is_a_no_op(self, qapp):
        """Finding #6: a crop rect equal to the current full image bounds
        must not push an undo snapshot or copy the image."""
        app_context = build_app_context()
        image = Image(id="noop-crop", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        original_qimage = dialog.working_qimage
        assert dialog.btn_undo.isEnabled() is False

        dialog._apply_crop()  # spinboxes already describe the full image

        assert dialog.btn_undo.isEnabled() is False
        assert dialog.working_qimage is original_qimage


class TestImageEditorDialogGetResultBytesSaveFailure:
    def test_get_result_bytes_raises_when_save_fails(self, qapp, monkeypatch):
        """Finding #13: a failed QImage.save() must not silently yield empty
        bytes -- that would get persisted as the image's new content."""
        app_context = build_app_context()
        image = Image(id="save-fail", name="Photo", width=10, height=10, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(10, 10))

        monkeypatch.setattr(QImage, "save", lambda self, *args, **kwargs: False)

        with pytest.raises(Exception):
            dialog.get_result_bytes()


class TestImageEditorDialogRedoShortcut:
    def test_ctrl_shift_z_also_triggers_redo(self, qapp):
        """Finding #11: Ctrl+Shift+Z must work as an additional redo binding
        alongside Ctrl+Y."""
        from PySide6.QtGui import QKeySequence, QShortcut

        app_context = build_app_context()
        image = Image(id="redo-shortcut", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        shortcuts = dialog.findChildren(QShortcut)
        sequences = [s.key() for s in shortcuts]
        assert QKeySequence("Ctrl+Shift+Z") in sequences


class TestImageEditorDialogEndToEndFlow:
    def test_full_crop_lock_rotate_undo_export_flow(self, qapp):
        """Finding #17/#18/#19: a realistic full sequence through the
        dialog -- set a crop rect via the canvas, lock an aspect ratio,
        rotate, undo, then export -- asserting sane state at each step.
        This is the kind of test that would have directly caught findings
        #2 and #3 (aspect lock silently violated at the image boundary and
        after a commit)."""
        from PySide6.QtCore import QRect

        app_context = build_app_context()
        image = Image(id="e2e-1", name="Photo", width=200, height=100, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(200, 100))

        # 1. Drag/set a crop rect directly on the canvas (as a real drag
        # would, via the cropRectChanged signal the canvas emits).
        dialog.crop_canvas.cropRectChanged.emit(QRect(10, 10, 150, 70))
        dialog.crop_canvas.set_crop_rect(QRect(10, 10, 150, 70))
        assert dialog.crop_canvas.crop_rect() == QRect(10, 10, 150, 70)
        assert dialog.spin_crop_w.value() == 150
        assert dialog.spin_crop_h.value() == 70

        # 2. Lock an aspect ratio -- reflows the current rect to match.
        index = dialog.aspect_combo.findText("1:1")
        dialog.aspect_combo.setCurrentIndex(index)
        locked_rect = dialog.crop_canvas.crop_rect()
        assert locked_rect.width() == locked_rect.height()

        # 3. Rotate -- the canvas resets to the new full bounds, but the
        #    lock (still active) must be reflowed onto it, and stay a valid
        #    ratio for the new orientation too (finding #3a).
        dialog._rotate(90)
        assert dialog.working_qimage.width() == 100
        assert dialog.working_qimage.height() == 200
        post_rotate_rect = dialog.crop_canvas.crop_rect()
        assert post_rotate_rect.width() == post_rotate_rect.height()
        assert post_rotate_rect.width() <= 100
        assert post_rotate_rect.height() <= 200

        # 4. Undo the rotate -- canvas must reflect the restored image's
        #    full bounds (finding #18), not stale post-rotate bounds.
        dialog._undo()
        assert dialog.working_qimage.width() == 200
        assert dialog.working_qimage.height() == 100
        undone_rect = dialog.crop_canvas.crop_rect()
        assert undone_rect.width() <= 200
        assert undone_rect.height() <= 100

        # 5. Export -- sane, non-empty result reflecting the current image.
        result_bytes = dialog.get_result_bytes()
        assert isinstance(result_bytes, bytes)
        assert len(result_bytes) > 0
        assert dialog.get_result_width() == 200
        assert dialog.get_result_height() == 100


class TestImageEditorDialogUndoRestoresCanvasBounds:
    def test_undo_after_crop_restores_canvas_to_pre_crop_full_bounds(self, qapp):
        """Finding #18: after undo, crop_canvas.crop_rect() must reflect the
        restored image's full bounds, not stale bounds from the undone
        (cropped) state."""
        from PySide6.QtCore import QRect

        app_context = build_app_context()
        image = Image(id="undo-canvas-1", name="Photo", width=100, height=80, image_ext="png")
        dialog = ImageEditorDialog(app_context, image, _make_test_image_bytes(100, 80))

        dialog.spin_crop_x.setValue(10)
        dialog.spin_crop_y.setValue(10)
        dialog.spin_crop_w.setValue(40)
        dialog.spin_crop_h.setValue(30)
        dialog._apply_crop()
        assert dialog.crop_canvas.crop_rect() == QRect(0, 0, 40, 30)

        dialog._undo()

        assert dialog.working_qimage.width() == 100
        assert dialog.working_qimage.height() == 80
        assert dialog.crop_canvas.crop_rect() == QRect(0, 0, 100, 80)
