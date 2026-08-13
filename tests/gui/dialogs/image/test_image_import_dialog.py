"""Tests for ImageImportDialog."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.image.image_import_dialog import ImageImportDialog
from pandaplot.models.state.app_context import AppContext


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def app_context():
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    return ctx


class TestImageImportDialog:
    def test_defaults(self, app_context):
        dialog = ImageImportDialog(app_context)

        assert dialog.get_copy_into_project() is True
        assert dialog.get_sources() == []

    def test_url_mode_returns_entered_url_as_single_source(self, app_context):
        dialog = ImageImportDialog(app_context)

        dialog.url_radio.setChecked(True)
        dialog.url_edit.setText("https://example.com/pic.png")

        assert dialog.get_sources() == ["https://example.com/pic.png"]

    def test_files_mode_returns_selected_paths(self, app_context, tmp_path):
        dialog = ImageImportDialog(app_context)
        fake_paths = [str(tmp_path / "a.png"), str(tmp_path / "b.png")]

        dialog._set_selected_files(fake_paths)

        assert dialog.get_sources() == fake_paths

    def test_import_button_disabled_when_no_source_selected(self, app_context):
        dialog = ImageImportDialog(app_context)

        assert dialog.import_button.isEnabled() is False

        dialog._set_selected_files(["/tmp/a.png"])

        assert dialog.import_button.isEnabled() is True

    def test_unchecking_copy_checkbox_sets_external_mode(self, app_context):
        dialog = ImageImportDialog(app_context)

        dialog.copy_checkbox.setChecked(False)

        assert dialog.get_copy_into_project() is False
