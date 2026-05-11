from __future__ import annotations
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QWheelEvent, QKeyEvent

from ui.widgets.node_item import NodeItem, NodeSignals, PortItem
from ui.widgets.edge_item import EdgeItem
from models.workflow_graph import WorkflowGraph
from core.node_base import BaseNode


class NodeCanvas(QGraphicsView):
    node_selected = pyqtSignal(object)    # BaseNode | None
    graph_changed = pyqtSignal()          # solicita re-ejecución

    def __init__(self, graph: WorkflowGraph):
        super().__init__()
        self.graph = graph
        self._node_items: dict[str, NodeItem] = {}   # node_id → NodeItem
        self._edge_items: list[EdgeItem] = []

        # Estado para drag de conexión
        self._connecting: bool = False
        self._conn_source_port: PortItem | None = None
        self._temp_edge: EdgeItem | None = None

        # Scene
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QColor("#1A1B26"))
        self.setScene(self._scene)

        self.setRenderHint(self.renderHints().Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)

        # Grid punteada
        self._draw_grid()

        # Signals compartidas entre todos los nodos
        self._signals = NodeSignals()
        self._signals.selected.connect(self._on_node_selected)
        self._signals.moved.connect(self._on_node_moved)

    # ── Grid decorativa ────────────────────────────────────

    def _draw_grid(self):
        step = 30
        extent = 3000
        pen = QPen(QColor("#25263A"), 1)
        for x in range(-extent, extent, step):
            self._scene.addLine(x, -extent, x, extent, pen)
        for y in range(-extent, extent, step):
            self._scene.addLine(-extent, y, extent, y, pen)

    # ── Añadir / eliminar nodos ────────────────────────────

    def add_node(self, node: BaseNode, x: float = 0, y: float = 0) -> NodeItem:
        item = NodeItem(node, self._signals)
        item.setPos(x, y)
        self._scene.addItem(item)
        self._node_items[node.node_id] = item
        return item

    def remove_selected_nodes(self):
        for item in self._scene.selectedItems():
            if isinstance(item, NodeItem):
                nid = item.node.node_id
                # Eliminar aristas relacionadas
                to_remove = [e for e in self._edge_items
                             if e.source_id == nid or e.target_id == nid]
                for e in to_remove:
                    self._scene.removeItem(e)
                    self._edge_items.remove(e)
                self.graph.remove_node(nid)
                self._scene.removeItem(item)
                del self._node_items[nid]
        self.graph_changed.emit()

    # ── Conexiones entre nodos ────────────────────────────

    def _start_connection(self, port: PortItem):
        self._connecting = True
        self._conn_source_port = port
        start = port.center_scene_pos()
        self._temp_edge = EdgeItem(start, start)
        pen = QPen(QColor("#FFAA44"), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self._temp_edge.setPen(pen)
        self._scene.addItem(self._temp_edge)

    def _finish_connection(self, target_port: PortItem):
        if self._conn_source_port is None or self._temp_edge is None:
            return

        src = self._conn_source_port
        tgt = target_port

        # El source debe ser output y el target input (o viceversa)
        if src.is_output == tgt.is_output:
            self._cancel_connection()
            return

        out_port = src if src.is_output else tgt
        in_port = tgt if src.is_output else src

        source_id = out_port.node_item.node.node_id
        target_id = in_port.node_item.node.node_id

        self.graph.connect(source_id, target_id)

        edge = EdgeItem(
            out_port.center_scene_pos(),
            in_port.center_scene_pos(),
            source_id=source_id,
            target_id=target_id,
        )
        self._scene.addItem(edge)
        self._edge_items.append(edge)

        self._cancel_connection()
        self.graph_changed.emit()

    def _cancel_connection(self):
        if self._temp_edge:
            self._scene.removeItem(self._temp_edge)
            self._temp_edge = None
        self._connecting = False
        self._conn_source_port = None

    # ── Actualiza posiciones de aristas al mover nodos ────

    def _on_node_moved(self, node_id: str, x: float, y: float):
        for edge in self._edge_items:
            if edge.source_id == node_id:
                src_item = self._node_items.get(node_id)
                if src_item and src_item.output_ports:
                    edge.update_positions(
                        src_item.output_ports[0].center_scene_pos(),
                        edge._target_pos
                    )
            if edge.target_id == node_id:
                tgt_item = self._node_items.get(node_id)
                if tgt_item and tgt_item.input_ports:
                    edge.update_positions(
                        edge._source_pos,
                        tgt_item.input_ports[0].center_scene_pos()
                    )

    def _on_node_selected(self, node_id: str):
        node = self.graph.nodes.get(node_id)
        self.node_selected.emit(node)

    # ── Drag & Drop desde el panel de nodos ───────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        node_type = event.mimeData().text()
        scene_pos = self.mapToScene(event.position().toPoint())
        try:
            node = self.graph.add_node(node_type)
            self.add_node(node, scene_pos.x() - 80, scene_pos.y() - 30)
            self.graph_changed.emit()
        except ValueError as e:
            print(f"[Canvas] Drop error: {e}")

    # ── Mouse events para conexiones ──────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, PortItem):
                self._start_connection(item)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._connecting and self._temp_edge:
            scene_pos = self.mapToScene(event.pos())
            self._temp_edge.set_target(scene_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._connecting:
            item = self.itemAt(event.pos())
            if isinstance(item, PortItem):
                self._finish_connection(item)
            else:
                self._cancel_connection()
            return
        super().mouseReleaseEvent(event)

    # ── Zoom con rueda ────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    # ── Teclas ────────────────────────────────────────────

    def fit_view(self):
        rect = self._scene.itemsBoundingRect()
        if not rect.isEmpty():
            self.fitInView(rect.adjusted(-40, -40, 40, 40),
                           Qt.AspectRatioMode.KeepAspectRatio)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            self.remove_selected_nodes()
        elif event.key() == Qt.Key.Key_F:
            self.fit_view()
        super().keyPressEvent(event)
