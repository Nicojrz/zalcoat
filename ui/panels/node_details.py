from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QScrollArea, QFrame,
    QPushButton, QColorDialog
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
