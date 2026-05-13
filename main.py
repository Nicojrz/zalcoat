import sys
import os

# Asegura que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from ui.main_window import MainWindow

def apply_dark_palette(app: QApplication):
    palette = QPalette()
    # Monochromatic dark gray palette
    palette.setColor(QPalette.ColorRole.Window, QColor("#0F0F0F"))        # Very dark background
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E0E0E0"))    # Light gray text
    palette.setColor(QPalette.ColorRole.Base, QColor("#1A1A1A"))          # Dark gray base
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#141414")) # Slightly darker alternate
    palette.setColor(QPalette.ColorRole.Text, QColor("#E0E0E0"))          # Light gray text
    palette.setColor(QPalette.ColorRole.Button, QColor("#1A1A1A"))        # Dark gray buttons
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E0E0E0"))    # Light gray button text
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#404040"))     # Medium gray highlight
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF")) # White highlighted text
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
