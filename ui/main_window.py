import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QToolBar, QStatusBar,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QKeySequence

from ui.panels.node_canvas import NodeCanvas
from ui.panels.node_panel import NodePanel
from ui.panels.node_details import NodeDetailsPanel
from ui.panels.preview_panel import PreviewPanel
from models.workflow_graph import WorkflowGraph
from core.nodes.all_nodes import InputImageNode

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDI Node Editor")
        self.resize(1400, 860)
        self.setStyleSheet("background: #1A1B26; color: #CDD6F4;")
        self.setAcceptDrops(True)   # drag de imagen desde el explorador

        # Modelo
        self.graph = WorkflowGraph()
        self._input_node_id: str | None = None   # id del nodo InputImage activo

        # Panels
        self._node_panel = NodePanel()
        self._canvas = NodeCanvas(self.graph)
        self._details = NodeDetailsPanel()
        self._preview = PreviewPanel()

        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._node_panel)
        splitter.addWidget(self._canvas)
        splitter.addWidget(self._details)
        splitter.addWidget(self._preview)
        splitter.setSizes([200, 700, 220, 280])
        splitter.setStyleSheet("QSplitter::handle { background: #2A2D3E; }")
        self.setCentralWidget(splitter)

        # Toolbar
        self._build_toolbar()

        # Status bar
        self._status = QStatusBar()
        self._status.setStyleSheet("background: #13141F; color: #6C7086; font-size: 11px;")
        self.setStatusBar(self._status)
        self._status.showMessage(
            "📂 Abre o arrastra una imagen · Arrastra nodos al canvas · F = centrar · Supr = eliminar nodo"
        )

        # Timer de ejecución (debounce 300 ms)
        self._exec_timer = QTimer()
        self._exec_timer.setSingleShot(True)
        self._exec_timer.setInterval(300)
        self._exec_timer.timeout.connect(self._run_graph)

        # Señales
        self._canvas.node_selected.connect(self._details.load_node)
        self._canvas.graph_changed.connect(self._schedule_run)
        self._details.param_changed.connect(self._schedule_run)

        # Nodos por defecto ya conectados
        self._add_default_nodes()

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

        act_open = QAction("📂 Abrir imagen", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._open_image)
        tb.addAction(act_open)

        tb.addSeparator()

        act_run = QAction("▶ Ejecutar", self)
        act_run.setShortcut("Ctrl+Return")
        act_run.triggered.connect(self._run_graph)
        tb.addAction(act_run)

        act_clear = QAction("🗑 Limpiar", self)
        act_clear.triggered.connect(self._clear_canvas)
        tb.addAction(act_clear)

        tb.addSeparator()

        act_fit = QAction("⊡ Centrar (F)", self)
        act_fit.triggered.connect(self._canvas.fit_view)
        tb.addAction(act_fit)

    # ── Nodos por defecto ─────────────────────────────────

    def _add_default_nodes(self):
        """Crea InputImage → OutputImage conectados y listos."""
        inp = self.graph.add_node("input_image")
        out = self.graph.add_node("output_image")
        self.graph.connect(inp.node_id, out.node_id)   # ← conexión en el grafo
        self._canvas.add_node(inp, 60, 200)
        self._canvas.add_node(out, 280, 200)
        self._input_node_id = inp.node_id

        # Arista visual entre los dos nodos por defecto
        from ui.widgets.edge_item import EdgeItem
        src_item = self._canvas._node_items[inp.node_id]
        tgt_item = self._canvas._node_items[out.node_id]
        if src_item.output_ports and tgt_item.input_ports:
            edge = EdgeItem(
                src_item.output_ports[0].center_scene_pos(),
                tgt_item.input_ports[0].center_scene_pos(),
                source_id=inp.node_id,
                target_id=out.node_id,
            )
            self._canvas._scene.addItem(edge)
            self._canvas._edge_items.append(edge)

    def _get_input_node(self) -> InputImageNode | None:
        """Devuelve el nodo InputImage activo (el primero que encuentre)."""
        # Primero intenta con el id guardado
        if self._input_node_id and self._input_node_id in self.graph.nodes:
            node = self.graph.nodes[self._input_node_id]
            if isinstance(node, InputImageNode):
                return node
        # Fallback: busca cualquier InputImageNode
        for node in self.graph.nodes.values():
            if isinstance(node, InputImageNode):
                self._input_node_id = node.node_id
                return node
        return None

    # ── Carga de imagen ───────────────────────────────────

    def _load_image_path(self, path: str):
        img = cv2.imread(path)
        if img is None:
            QMessageBox.critical(self, "Error", f"No se pudo leer:\n{path}")
            return
        inp = self._get_input_node()
        if inp is None:
            QMessageBox.warning(self, "Sin nodo de entrada",
                                "Añade un nodo 'Input Image' al canvas primero.")
            return
        inp.set_image(img)
        h, w = img.shape[:2]
        self._status.showMessage(f"✅ Imagen cargada: {path}  ({w}×{h} px)")
        self._schedule_run()

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir imagen", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp)"
        )
        if path:
            self._load_image_path(path)

    # ── Drag & drop de imagen desde el explorador ─────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(self._is_image_url(u) for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if self._is_image_url(url):
                self._load_image_path(url.toLocalFile())
                break

    @staticmethod
    def _is_image_url(url: QUrl) -> bool:
        import os
        ext = os.path.splitext(url.toLocalFile())[1].lower()
        return ext in IMAGE_EXTS

    # ── Ejecución del grafo ───────────────────────────────

    def _schedule_run(self):
        self._exec_timer.start()

    def _run_graph(self):
        try:
            results = self.graph.execute()
            if not results:
                return

            # Mostrar el nodo de salida con más "ancestros" (el más al final del DAG)
            order = self.graph._topological_sort()
            # Filtra solo los que tienen resultado
            ordered_results = [nid for nid in order if nid in results]
            if not ordered_results:
                return

            last_id = ordered_results[-1]
            self._preview.show_image(results[last_id])
            self._status.showMessage(
                f"▶ Ejecutado · {len(results)} nodo(s) procesados"
            )
        except Exception as e:
            import traceback
            self._status.showMessage(f"❌ Error: {e}")
            print(traceback.format_exc())

    # ── Limpiar ───────────────────────────────────────────

    def _clear_canvas(self):
        self._canvas._scene.clear()
        self._canvas._node_items.clear()
        self._canvas._edge_items.clear()
        self.graph.nodes.clear()
        self.graph.edges.clear()
        self._input_node_id = None
        self._canvas._draw_grid()
        self._add_default_nodes()
        self._details.load_node(None)
        self._status.showMessage("Canvas limpiado.")
