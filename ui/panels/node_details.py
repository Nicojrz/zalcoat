from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QScrollArea, QFrame,
    QPushButton, QColorDialog, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from core.node_base import BaseNode, NodeParam


class NodeDetailsPanel(QWidget):
    """Genera widgets Qt dinámicamente según los param_descriptors del nodo seleccionado."""

    param_changed = pyqtSignal(str)   # pide re-ejecución del grafo para el nodo modificado

    def __init__(self):
        super().__init__()
        self.setFixedWidth(220)
        self.setStyleSheet("""
            QWidget { background: #1E2030; color: #CDD6F4; }
            QLabel { color: #A6ADC8; font-size: 11px; }
            QLabel#title { color: #CDD6F4; font-size: 13px; font-weight: bold; }
            QLabel#category { color: #6C7086; font-size: 10px; }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background: #2A2D3E; border: 1px solid #3A3D52;
                border-radius: 4px; padding: 3px 6px; color: #CDD6F4;
            }
            QSlider::groove:horizontal {
                height: 4px; background: #3A3D52; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px; height: 12px; margin: -4px 0;
                background: #5B6CFF; border-radius: 6px;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(10)
        self._layout.addStretch()
        scroll.setWidget(self._inner)

        self._current_node: BaseNode | None = None
        self._show_placeholder()

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self):
        self._clear()
        lbl = QLabel("Selecciona un nodo\npara ver sus parámetros")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #6C7086; font-size: 11px;")
        self._layout.addWidget(lbl)
        self._layout.addStretch()

    def load_node(self, node: BaseNode | None):
        self._current_node = node
        self._clear()

        if node is None:
            self._show_placeholder()
            return

        # Header
        title = QLabel(node.label)
        title.setObjectName("title")
        category = QLabel(node.category)
        category.setObjectName("category")
        self._layout.addWidget(title)
        self._layout.addWidget(category)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #3A3D52;")
        self._layout.addWidget(sep)

        descriptors = node.param_descriptors()
        if not descriptors:
            lbl = QLabel("Sin parámetros")
            lbl.setStyleSheet("color: #6C7086;")
            self._layout.addWidget(lbl)
        else:
            for desc in descriptors:
                self._add_param_widget(node, desc)

        self._layout.addStretch()

    def _add_param_widget(self, node: BaseNode, desc: NodeParam):
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(3)

        label = QLabel(desc.label)
        row_layout.addWidget(label)

        if desc.type == "int":
            widget = self._make_int_widget(node, desc)
        elif desc.type == "float":
            widget = self._make_float_widget(node, desc)
        elif desc.type == "bool":
            widget = self._make_bool_widget(node, desc)
        elif desc.type == "choice":
            widget = self._make_choice_widget(node, desc)
        elif desc.type == "hsv":
            widget = self._make_hsv_widget(node, desc)
        elif desc.type == "kernel":
            widget = self._make_kernel_widget(node, desc)
        else:
            widget = QLabel(f"({desc.type} no soportado)")

        row_layout.addWidget(widget)
        self._layout.addWidget(row)

    def _make_int_widget(self, node: BaseNode, desc: NodeParam) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        spin = QSpinBox()
        spin.setRange(int(desc.min or 0), int(desc.max or 100))
        spin.setSingleStep(int(desc.step or 1))
        spin.setValue(int(node.params[desc.name]))

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(desc.min or 0), int(desc.max or 100))
        slider.setSingleStep(int(desc.step or 1))
        slider.setValue(int(node.params[desc.name]))

        def on_spin(v):
            slider.blockSignals(True)
            slider.setValue(v)
            slider.blockSignals(False)
            node.set_param(desc.name, v)
            self.param_changed.emit(node.node_id)

        def on_slider(v):
            spin.blockSignals(True)
            spin.setValue(v)
            spin.blockSignals(False)
            node.set_param(desc.name, v)
            self.param_changed.emit(node.node_id)

        spin.valueChanged.connect(on_spin)
        slider.valueChanged.connect(on_slider)

        h.addWidget(slider)
        h.addWidget(spin)
        return container

    def _make_float_widget(self, node: BaseNode, desc: NodeParam) -> QWidget:
        spin = QDoubleSpinBox()
        spin.setRange(float(desc.min or 0.0), float(desc.max or 100.0))
        spin.setSingleStep(float(desc.step or 0.1))
        spin.setDecimals(2)
        spin.setValue(float(node.params[desc.name]))

        def on_change(v):
            node.set_param(desc.name, v)
            self.param_changed.emit(node.node_id)

        spin.valueChanged.connect(on_change)
        return spin

    def _make_bool_widget(self, node: BaseNode, desc: NodeParam) -> QWidget:
        cb = QCheckBox()
        cb.setChecked(bool(node.params[desc.name]))

        def on_change(state):
            node.set_param(desc.name, bool(state))
            self.param_changed.emit(node.node_id)

        cb.stateChanged.connect(on_change)
        return cb

    def _make_choice_widget(self, node: BaseNode, desc: NodeParam) -> QWidget:
        combo = QComboBox()
        combo.addItems(desc.choices)
        current = node.params[desc.name]
        if current in desc.choices:
            combo.setCurrentIndex(desc.choices.index(current))

        def on_change(text):
            node.set_param(desc.name, text)
            self.param_changed.emit(node.node_id)

        combo.currentTextChanged.connect(on_change)
        return combo

    def _make_kernel_widget(self, node: BaseNode, desc: NodeParam) -> QWidget:
        matrix = node.params.get(desc.name, desc.default)
        size = len(matrix) if isinstance(matrix, list) and matrix else 3

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        size_label = QLabel("Size:")
        size_label.setStyleSheet("color: #CDD6F4; font-size: 11px;")
        size_combo = QComboBox()
        size_combo.addItems(["3", "5"])
        size_combo.setCurrentText(str(size))
        size_combo.setFixedWidth(60)

        header_layout.addWidget(size_label)
        header_layout.addWidget(size_combo)
        header_layout.addStretch()
        layout.addWidget(header)

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(4)
        layout.addWidget(grid_widget)

        checkboxes: list[list[QCheckBox]] = []

        def normalize_matrix(matrix_value, matrix_size):
            try:
                normalized = [list(map(int, row)) for row in matrix_value]
            except Exception:
                normalized = []
            if len(normalized) != matrix_size or any(len(row) != matrix_size for row in normalized):
                new_matrix = [[0] * matrix_size for _ in range(matrix_size)]
                old_size = len(normalized)
                if old_size == 0:
                    return [[1] * matrix_size for _ in range(matrix_size)]
                offset = (matrix_size - old_size) // 2
                for y in range(min(old_size, matrix_size)):
                    for x in range(min(len(normalized[y]), matrix_size)):
                        new_matrix[offset + y][offset + x] = 1 if normalized[y][x] else 0
                return new_matrix
            return [[1 if value else 0 for value in row] for row in normalized]

        def set_node_kernel(matrix_value):
            node.set_param(desc.name, matrix_value)
            self.param_changed.emit(node.node_id)

        def rebuild_grid(new_size):
            nonlocal matrix, size
            size = new_size
            matrix = normalize_matrix(matrix, size)
            set_node_kernel(matrix)
            for i in reversed(range(grid_layout.count())):
                item = grid_layout.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()
            checkboxes.clear()
            for y in range(size):
                row = []
                for x in range(size):
                    box = QCheckBox()
                    box.setChecked(bool(matrix[y][x]))
                    box.setStyleSheet(
                        "QCheckBox::indicator { width: 18px; height: 18px; }"
                        "QCheckBox::indicator:checked { background: #5B6CFF; border: 1px solid #3A3D52; }"
                        "QCheckBox::indicator:unchecked { background: #1A1A1A; border: 1px solid #3A3D52; }"
                    )
                    def make_toggler(py=y, px=x):
                        def on_toggle(state):
                            matrix[py][px] = 1 if state == Qt.CheckState.Checked else 0
                            set_node_kernel(matrix)
                        return on_toggle
                    box.stateChanged.connect(make_toggler())
                    grid_layout.addWidget(box, y, x)
                    row.append(box)
                checkboxes.append(row)

        rebuild_grid(size)

        def on_size_changed(text):
            new_size = int(text)
            rebuild_grid(new_size)

        size_combo.currentTextChanged.connect(on_size_changed)
        return widget

    def _make_hsv_widget(self, node: BaseNode, desc: NodeParam) -> QWidget:
        value = tuple(node.params.get(desc.name, (0, 0, 0)))
        hue, sat, val = int(value[0]), int(value[1]), int(value[2])

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        preview = QFrame()
        preview.setFixedSize(40, 24)
        preview.setStyleSheet(
            f"background: {QColor.fromHsv(hue * 2, sat, val).name()};"
            "border: 1px solid #3A3D52; border-radius: 4px;"
        )

        info = QLabel(f"H:{hue} S:{sat} V:{val}")
        info.setStyleSheet("color: #CDD6F4; font-size: 10px;")

        button = QPushButton("Seleccionar")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            "background: #2A2D3E; border: 1px solid #3A3D52; border-radius: 4px;"
            "padding: 4px 8px; color: #CDD6F4;"
        )

        top_layout.addWidget(preview)
        top_layout.addWidget(info)
        top_layout.addStretch()
        top_layout.addWidget(button)
        layout.addWidget(top_row)

        def update_widgets(h, s, v):
            preview.setStyleSheet(
                f"background: {QColor.fromHsv(h * 2, s, v).name()};"
                "border: 1px solid #3A3D52; border-radius: 4px;"
            )
            info.setText(f"H:{h} S:{s} V:{v}")
            node.set_param(desc.name, (h, s, v))
            self.param_changed.emit(node.node_id)

        def pick_color():
            current_color = QColor.fromHsv(hue * 2, sat, val)
            selected = QColorDialog.getColor(current_color, self, "Selecciona un color HSV")
            if not selected.isValid():
                return
            picked_h, picked_s, picked_v, _ = selected.getHsv()
            picked_h = int(picked_h / 2) if picked_h >= 0 else 0
            picked_s = int(picked_s)
            picked_v = int(picked_v)
            update_widgets(picked_h, picked_s, picked_v)

        button.clicked.connect(pick_color)
        return widget
