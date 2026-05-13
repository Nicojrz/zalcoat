from __future__ import annotations
from dataclasses import dataclass, field
import uuid
import numpy as np
from core.node_base import BaseNode
from core.nodes.all_nodes import NODE_REGISTRY


@dataclass
class Edge:
    source_id: str
    target_id: str


class WorkflowGraph:
    def __init__(self):
        self.nodes: dict[str, BaseNode] = {}
        self.edges: list[Edge] = []

    # ── Nodos ──────────────────────────────────────────────
    def add_node(self, node_type: str, node_id: str | None = None) -> BaseNode:
        if node_type not in NODE_REGISTRY:
            raise ValueError(f"Unknown node type: {node_type}")
        nid = node_id or str(uuid.uuid4())[:8]
        node = NODE_REGISTRY[node_type](nid)
        self.nodes[nid] = node
        return node

    def remove_node(self, node_id: str):
        self.nodes.pop(node_id, None)
        self.edges = [e for e in self.edges
                      if e.source_id != node_id and e.target_id != node_id]

    # ── Aristas ────────────────────────────────────────────
    def connect(self, source_id: str, target_id: str):
        # Evita duplicados y auto-ciclos
        if source_id == target_id:
            return
        for e in self.edges:
            if e.source_id == source_id and e.target_id == target_id:
                return
        self.edges.append(Edge(source_id, target_id))
        # Invalida cache del target
        if target_id in self.nodes:
            self.nodes[target_id]._dirty = True

    def disconnect(self, source_id: str, target_id: str):
        self.edges = [e for e in self.edges
                      if not (e.source_id == source_id and e.target_id == target_id)]

    # ── Ejecución ──────────────────────────────────────────
    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm."""
        in_degree = {nid: 0 for nid in self.nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in self.nodes}

        for e in self.edges:
            if e.source_id in self.nodes and e.target_id in self.nodes:
                adjacency[e.source_id].append(e.target_id)
                in_degree[e.target_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for neighbour in adjacency[nid]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)
        return order

    def _inputs_for(self, node_id: str) -> list[np.ndarray]:
        sources = [e.source_id for e in self.edges if e.target_id == node_id]
        inputs = [self.nodes[sid]._cache for sid in sources
                if sid in self.nodes and self.nodes[sid]._cache is not None]
        if sources and not inputs:
            print(f"[WorkflowGraph] Warning: {node_id} has {len(sources)} source(s) but got {len(inputs)} valid input(s)")
            for sid in sources:
                if sid in self.nodes:
                    cache_status = "None" if self.nodes[sid]._cache is None else f"shape={self.nodes[sid]._cache.shape}"
                    print(f"  - Source {sid}: _cache={cache_status}")
        return inputs

    def execute(self) -> dict[str, np.ndarray]:
        """Ejecuta todos los nodos en orden topológico. Retorna {node_id: output}."""
        order = self._topological_sort()
        results = {}
        for nid in order:
            node = self.nodes[nid]
            inputs = self._inputs_for(nid)
            try:
                output = node.get_output(inputs)
                results[nid] = output
            except Exception as exc:
                import traceback
                print(f"[WorkflowGraph] Error en nodo {nid} ({node.node_type}): {exc}")
                print(traceback.format_exc())
                # Retorna una imagen negra como fallback para no romper el flujo
                results[nid] = np.zeros((256, 256, 3), dtype=np.uint8)
        return results
