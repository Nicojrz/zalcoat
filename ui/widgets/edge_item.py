from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath, QPen, QColor


class EdgeItem(QGraphicsPathItem):
    """Curva bezier que conecta dos puertos."""

    def __init__(self, source_pos: QPointF, target_pos: QPointF,
                 source_id: str = "", target_id: str = ""):
        super().__init__()
        self.source_id = source_id
        self.target_id = target_id
        self._source_pos = source_pos
        self._target_pos = target_pos
        self.setZValue(-1)
        pen = QPen(QColor("#5B8DDE"), 2)
        pen.setStyle(pen.style().SolidLine)
        self.setPen(pen)
        self._update_path()

    def _update_path(self):
        s = self._source_pos
        t = self._target_pos
        dx = abs(t.x() - s.x()) * 0.5

        path = QPainterPath(s)
        path.cubicTo(
            QPointF(s.x() + dx, s.y()),
            QPointF(t.x() - dx, t.y()),
            t
        )
        self.setPath(path)

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
