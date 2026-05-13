from __future__ import annotations
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QStyleOptionGraphicsItem, QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from core.node_base import BaseNode

PORT_RADIUS = 7
NODE_W = 180
NODE_H = 72
HEADER_H = 32
THUMB_SIZE = 36   # miniatura de imagen en el cuerpo del nodo


class PortItem(QGraphicsEllipseItem):
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
    selected = pyqtSignal(str)
    moved = pyqtSignal(str, float, float)
    double_clicked = pyqtSignal(str)   # node_id


class NodeItem(QGraphicsItem):
    def __init__(self, node: BaseNode, signals: NodeSignals):
        super().__init__()
        self.node = node
        self.signals = signals
        self._selected = False
        self._hovered = False
        self._thumb = None   # QPixmap miniatura para InputImage

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

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

    def _get_thumb(self):
        """Genera miniatura QPixmap del ndarray del nodo si es InputImage."""
        try:
            from core.nodes.all_nodes import InputImageNode
            import cv2
            from PyQt6.QtGui import QImage, QPixmap
            if not isinstance(self.node, InputImageNode):
                return None
            img = self.node._image
            if img is None:
                return None
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
            return pix.scaled(THUMB_SIZE, THUMB_SIZE,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        except Exception:
            return None

    # -- Qt overrides --

    def boundingRect(self) -> QRectF:
        return QRectF(-2, -2, NODE_W + 4, NODE_H + 4)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Sombra
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
        painter.drawRoundedRect(QRectF(4, 4, NODE_W, NODE_H), 10, 10)

        # Cuerpo
        painter.setBrush(QBrush(QColor("#2A2D3E")))
        border_color = QColor(self.node.color) if self._selected else QColor("#3A3D52")
        painter.setPen(QPen(border_color, 2 if self._selected else 1))
        painter.drawRoundedRect(QRectF(0, 0, NODE_W, NODE_H), 10, 10)

        # Header coloreado
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, NODE_W, HEADER_H), 10, 10)
        path.addRect(QRectF(0, HEADER_H / 2, NODE_W, HEADER_H / 2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(self.node.color)))
        painter.drawPath(path)

        # Etiqueta header
        painter.setPen(QPen(QColor("#FFFFFF")))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(10, 0, NODE_W - 20, HEADER_H),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         self.node.label)

        # Cuerpo del nodo - contenido
        from core.nodes.all_nodes import InputImageNode
        if isinstance(self.node, InputImageNode):
            self._paint_input_node_body(painter)
        else:
            # Subtitulo generico
            painter.setPen(QPen(QColor("#8A8FAF")))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(QRectF(10, HEADER_H + 4, NODE_W - 20, NODE_H - HEADER_H - 8),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             self.node.node_type.replace("_", " "))

    def _paint_input_node_body(self, painter: QPainter):
        """Pinta miniatura + nombre de archivo o instruccion de clic."""
        from core.nodes.all_nodes import InputImageNode
        body_top = HEADER_H + 4
        body_h = NODE_H - HEADER_H - 8

        thumb = self._get_thumb()
        if thumb:
            # Miniatura a la izquierda
            thumb_x = 8
            thumb_y = body_top + (body_h - thumb.height()) // 2
            painter.drawPixmap(int(thumb_x), int(thumb_y), thumb)
            # Nombre del archivo
            filename = getattr(self.node, "filename", "imagen cargada")
            painter.setPen(QPen(QColor("#CDD6F4")))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(
                QRectF(thumb_x + thumb.width() + 6, body_top, NODE_W - thumb_x - thumb.width() - 14, body_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                filename
            )
        else:
            # Sin imagen: instruccion
            painter.setPen(QPen(QColor("#6C7086")))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(
                QRectF(8, body_top, NODE_W - 16, body_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                "Doble clic para\ncargar imagen"
            )

    def update(self):
        self._thumb = None   # invalida cache de miniatura
        super().update()

    def hoverEnterEvent(self, event):
        self._hovered = True
        super().update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        super().update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self.signals.selected.emit(self.node.node_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.signals.double_clicked.emit(self.node.node_id)
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.signals.moved.emit(self.node.node_id, value.x(), value.y())
        return super().itemChange(change, value)
