import numpy as np
import cv2
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

        self._original_pixmap: QPixmap | None = None

    def show_image(self, img: np.ndarray):
        if img is None:
            print("[PreviewPanel] show_image called with None")
            return

        if not isinstance(img, np.ndarray):
            print(f"[PreviewPanel] Invalid image type: {type(img)}")
            self.clear()
            return

        if img.size == 0:
            print("[PreviewPanel] Image has no data")
            self.clear()
            return

        try:
            # Convertir a RGB
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            elif len(img.shape) == 3 and img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            elif len(img.shape) == 3 and img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            else:
                print(f"[PreviewPanel] Unsupported image shape: {img.shape}")
                self.clear()
                return

            # Asegurar que es uint8
            if img.dtype != np.uint8:
                if img.max() <= 1.0:
                    img = (img * 255).astype(np.uint8)
                else:
                    img = np.clip(img, 0, 255).astype(np.uint8)

            # Convertir a bytes primero — Python mantiene el objeto vivo,
            # evitando que el GC libere el buffer antes de que Qt lo copie.
            h, w, ch = img.shape
            img_bytes = img.tobytes()
            qimg = QImage(img_bytes, w, h, ch * w, QImage.Format.Format_RGB888)

            # fromImage hace una copia interna completa — el pixmap es completamente
            # independiente de img_bytes a partir de aqui.
            self._original_pixmap = QPixmap.fromImage(qimg)

            if self._original_pixmap.isNull():
                print("[PreviewPanel] Failed to create pixmap from image")
                self.clear()
                return

            self._info.setText(f"{w} × {h} px")
            self._refresh_scaled()
            print(f"[PreviewPanel] Image displayed: {w}x{h}")
        except Exception as e:
            import traceback
            print(f"[PreviewPanel] Error displaying image: {e}")
            print(traceback.format_exc())
            self.clear()

    def _refresh_scaled(self):
        """Siempre escala desde el pixmap original — sin degradacion acumulada."""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        scaled = self._original_pixmap.scaled(
            self._label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_scaled()

    def clear(self):
        self._original_pixmap = None
        self._label.clear()
        self._label.setText("Conecta un Output Image\npara ver el resultado")
        self._info.setText("")
