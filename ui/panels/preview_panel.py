import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap


class PreviewPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #13141F;")
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        title = QLabel("Preview")
        title.setStyleSheet("color: #7F849C; font-size: 11px; font-weight: bold;")
        layout.addWidget(title)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: #1A1B26; border-radius: 6px; color: #45475A;")
        self._label.setText("Sin imagen")
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._label)

        self._info = QLabel("")
        self._info.setStyleSheet("color: #6C7086; font-size: 10px;")
        self._info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info)

    def show_image(self, img: np.ndarray):
        if img is None:
            return
        import cv2
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        h, w, ch = img.shape
        bytes_per_line = ch * w
        qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        label_size = self._label.size()
        scaled = pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._label.setPixmap(scaled)
        self._info.setText(f"{w} × {h} px")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reescala la imagen al redimensionar la ventana
        if self._label.pixmap() and not self._label.pixmap().isNull():
            scaled = self._label.pixmap().scaled(
                self._label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._label.setPixmap(scaled)
