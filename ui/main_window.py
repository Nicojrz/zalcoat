import json
import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QToolBar, QStatusBar,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QPointF
from PyQt6.QtGui import QAction, QKeySequence, QKeyEvent

from ui.panels.node_canvas import NodeCanvas
from ui.panels.node_panel import NodePanel
from ui.panels.node_details import NodeDetailsPanel
from ui.panels.preview_panel import PreviewPanel
from models.workflow_graph import WorkflowGraph
from core.nodes.all_nodes import InputImageNode, OutputImageNode

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Nodos PDI")
        self.resize(1400, 860)
        self.setStyleSheet("background: #0F0F0F; color: #E0E0E0;")
        self.setAcceptDrops(True)

        self.graph = WorkflowGraph()

        self._node_panel = NodePanel()
        self._canvas = NodeCanvas(self.graph)
        self._details = NodeDetailsPanel()
        self._preview = PreviewPanel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._node_panel)
        splitter.addWidget(self._canvas)
        splitter.addWidget(self._details)
        splitter.addWidget(self._preview)
        splitter.setSizes([200, 700, 220, 280])
        splitter.setStyleSheet("QSplitter::handle { background: #1A1A1A; }")
        self.setCentralWidget(splitter)

        self._workflow_path: str | None = None
        self._build_toolbar()

        self._status = QStatusBar()
        self._status.setStyleSheet("background: #0A0A0A; color: #808080; font-size: 11px;")
        self.setStatusBar(self._status)
        self._status.showMessage(
            "El workflow se actualiza automáticamente  |  Doble clic en Input Image para cambiar imagen  |  Clic derecho en conexion para eliminarla  |  Ctrl+O para abrir imagen"
        )

        # Timer para ejecutar el grafo con debounce (evita múltiples ejecuciones rápidas)
        self._exec_timer = QTimer()
        self._exec_timer.setSingleShot(True)
        self._exec_timer.setInterval(100)  # Reduced to 100ms for more responsive auto-refresh
        self._exec_timer.timeout.connect(self._run_graph)

        # Senales del canvas
        self._canvas.node_selected.connect(self._details.load_node)
        self._canvas.graph_changed.connect(self._schedule_run)
        self._canvas.load_image_for_node.connect(self._pick_image_for_node)
        self._canvas.image_dropped.connect(self._on_image_dropped_on_canvas)
        self._details.param_changed.connect(self._on_node_param_changed)

    # ── Toolbar ───────────────────────────────────────────

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setStyleSheet("""
            QToolBar { background: #0A0A0A; border-bottom: 1px solid #1A1A1A;
                       spacing: 4px; padding: 4px; }
            QToolButton { color: #E0E0E0; padding: 4px 12px; border-radius: 4px; }
            QToolButton:hover { background: #1A1A1A; }
        """)
        self.addToolBar(tb)

        # Open image via File Dialog (Ctrl+O) - handled in keyPressEvent
        act_open = QAction("Abrir imagen", self)
        act_open.triggered.connect(self._open_image_dialog)
        tb.addAction(act_open)
        self.addAction(act_open)

        # Workflow persistence
        act_save = QAction("Guardar workflow", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._save_workflow_dialog)
        tb.addAction(act_save)
        self.addAction(act_save)

        act_load = QAction("Abrir workflow", self)
        act_load.setShortcut("Ctrl+Shift+O")
        act_load.triggered.connect(self._open_workflow_dialog)
        tb.addAction(act_load)
        self.addAction(act_load)

        tb.addSeparator()

        # Run graph manually (Ctrl+Return)
        act_run = QAction("Ejecutar", self)
        act_run.setShortcut("Ctrl+Return")
        act_run.triggered.connect(self._run_graph)
        self.addAction(act_run)  # Register globally
        tb.addAction(act_run)  # Add to toolbar

        # Clear canvas
        act_clear = QAction("Limpiar", self)
        act_clear.triggered.connect(self._clear_canvas)
        tb.addAction(act_clear)

        tb.addSeparator()

        # Fit view (F key)
        act_fit = QAction("Centrar", self)
        act_fit.setShortcut("F")
        act_fit.triggered.connect(self._canvas.fit_view)
        tb.addAction(act_fit)

    # ── Crear/cargar nodos de imagen ──────────────────────

    def _make_input_node(self, img: np.ndarray, filename: str,
                         scene_pos: QPointF | None = None) -> InputImageNode:
        """Crea un nodo InputImage en el canvas con imagen ya cargada."""
        node = self.graph.add_node("input_image")
        node.set_image(img)
        node.filename = filename
        x = (scene_pos.x() - 80) if scene_pos else 100
        y = (scene_pos.y() - 30) if scene_pos else 100
        self._canvas.add_node(node, x, y)
        return node

    def _load_image_file(self, path: str, scene_pos: QPointF | None = None):
        img = cv2.imread(path)
        if img is None:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la imagen:\n{path}")
            return
        filename = os.path.basename(path)
        h, w = img.shape[:2]
        self._make_input_node(img, filename, scene_pos)
        self._status.showMessage(f"Imagen cargada: {filename}  ({w} x {h} px)")
        self._schedule_run()

    # ── Abrir imagen desde toolbar ────────────────────────

    def _open_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir imagen", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp)"
        )
        if path:
            center = self._canvas.mapToScene(
                self._canvas.viewport().rect().center()
            )
            self._load_image_file(path, center)

    # ── Doble clic en InputImageNode → cambiar imagen ─────

    def _pick_image_for_node(self, node_id: str):
        node = self.graph.nodes.get(node_id)
        if not isinstance(node, InputImageNode):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Cambiar imagen", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp)"
        )
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la imagen:\n{path}")
            return
        node.set_image(img)
        node.filename = os.path.basename(path)
        item = self._canvas._node_items.get(node_id)
        if item:
            item.update()
        h, w = img.shape[:2]
        self._status.showMessage(f"Imagen actualizada: {node.filename}  ({w} x {h} px)")
        self._schedule_run()

    # ── Imagen arrastrada directamente al canvas ──────────

    def _on_image_dropped_on_canvas(self, path: str, scene_pos: QPointF):
        self._load_image_file(path, scene_pos)

    # ── Drag & drop de imagen sobre la ventana principal ──

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
            self._is_image_url(u) for u in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        canvas_pos = self._canvas.mapFrom(self, event.position().toPoint())
        scene_pos = self._canvas.mapToScene(canvas_pos)
        for url in event.mimeData().urls():
            if self._is_image_url(url):
                self._load_image_file(url.toLocalFile(), scene_pos)
                scene_pos = QPointF(scene_pos.x() + 200, scene_pos.y() + 40)

    @staticmethod
    def _is_image_url(url: QUrl) -> bool:
        ext = os.path.splitext(url.toLocalFile())[1].lower()
        return ext in IMAGE_EXTS

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_O and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._open_image_dialog()
            event.accept()
        else:
            super().keyPressEvent(event)

    # ── Ejecucion del workflow ────────────────────────────

    def _schedule_run(self, *args):
        """Programa la ejecución del workflow con debounce.
        Se ejecuta automáticamente 100ms después del último cambio."""
        self._exec_timer.stop()  # Reinicia el timer
        self._exec_timer.start()

    def _on_node_param_changed(self, node_id: str):
        self.graph.invalidate_node_and_descendants(node_id)
        self._schedule_run()

    def _output_node(self) -> OutputImageNode | None:
        """Retorna el nodo OutputImage si existe en el grafo."""
        for node in self.graph.nodes.values():
            if isinstance(node, OutputImageNode):
                return node
        return None

    def _output_has_input(self) -> bool:
        """Verifica que el OutputImageNode tenga al menos una conexion entrante."""
        out = self._output_node()
        if out is None:
            return False
        return any(e.target_id == out.node_id for e in self.graph.edges)

    def _run_graph(self):
        # Solo ejecutar si hay un OutputImageNode conectado
        if not self._output_has_input():
            print("[MainWindow] No OutputImageNode with input, clearing preview")
            self._preview.clear()
            return

        try:
            results = self.graph.execute()
            if not results:
                self._preview.clear()
                return

            # Mostrar la salida del OutputImageNode
            out = self._output_node()
            if out is None:
                self._preview.clear()
                return
            
            if out.node_id not in results:
                self._preview.clear()
                return
            
            output_img = results[out.node_id]
            self._preview.show_image(output_img)
            self._status.showMessage(f"✓ Procesado: {len(results)} nodo(s)")

        except Exception as e:
            import traceback
            self._status.showMessage(f"Error: {e}")
            print(f"[MainWindow] Error in _run_graph: {e}")
            print(traceback.format_exc())

    # ── Limpiar ───────────────────────────────────────────

    def _clear_canvas(self):
        self._canvas._scene.clear()
        self._canvas._node_items.clear()
        self._canvas._edge_items.clear()
        self.graph.nodes.clear()
        self.graph.edges.clear()
        self._canvas._draw_grid()
        self._details.load_node(None)
        self._preview.clear()
        self._status.showMessage("Canvas limpiado.")

    def _get_node_positions(self) -> dict[str, tuple[float, float]]:
        return {
            node_id: (item.pos().x(), item.pos().y())
            for node_id, item in self._canvas._node_items.items()
        }

    def _save_workflow_dialog(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar workflow", "", "Workflow (*.json)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self._save_workflow_to(path)

    def _save_workflow_to(self, path: str):
        data = self.graph.to_dict(self._get_node_positions())
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._workflow_path = path
            self._status.showMessage(f"Workflow guardado: {os.path.basename(path)}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el workflow:\n{exc}")

    def _open_workflow_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir workflow", "", "Workflow (*.json)"
        )
        if not path:
            return
        self._load_workflow_from(path)

    def _load_workflow_from(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el workflow:\n{exc}")
            return

        self._clear_canvas()
        try:
            graph = WorkflowGraph.from_dict(data)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"El workflow no es válido:\n{exc}")
            return

        self.graph = graph
        self._canvas.graph = graph

        for node_info in data.get("nodes", []):
            node_id = node_info["node_id"]
            node = self.graph.nodes.get(node_id)
            pos = node_info.get("position", {"x": 100, "y": 100})
            if node is not None:
                self._canvas.add_node(node, pos["x"], pos["y"])

        for edge in self.graph.edges:
            self._canvas.add_edge(edge.source_id, edge.target_id)

        self._workflow_path = path
        self._status.showMessage(f"Workflow cargado: {os.path.basename(path)}")
        self._schedule_run()
