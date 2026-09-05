from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

from pandaplot.commands.base_command import CommandResult
from pandaplot.commands.project.image.create_image_gallery_command import CreateImageGalleryCommand
from pandaplot.commands.project.image.edit_image_command import EditImageCommand
from pandaplot.models.project.items import Image


def _make_png_bytes(width: int = 10, height: int = 10) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img = QImage(width, height, QImage.Format.Format_RGB32)
    img.fill(0xFF0000)
    img.save(buffer, "PNG")
    return bytes(buffer.data())


class TestEditImageCommand:
    def test_execute_and_undo_redo(self, app_context_with_project):
        # Create gallery and image
        gallery_cmd = CreateImageGalleryCommand(app_context_with_project, gallery_name="Gallery")
        gallery_cmd.execute()
        gallery_id = gallery_cmd.created_gallery_id

        project = app_context_with_project.get_app_state().current_project

        old_data = _make_png_bytes(20, 20)
        image = Image(id="img-edit-1", name="Original", width=20, height=20, storage_mode="external")
        image.set_bytes(old_data)
        project.add_item(image, parent_id=gallery_id)

        new_data = _make_png_bytes(10, 15)
        edit_cmd = EditImageCommand(
            app_context_with_project, image_id="img-edit-1",
            new_bytes=new_data, new_width=10, new_height=15, new_ext="png"
        )

        # Execute
        res = edit_cmd.execute()
        assert res is CommandResult.SUCCESS
        assert image.width == 10
        assert image.height == 15
        assert image.storage_mode == "copied"
        assert image.get_bytes() == new_data
        assert image.size_bytes == len(new_data)

        # Undo
        undo_res = edit_cmd.undo()
        assert undo_res is CommandResult.SUCCESS
        assert image.width == 20
        assert image.height == 20
        assert image.storage_mode == "external"
        assert image.get_bytes() == old_data

        # Redo
        redo_res = edit_cmd.redo()
        assert redo_res is CommandResult.SUCCESS
        assert image.width == 10
        assert image.height == 15
        assert image.get_bytes() == new_data
