from PyQt6.QtWidgets import QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPainter


class EdgeItem(QGraphicsPathItem):
    """Curva bezier que conecta dos puertos. Click derecho la elimina."""

    HIT_WIDTH = 12   # ancho de zona clickeable (invisible)

    def __init__(self, source_pos: QPointF, target_pos: QPointF,
                 source_id: str = "", target_id: str = ""):
        super().__init__()
        self.source_id = source_id
        self.target_id = target_id
        self._source_pos = source_pos
        self._target_pos = target_pos
        self._hovered = False

        self.setZValue(-1)
        self.setAcceptHoverEvents(True)
        # Permite recibir eventos de mouse
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)

        self._update_style()
        self._update_path()

    def _update_style(self):
        if self._hovered:
            pen = QPen(QColor("#FF6B6B"), 2.5)
        else:
            pen = QPen(QColor("#5B8DDE"), 2)
        pen.setStyle(pen.style().SolidLine)
        self.setPen(pen)

    def _update_path(self):
        s = self._source_pos
        t = self._target_pos
        dx = max(abs(t.x() - s.x()) * 0.5, 60)

        path = QPainterPath(s)
        path.cubicTo(
            QPointF(s.x() + dx, s.y()),
            QPointF(t.x() - dx, t.y()),
            t
        )
        self.setPath(path)

    # Amplía la zona de detección del click
    def shape(self):
        stroker = QPainterPath()
        from PyQt6.QtGui import QPainterPathStroker
        ps = QPainterPathStroker()
        ps.setWidth(self.HIT_WIDTH)
        return ps.createStroke(self.path())

    def update_positions(self, source_pos: QPointF, target_pos: QPointF):
        self._source_pos = source_pos
        self._target_pos = target_pos
        self._update_path()

    def set_source(self, pos: QPointF):
        self._source_pos = pos
        self._update_path()

    def set_target(self, pos: QPointF):
        self._target_pos = pos
        self._update_path()

    # -- Hover --

    def hoverEnterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().hoverLeaveEvent(event)
