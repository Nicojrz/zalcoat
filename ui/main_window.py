import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QToolBar, QStatusBar,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QPointF
from PyQt6.QtGui import QAction, QKeySequence

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
        self.setWindowTitle("PDI Node Editor")
        self.resize(1400, 860)
        self.setStyleSheet("background: #1A1B26; color: #CDD6F4;")
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
        splitter.setStyleSheet("QSplitter::handle { background: #2A2D3E; }")
        self.setCentralWidget(splitter)

        self._build_toolbar()

        self._status = QStatusBar()
        self._status.setStyleSheet("background: #13141F; color: #6C7086; font-size: 11px;")
        self.setStatusBar(self._status)
        self._status.showMessage(
            "Arrastra una imagen al canvas  |  Doble clic en Input Image para cambiar imagen  |  Clic derecho en conexion para eliminarla"
        )

        self._exec_timer = QTimer()
        self._exec_timer.setSingleShot(True)
        self._exec_timer.setInterval(300)
        self._exec_timer.timeout.connect(self._run_graph)

        # Senales del canvas
        self._canvas.node_selected.connect(self._details.load_node)
        self._canvas.graph_changed.connect(self._schedule_run)
        self._canvas.load_image_for_node.connect(self._pick_image_for_node)
        self._canvas.image_dropped.connect(self._on_image_dropped_on_canvas)
        self._details.param_changed.connect(self._schedule_run)

    # ── Toolbar ───────────────────────────────────────────

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setStyleSheet("""
            QToolBar { background: #13141F; border-bottom: 1px solid #2A2D3E;
                       spacing: 4px; padding: 4px; }
            QToolButton { color: #CDD6F4; padding: 4px 12px; border-radius: 4px; }
            QToolButton:hover { background: #2A2D3E; }
        """)
        self.addToolBar(tb)

        act_open = QAction("Abrir imagen", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._open_image_dialog)
        tb.addAction(act_open)

        tb.addSeparator()

        act_run = QAction("Ejecutar", self)
        act_run.setShortcut("Ctrl+Return")
        act_run.triggered.connect(self._run_graph)
        tb.addAction(act_run)

        act_clear = QAction("Limpiar", self)
        act_clear.triggered.connect(self._clear_canvas)
        tb.addAction(act_clear)

        tb.addSeparator()

        act_fit = QAction("Centrar (F)", self)
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
            QMessageBox.critical(self, "Error", f"No se pudo leer:\n{path}")
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
            "Imagenes (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp)"
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
            "Imagenes (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp)"
        )
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            QMessageBox.critical(self, "Error", f"No se pudo leer:\n{path}")
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

    # ── Ejecucion del workflow ────────────────────────────

    def _schedule_run(self):
        self._exec_timer.start()

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
            print(f"[MainWindow] Executing graph with {len(self.graph.nodes)} nodes...")
            results = self.graph.execute()
            if not results:
                print("[MainWindow] No results from graph execution")
                self._preview.clear()
                return

            # Mostrar la salida del OutputImageNode
            out = self._output_node()
            if out is None:
                print("[MainWindow] No OutputImageNode found")
                self._preview.clear()
                return
            
            if out.node_id not in results:
                print(f"[MainWindow] OutputImageNode {out.node_id} not in results")
                print(f"[MainWindow] Available results: {list(results.keys())}")
                self._preview.clear()
                return
            
            output_img = results[out.node_id]
            print(f"[MainWindow] Showing output image with shape: {output_img.shape if hasattr(output_img, 'shape') else 'unknown'}")
            self._preview.show_image(output_img)
            self._status.showMessage(f"Ejecutado: {len(results)} nodo(s) procesados")

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
