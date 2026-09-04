"""
Tests for note image path resolution and insert-image picker dialog.
"""

import os
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QDialog

from pandaplot.gui.components.tabs.note.note_editor import (
    NoteEditorWidget,
    NotePreviewBrowser,
    get_project_base_dir,
    register_project_image_resources,
)
from pandaplot.gui.dialogs.image.note_image_picker_dialog import NoteImagePickerDialog
from pandaplot.models.events.event_types import ProjectEvents
from pandaplot.models.project.items import Image, ImageGallery, Note
from pandaplot.models.project.project import Project


def create_test_png_bytes(width=10, height=10) -> bytes:
    """Generate valid PNG bytes in memory for testing."""
    from PySide6.QtCore import QBuffer, QIODevice

    img = QImage(width, height, QImage.Format.Format_RGB32)
    img.fill(0xFF0000)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def test_get_project_base_dir(tmp_path):
    app_context = MagicMock()
    project_file = str(tmp_path / "sub" / "my_project.pplot")
    project = Project(name="Test Project")
    project.project_file_path = project_file

    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state

    base_dir = get_project_base_dir(app_context)
    assert base_dir == os.path.dirname(os.path.abspath(project_file))


def test_register_project_image_resources(qapp, tmp_path):
    project_file = str(tmp_path / "my_project.pplot")
    project = Project(name="Test Project")
    project.project_file_path = project_file

    gallery = ImageGallery(name="Gallery 1")
    project.add_item(gallery)

    png_bytes = create_test_png_bytes()
    image = Image(name="sample.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image, parent_id=gallery.id)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state

    doc = QTextDocument()
    base_dir = register_project_image_resources(doc, app_context)

    assert base_dir == str(tmp_path)
    base_url = QUrl.fromLocalFile(str(tmp_path) + "/")

    # Registered by immutable id and by its exact gallery-relative path
    # ("Gallery 1/sample.png") -- never by bare name, which would ambiguously
    # match any other same-named image or an unrelated on-disk file.
    gallery_path = "Gallery 1/sample.png"
    res_path = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl(gallery_path))
    res_resolved = doc.resource(QTextDocument.ResourceType.ImageResource, base_url.resolved(QUrl(gallery_path)))
    res_id = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl(image.id))
    res_bare_name = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl("sample.png"))

    assert res_path is not None and not res_path.isNull()
    assert res_resolved is not None and not res_resolved.isNull()
    assert res_id is not None and not res_id.isNull()
    assert res_bare_name is None


def test_note_preview_browser_load_resource(qapp, tmp_path):
    project = Project(name="Test Project")
    png_bytes = create_test_png_bytes()
    image = Image(name="fig1.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state

    browser = NotePreviewBrowser(app_context=app_context)
    res = browser.loadResource(QTextDocument.ResourceType.ImageResource, QUrl("fig1.png"))

    assert res is not None
    assert isinstance(res, QImage)
    assert not res.isNull()


def test_note_preview_browser_does_not_fuzzy_match_by_stem(qapp, tmp_path):
    """A reference to an unrelated file must not be hijacked by a same-stem
    gallery image (PR #326 review: only exact id/gallery-path should match)."""
    project = Project(name="Test Project")
    png_bytes = create_test_png_bytes()
    image = Image(name="plot.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state

    browser = NotePreviewBrowser(app_context=app_context)
    # Different extension/full name than the gallery image's exact name/id:
    # must not resolve via filename-stem or basename fuzzy matching.
    res = browser.loadResource(QTextDocument.ResourceType.ImageResource, QUrl("assets/plot.jpg"))

    assert res is None or (hasattr(res, "isNull") and res.isNull())


def test_note_preview_browser_prefers_real_file_over_gallery_match(qapp, tmp_path):
    """An existing on-disk file wins over a same-name/id gallery image."""
    real_file = tmp_path / "shared.png"
    real_bytes = create_test_png_bytes(width=5, height=5)
    real_file.write_bytes(real_bytes)

    project = Project(name="Test Project")
    gallery_bytes = create_test_png_bytes(width=50, height=50)
    image = Image(id="shared.png", name="shared.png", storage_mode="copied")
    image.set_bytes(gallery_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state

    browser = NotePreviewBrowser(app_context=app_context)
    res = browser.loadResource(QTextDocument.ResourceType.ImageResource, QUrl.fromLocalFile(str(real_file)))

    # Qt's default loadResource() may hand back either a decoded QImage or
    # the raw file bytes (which QTextDocument decodes itself); either way it
    # must be the 5x5 real file, not the 50x50 gallery image.
    if isinstance(res, QImage):
        loaded = res
    else:
        loaded = QImage()
        loaded.loadFromData(bytes(res))
    assert not loaded.isNull()
    assert loaded.width() == 5 and loaded.height() == 5


def test_note_editor_update_preview_and_event_refresh(qapp, tmp_path):
    project = Project(name="Test Project")
    png_bytes = create_test_png_bytes()
    image = Image(name="plot.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state
    app_context.get_manager.return_value.get_surface_palette.return_value = {}

    note = Note(name="My Note", content="![Plot](plot.png)")
    editor = NoteEditorWidget(app_context=app_context, note=note, parent=None)

    # Switch to preview mode
    editor.set_mode("preview")
    assert editor.stack.currentIndex() == 1

    # Check preview document contains image resource
    doc = editor.preview.document()
    res = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl("plot.png"))
    assert res is not None and not res.isNull()

    # Trigger project item changed event
    with patch.object(editor, "update_preview") as mock_update:
        editor.on_project_item_changed_event({"event": ProjectEvents.PROJECT_ITEM_ADDED})
        mock_update.assert_called_once()


def test_note_editor_export_pdf_registers_resources(qapp, tmp_path):
    project = Project(name="Test Project")
    png_bytes = create_test_png_bytes()
    image = Image(name="chart.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state
    app_context.get_manager.return_value.get_surface_palette.return_value = {}

    pdf_file = str(tmp_path / "output.pdf")
    note = Note(name="PDF Note", content="![Chart](chart.png)")
    editor = NoteEditorWidget(app_context=app_context, note=note, parent=None)

    with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(pdf_file, "PDF Files (*.pdf)")):
        editor.export_pdf()

    assert os.path.exists(pdf_file)


def test_note_image_picker_dialog_tree_and_selection(qapp):
    project = Project(name="Test Project")
    gallery = ImageGallery(name="Album 1")
    project.add_item(gallery)

    png_bytes = create_test_png_bytes()
    image = Image(name="photo1.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image, parent_id=gallery.id)

    app_context = MagicMock()
    app_context.get_manager.return_value.get_design_tokens.return_value = {}

    dialog = NoteImagePickerDialog(app_context=app_context, project=project)
    dialog.show()

    assert not dialog.tree.isHidden()
    assert dialog.empty_label.isHidden()

    # Select image item
    items = dialog.tree.findItems(
        "photo1.png",
        Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchRecursive,
    )
    assert len(items) == 1
    items[0].setSelected(True)

    assert dialog.ok_button.isEnabled()
    dialog._on_ok_clicked()
    assert dialog.get_selected_image() == image


def test_note_image_picker_dialog_empty_state(qapp):
    project = Project(name="Empty Project")
    app_context = MagicMock()

    dialog = NoteImagePickerDialog(app_context=app_context, project=project)
    dialog.show()

    assert dialog.tree.isHidden()
    assert not dialog.empty_label.isHidden()
    assert not dialog.ok_button.isEnabled()


def test_note_editor_insert_image_action(qapp):
    project = Project(name="Test Project")
    png_bytes = create_test_png_bytes()
    image = Image(name="my_diagram.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state
    app_context.get_manager.return_value.get_surface_palette.return_value = {}

    note = Note(name="Note 1", content="")
    editor = NoteEditorWidget(app_context=app_context, note=note, parent=None)

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog.get_selected_image.return_value = image

    with patch("pandaplot.gui.components.tabs.note.note_editor.NoteImagePickerDialog", return_value=mock_dialog):
        editor.insert_image_from_picker()

    # References by immutable id (not the mutable/duplicatable name), with
    # the name kept as alt text.
    assert editor.text_edit.toPlainText() == f"![my_diagram.png]({image.id})"


def test_note_editor_insert_image_applies_default_width_cap(qapp):
    """A gallery image wider than the default cap gets a `=WIDTHx` modifier."""
    project = Project(name="Test Project")
    png_bytes = create_test_png_bytes()
    image = Image(name="wide.png", storage_mode="copied", width=1200, height=800)
    image.set_bytes(png_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state
    app_context.get_manager.return_value.get_surface_palette.return_value = {}

    note = Note(name="Note 1", content="")
    editor = NoteEditorWidget(app_context=app_context, note=note, parent=None)

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog.get_selected_image.return_value = image

    with patch("pandaplot.gui.components.tabs.note.note_editor.NoteImagePickerDialog", return_value=mock_dialog):
        editor.insert_image_from_picker()

    assert editor.text_edit.toPlainText() == f"![wide.png]({image.id} =500x)"


def test_note_editor_insert_image_refreshes_preview_only_mode(qapp):
    """Inserting while preview-only (no live textChanged connection) still refreshes."""
    project = Project(name="Test Project")
    png_bytes = create_test_png_bytes()
    image = Image(name="my_diagram.png", storage_mode="copied")
    image.set_bytes(png_bytes)
    project.add_item(image)

    app_context = MagicMock()
    app_state = MagicMock()
    app_state.current_project = project
    app_context.get_app_state.return_value = app_state
    app_context.get_manager.return_value.get_surface_palette.return_value = {}

    note = Note(name="Note 1", content="")
    editor = NoteEditorWidget(app_context=app_context, note=note, parent=None)
    editor.set_mode("preview")

    mock_dialog = MagicMock()
    mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog.get_selected_image.return_value = image

    with patch("pandaplot.gui.components.tabs.note.note_editor.NoteImagePickerDialog", return_value=mock_dialog):
        with patch.object(editor, "update_preview") as mock_update:
            editor.insert_image_from_picker()
            mock_update.assert_called_once()
