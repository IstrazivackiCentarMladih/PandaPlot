"""
Dialog for basic image operations: crop, rotate, and resize.
"""

from typing import Optional, override

from PySide6.QtCore import QBuffer, QIODevice, QRect, QSize, Qt
from PySide6.QtGui import QImage, QPixmap, QTransform
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.components.common.p_button import PButton
from pandaplot.gui.core.widget_extension import PDialog
from pandaplot.models.project.items import Image
from pandaplot.models.state.app_context import AppContext

_PREVIEW_MAX_SIZE = QSize(700, 500)


class ImageEditorDialog(PDialog):
    """
    Dialog providing crop, rotate, and resize tools with live preview.
    """

    def __init__(self, app_context: AppContext, image: Image,
                 image_bytes: bytes, parent: Optional[QWidget] = None):
        super().__init__(app_context=app_context, parent=parent)
        self.image_model = image
        self.original_bytes = image_bytes
        self.image_ext = (image.image_ext or "png").lower()

        # Load working QImage from original bytes
        self.original_qimage = QImage()
        self.original_qimage.loadFromData(self.original_bytes)
        self.working_qimage = QImage(self.original_qimage)

        self.aspect_ratio = (
            self.working_qimage.width() / self.working_qimage.height()
            if self.working_qimage.height() > 0 else 1.0
        )
        self._updating_resize_spinboxes = False

        self._initialize()
        self._update_preview()
        self._sync_control_values()

    @override
    def _init_ui(self):
        self.setWindowTitle(f"Edit Image - {self.image_model.name}")
        self.resize(1000, 650)

        main_layout = QHBoxLayout(self)

        # Left side: Image preview area
        preview_container = QVBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.preview_label)
        scroll_area.setWidgetResizable(True)
        preview_container.addWidget(scroll_area, stretch=1)

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_container.addWidget(self.info_label)

        main_layout.addLayout(preview_container, stretch=2)

        # Right side: Control panel
        controls_layout = QVBoxLayout()

        # --- Rotate Box ---
        rotate_group = QGroupBox("Rotate")
        rotate_layout = QHBoxLayout(rotate_group)

        self.btn_rotate_ccw = PButton("↺ 90°", role="secondary", on_click=lambda: self._rotate(-90))
        self.btn_rotate_cw = PButton("↻ 90°", role="secondary", on_click=lambda: self._rotate(90))
        self.btn_rotate_180 = PButton("180°", role="secondary", on_click=lambda: self._rotate(180))

        rotate_layout.addWidget(self.btn_rotate_ccw)
        rotate_layout.addWidget(self.btn_rotate_cw)
        rotate_layout.addWidget(self.btn_rotate_180)
        controls_layout.addWidget(rotate_group)

        # --- Resize Box ---
        resize_group = QGroupBox("Resize")
        resize_layout = QVBoxLayout(resize_group)

        size_inputs_layout = QHBoxLayout()
        size_inputs_layout.addWidget(QLabel("Width:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 20000)
        size_inputs_layout.addWidget(self.spin_width)

        size_inputs_layout.addWidget(QLabel("Height:"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 20000)
        size_inputs_layout.addWidget(self.spin_height)

        resize_layout.addLayout(size_inputs_layout)

        self.chk_keep_aspect = QCheckBox("Maintain aspect ratio")
        self.chk_keep_aspect.setChecked(True)
        resize_layout.addWidget(self.chk_keep_aspect)

        self.btn_apply_resize = PButton("Apply Resize", role="secondary", on_click=self._apply_resize)
        resize_layout.addWidget(self.btn_apply_resize)

        controls_layout.addWidget(resize_group)

        # --- Crop Box ---
        crop_group = QGroupBox("Crop")
        crop_layout = QVBoxLayout(crop_group)

        crop_grid = QHBoxLayout()
        crop_grid.addWidget(QLabel("X:"))
        self.spin_crop_x = QSpinBox()
        self.spin_crop_x.setRange(0, 20000)
        crop_grid.addWidget(self.spin_crop_x)

        crop_grid.addWidget(QLabel("Y:"))
        self.spin_crop_y = QSpinBox()
        self.spin_crop_y.setRange(0, 20000)
        crop_grid.addWidget(self.spin_crop_y)

        crop_layout.addLayout(crop_grid)

        crop_dim_grid = QHBoxLayout()
        crop_dim_grid.addWidget(QLabel("W:"))
        self.spin_crop_w = QSpinBox()
        self.spin_crop_w.setRange(1, 20000)
        crop_dim_grid.addWidget(self.spin_crop_w)

        crop_dim_grid.addWidget(QLabel("H:"))
        self.spin_crop_h = QSpinBox()
        self.spin_crop_h.setRange(1, 20000)
        crop_dim_grid.addWidget(self.spin_crop_h)

        crop_layout.addLayout(crop_dim_grid)

        self.btn_apply_crop = PButton("Apply Crop", role="secondary", on_click=self._apply_crop)
        crop_layout.addWidget(self.btn_apply_crop)

        controls_layout.addWidget(crop_group)

        # --- Revert & Dialog Action Buttons ---
        controls_layout.addStretch(1)

        self.btn_reset = PButton("Reset All Edits", role="secondary", on_click=self._reset_edits)
        controls_layout.addWidget(self.btn_reset)

        btn_box = QHBoxLayout()
        self.btn_cancel = PButton("Cancel", role="secondary", on_click=self.reject)
        self.btn_apply = PButton("Save Changes", role="primary", on_click=self.accept)
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_apply)

        controls_layout.addLayout(btn_box)

        main_layout.addLayout(controls_layout, stretch=1)

        # Connect signals
        self.spin_width.valueChanged.connect(self._on_width_changed)
        self.spin_height.valueChanged.connect(self._on_height_changed)

    @override
    def _apply_theme(self):
        pass

    def _sync_control_values(self):
        w = self.working_qimage.width()
        h = self.working_qimage.height()
        self.aspect_ratio = w / h if h > 0 else 1.0

        self._updating_resize_spinboxes = True
        self.spin_width.setValue(w)
        self.spin_height.setValue(h)
        self._updating_resize_spinboxes = False

        self.spin_crop_x.setRange(0, max(0, w - 1))
        self.spin_crop_y.setRange(0, max(0, h - 1))
        self.spin_crop_w.setRange(1, w)
        self.spin_crop_h.setRange(1, h)

        self.spin_crop_x.setValue(0)
        self.spin_crop_y.setValue(0)
        self.spin_crop_w.setValue(w)
        self.spin_crop_h.setValue(h)

    def _update_preview(self):
        pixmap = QPixmap.fromImage(self.working_qimage)
        if pixmap.isNull():
            self.preview_label.setText("Failed to display image")
            return

        scaled = pixmap.scaled(
            _PREVIEW_MAX_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)
        self.info_label.setText(
            f"Current Size: {self.working_qimage.width()} × {self.working_qimage.height()} px"
        )

    def _on_width_changed(self, new_width: int):
        if self._updating_resize_spinboxes or not self.chk_keep_aspect.isChecked():
            return
        if self.aspect_ratio > 0:
            new_height = max(1, round(new_width / self.aspect_ratio))
            self._updating_resize_spinboxes = True
            self.spin_height.setValue(new_height)
            self._updating_resize_spinboxes = False

    def _on_height_changed(self, new_height: int):
        if self._updating_resize_spinboxes or not self.chk_keep_aspect.isChecked():
            return
        if self.aspect_ratio > 0:
            new_width = max(1, round(new_height * self.aspect_ratio))
            self._updating_resize_spinboxes = True
            self.spin_width.setValue(new_width)
            self._updating_resize_spinboxes = False

    def _rotate(self, degrees: int):
        transform = QTransform().rotate(degrees)
        self.working_qimage = self.working_qimage.transformed(
            transform, Qt.TransformationMode.SmoothTransformation
        )
        self._sync_control_values()
        self._update_preview()

    def _apply_resize(self):
        target_w = self.spin_width.value()
        target_h = self.spin_height.value()
        if target_w <= 0 or target_h <= 0:
            return

        self.working_qimage = self.working_qimage.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._sync_control_values()
        self._update_preview()

    def _apply_crop(self):
        x = self.spin_crop_x.value()
        y = self.spin_crop_y.value()
        w = self.spin_crop_w.value()
        h = self.spin_crop_h.value()

        img_w = self.working_qimage.width()
        img_h = self.working_qimage.height()

        crop_rect = QRect(x, y, w, h).intersected(QRect(0, 0, img_w, img_h))
        if crop_rect.isEmpty():
            return

        self.working_qimage = self.working_qimage.copy(crop_rect)
        self._sync_control_values()
        self._update_preview()

    def _reset_edits(self):
        self.working_qimage = QImage(self.original_qimage)
        self._sync_control_values()
        self._update_preview()

    def get_result_bytes(self) -> bytes:
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        fmt = "JPEG" if self.image_ext in ("jpg", "jpeg") else "PNG"
        self.working_qimage.save(buffer, fmt)
        return bytes(buffer.data())

    def get_result_width(self) -> int:
        return self.working_qimage.width()

    def get_result_height(self) -> int:
        return self.working_qimage.height()

    def get_result_ext(self) -> str:
        return "jpg" if self.image_ext in ("jpg", "jpeg") else "png"
