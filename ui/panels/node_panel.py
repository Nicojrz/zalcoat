from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit
)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QColor
from core.nodes.all_nodes import NODE_REGISTRY


class NodePanel(QWidget):
    """Panel lateral con todos los tipos de nodo disponibles, agrupados por categoría."""

    def __init__(self):
        super().__init__()
        self.setFixedWidth(200)
        self.setStyleSheet("""
            QWidget { background: #1E2030; color: #CDD6F4; }
            QLineEdit {
                background: #2A2D3E; border: 1px solid #3A3D52;
                border-radius: 6px; padding: 4px 8px; color: #CDD6F4;
            }
            QTreeWidget {
                background: #1E2030; border: none; outline: none;
            }
            QTreeWidget::item { padding: 4px 6px; border-radius: 4px; }
            QTreeWidget::item:hover { background: #2A2D3E; }
            QTreeWidget::item:selected { background: #3A3D52; }
            QTreeWidget::branch { background: #1E2030; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Nodos")
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #7F849C; padding: 2px 0;")
        layout.addWidget(title)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar nodo...")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setDragEnabled(True)
        self._tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        layout.addWidget(self._tree)

        self._build_tree()
        self._tree.expandAll()

        # Override startDrag para pasar el node_type como mime data
        self._tree.startDrag = self._start_drag

    def _build_tree(self, filter_text: str = ""):
        self._tree.clear()
        categories: dict[str, list] = {}

        for node_type, cls in NODE_REGISTRY.items():
            if filter_text and filter_text.lower() not in cls.label.lower():
                continue
            cat = cls.category
            categories.setdefault(cat, []).append(cls)

        for cat, nodes in sorted(categories.items()):
            parent = QTreeWidgetItem(self._tree, [cat])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            parent.setForeground(0, QColor("#7F849C"))
            for cls in nodes:
                child = QTreeWidgetItem(parent, [cls.label])
                child.setData(0, Qt.ItemDataRole.UserRole, cls.node_type)
                child.setForeground(0, QColor(cls.color))

    def _filter(self, text: str):
        self._build_tree(text)
        self._tree.expandAll()

    def _start_drag(self, supported_actions):
        item = self._tree.currentItem()
        if item is None:
            return
        node_type = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_type:
            return
        mime = QMimeData()
        mime.setText(node_type)
        drag = QDrag(self._tree)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
