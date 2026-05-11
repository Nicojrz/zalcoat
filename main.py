import sys
import os

# Asegura que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from ui.main_window import MainWindow


def apply_dark_palette(app: QApplication):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1A1B26"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#CDD6F4"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#2A2D3E"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1E2030"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#CDD6F4"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#2A2D3E"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#CDD6F4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#5B6CFF"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDI Node Editor")
    app.setStyle("Fusion")
    apply_dark_palette(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
