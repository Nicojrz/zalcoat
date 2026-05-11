from __future__ import annotations
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QStyleOptionGraphicsItem, QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from core.node_base import BaseNode


PORT_RADIUS = 7
NODE_W = 160
NODE_H = 60
HEADER_H = 32


class PortItem(QGraphicsEllipseItem):
    """Puerto de entrada o salida en un nodo."""

    def __init__(self, node_item: "NodeItem", is_output: bool, index: int = 0):
        super().__init__(-PORT_RADIUS, -PORT_RADIUS, PORT_RADIUS * 2, PORT_RADIUS * 2)
        self.node_item = node_item
        self.is_output = is_output
        self.index = index
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._hovered = False
        self._update_style()

    def _update_style(self):
        color = QColor("#5B6CFF") if self.is_output else QColor("#FF6B6B")
        if self._hovered:
            color = color.lighter(140)
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#ffffff"), 1.5))

    def hoverEnterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().hoverLeaveEvent(event)

    def center_scene_pos(self) -> QPointF:
        return self.mapToScene(QPointF(0, 0))


class NodeSignals(QObject):
    selected = pyqtSignal(str)           # node_id
    moved = pyqtSignal(str, float, float)
    port_clicked = pyqtSignal(object, bool)  # PortItem, is_output


class NodeItem(QGraphicsItem):
    def __init__(self, node: BaseNode, signals: NodeSignals):
        super().__init__()
        self.node = node
        self.signals = signals
        self._selected = False
        self._hovered = False

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        # Puertos
        self.input_ports: list[PortItem] = []
        self.output_ports: list[PortItem] = []
        self._build_ports()

    def _build_ports(self):
        if self.node.max_inputs > 0:
            port = PortItem(self, is_output=False)
            port.setParentItem(self)
            port.setPos(0, NODE_H / 2)
            self.input_ports.append(port)

        if self.node.max_outputs > 0:
            port = PortItem(self, is_output=True)
            port.setParentItem(self)
            port.setPos(NODE_W, NODE_H / 2)
            self.output_ports.append(port)

    # ── Qt overrides ───────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(-2, -2, NODE_W + 4, NODE_H + 4)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Sombra suave
        shadow_rect = QRectF(4, 4, NODE_W, NODE_H)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawRoundedRect(shadow_rect, 10, 10)

        # Cuerpo del nodo
        body_rect = QRectF(0, 0, NODE_W, NODE_H)
        body_color = QColor("#2A2D3E")
        painter.setBrush(QBrush(body_color))
        border_color = QColor(self.node.color) if self._selected else QColor("#3A3D52")
        painter.setPen(QPen(border_color, 2 if self._selected else 1))
        painter.drawRoundedRect(body_rect, 10, 10)

        # Header coloreado
        header_rect = QRectF(0, 0, NODE_W, HEADER_H)
        path = QPainterPath()
        path.addRoundedRect(header_rect, 10, 10)
        # Recortar parte inferior del header
        path.addRect(QRectF(0, HEADER_H / 2, NODE_W, HEADER_H / 2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(self.node.color)))
        painter.drawPath(path)

        # Etiqueta header
        painter.setPen(QPen(QColor("#FFFFFF")))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(10, 0, NODE_W - 20, HEADER_H),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         self.node.label)

        # Subtítulo / tipo
        painter.setPen(QPen(QColor("#8A8FAF")))
        font2 = QFont("Segoe UI", 7)
        painter.setFont(font2)
        painter.drawText(QRectF(10, HEADER_H + 2, NODE_W - 20, NODE_H - HEADER_H - 4),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         self.node.node_type.replace("_", " "))

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self.signals.selected.emit(self.node.node_id)
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.signals.moved.emit(self.node.node_id, value.x(), value.y())
        return super().itemChange(change, value)
