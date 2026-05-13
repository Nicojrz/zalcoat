from __future__ import annotations
import os
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QUrl
from PyQt6.QtGui import QColor, QPen, QWheelEvent, QKeyEvent, QAction

from ui.widgets.node_item import NodeItem, NodeSignals, PortItem
from ui.widgets.edge_item import EdgeItem
from models.workflow_graph import WorkflowGraph
from core.node_base import BaseNode

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


class NodeCanvas(QGraphicsView):
    node_selected = pyqtSignal(object)       # BaseNode | None
    graph_changed = pyqtSignal()             # solicita re-ejecucion
    load_image_for_node = pyqtSignal(str)    # node_id
    image_dropped = pyqtSignal(str, QPointF) # path, scene_pos  (imagen sobre canvas)

    def __init__(self, graph: WorkflowGraph):
        super().__init__()
        self.graph = graph
        self._node_items: dict[str, NodeItem] = {}
        self._edge_items: list[EdgeItem] = []

        self._connecting: bool = False
        self._conn_source_port: PortItem | None = None
        self._temp_edge: EdgeItem | None = None

        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QColor("#0F0F0F"))
        self.setScene(self._scene)

        self.setRenderHint(self.renderHints().Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)

        self._draw_grid()

        self._signals = NodeSignals()
        self._signals.selected.connect(self._on_node_selected)
        self._signals.moved.connect(self._on_node_moved)
        self._signals.double_clicked.connect(self._on_node_double_clicked)

    # ── Grid ──────────────────────────────────────────────

    def _draw_grid(self):
        step = 30
        extent = 3000
        pen = QPen(QColor("#25263A"), 1)
        for x in range(-extent, extent, step):
            self._scene.addLine(x, -extent, x, extent, pen)
        for y in range(-extent, extent, step):
            self._scene.addLine(-extent, y, extent, y, pen)

    # ── Nodos ─────────────────────────────────────────────

    def add_node(self, node: BaseNode, x: float = 0, y: float = 0) -> NodeItem:
        item = NodeItem(node, self._signals)
        item.setPos(x, y)
        self._scene.addItem(item)
        self._node_items[node.node_id] = item
        return item

    def add_edge(self, source_id: str, target_id: str, source_port_index: int = 0, target_port_index: int = 0):
        source_item = self._node_items.get(source_id)
        target_item = self._node_items.get(target_id)
        if source_item is None or target_item is None:
            return
        if source_port_index >= len(source_item.output_ports) or target_port_index >= len(target_item.input_ports):
            return
        edge = EdgeItem(
            source_item.output_ports[source_port_index].center_scene_pos(),
            target_item.input_ports[target_port_index].center_scene_pos(),
            source_id=source_id,
            target_id=target_id,
            source_port_index=source_port_index,
            target_port_index=target_port_index,
        )
        self._scene.addItem(edge)
        self._edge_items.append(edge)

    def has_output_node(self) -> bool:
        from core.nodes.all_nodes import OutputImageNode
        return any(isinstance(n, OutputImageNode) for n in self.graph.nodes.values())

    def remove_selected_nodes(self):
        for item in list(self._scene.selectedItems()):
            if isinstance(item, NodeItem):
                self._remove_node_item(item)
        self.graph_changed.emit()

    def _remove_node_item(self, item: NodeItem):
        nid = item.node.node_id
        to_remove = [e for e in self._edge_items
                     if e.source_id == nid or e.target_id == nid]
        for e in to_remove:
            self._scene.removeItem(e)
            self._edge_items.remove(e)
            self.graph.disconnect(e.source_id, e.target_id)
        self.graph.remove_node(nid)
        self._scene.removeItem(item)
        del self._node_items[nid]

    # ── Conexiones ────────────────────────────────────────

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
        if src.is_output == tgt.is_output:
            self._cancel_connection()
            return
        out_port = src if src.is_output else tgt
        in_port  = tgt if src.is_output else src
        source_id = out_port.node_item.node.node_id
        target_id = in_port.node_item.node.node_id
        self.graph.connect(source_id, target_id)
        edge = EdgeItem(
            out_port.center_scene_pos(),
            in_port.center_scene_pos(),
            source_id=source_id,
            target_id=target_id,
            source_port_index=out_port.index,
            target_port_index=in_port.index,
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

    def _remove_edge(self, edge: EdgeItem):
        """Elimina una arista del canvas y del grafo."""
        self.graph.disconnect(edge.source_id, edge.target_id)
        self._scene.removeItem(edge)
        self._edge_items.remove(edge)
        self.graph_changed.emit()

    # ── Actualiza aristas al mover nodos ──────────────────

    def _on_node_moved(self, node_id: str, x: float, y: float):
        for edge in self._edge_items:
            if edge.source_id == node_id:
                src_item = self._node_items.get(node_id)
                if src_item and edge.source_port_index < len(src_item.output_ports):
                    new_source_pos = src_item.output_ports[edge.source_port_index].center_scene_pos()
                    edge.update_positions(new_source_pos, edge._target_pos)
            if edge.target_id == node_id:
                tgt_item = self._node_items.get(node_id)
                if tgt_item and edge.target_port_index < len(tgt_item.input_ports):
                    new_target_pos = tgt_item.input_ports[edge.target_port_index].center_scene_pos()
                    edge.update_positions(edge._source_pos, new_target_pos)

    def _on_node_selected(self, node_id: str):
        node = self.graph.nodes.get(node_id)
        self.node_selected.emit(node)

    def _on_node_double_clicked(self, node_id: str):
        self.load_image_for_node.emit(node_id)

    # ── Drag & Drop ───────────────────────────────────────

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasText():
            event.accept()
        elif mime.hasUrls() and any(self._is_image_url(u) for u in mime.urls()):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        mime = event.mimeData()
        scene_pos = self.mapToScene(event.position().toPoint())

        if mime.hasText():
            node_type = mime.text()
            # Solo un OutputImageNode permitido
            if node_type == "output_image" and self.has_output_node():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Un solo nodo Output",
                    "Ya existe un nodo Output en el workflow.\n"
                    "Solo se permite uno a la vez."
                )
                return
            try:
                node = self.graph.add_node(node_type)
                self.add_node(node, scene_pos.x() - 80, scene_pos.y() - 30)
                self.graph_changed.emit()
            except ValueError as e:
                print(f"[Canvas] Drop error: {e}")

        elif mime.hasUrls():
            for url in mime.urls():
                if self._is_image_url(url):
                    self.image_dropped.emit(url.toLocalFile(), scene_pos)
                    scene_pos = QPointF(scene_pos.x() + 200, scene_pos.y() + 40)

    @staticmethod
    def _is_image_url(url: QUrl) -> bool:
        ext = os.path.splitext(url.toLocalFile())[1].lower()
        return ext in IMAGE_EXTS

    # ── Mouse ─────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, PortItem):
                self._start_connection(item)
                return

        elif event.button() == Qt.MouseButton.RightButton:
            # Click derecho sobre arista → menú contextual para eliminar
            item = self.itemAt(event.pos())
            if isinstance(item, EdgeItem):
                self._show_edge_context_menu(item, event.globalPosition().toPoint())
                return
            elif isinstance(item, NodeItem):
                self._show_node_context_menu(item, event.globalPosition().toPoint())
                return

        super().mousePressEvent(event)

    def _show_edge_context_menu(self, edge: EdgeItem, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #2A2D3E; color: #CDD6F4; border: 1px solid #3A3D52;
                    border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #FF6B6B; color: #fff; }
        """)
        act = QAction("Eliminar conexión", menu)
        act.triggered.connect(lambda: self._remove_edge(edge))
        menu.addAction(act)
        menu.exec(global_pos)

    def _show_node_context_menu(self, item: NodeItem, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #2A2D3E; color: #CDD6F4; border: 1px solid #3A3D52;
                    border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #FF6B6B; color: #fff; }
        """)
        act_del = QAction("Eliminar nodo", menu)
        act_del.triggered.connect(lambda: (self._remove_node_item(item), self.graph_changed.emit()))
        menu.addAction(act_del)
        menu.exec(global_pos)

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

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            self._signals.double_clicked.emit(item.node.node_id)
        super().mouseDoubleClickEvent(event)

    # ── Zoom ──────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    # ── Centrar ───────────────────────────────────────────

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
