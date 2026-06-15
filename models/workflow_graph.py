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
        self.invalidate_node_and_descendants(target_id)

    def disconnect(self, source_id: str, target_id: str):
        self.edges = [e for e in self.edges
                      if not (e.source_id == source_id and e.target_id == target_id)]
        self.invalidate_node_and_descendants(target_id)

    def invalidate_node_and_descendants(self, node_id: str):
        if node_id not in self.nodes:
            return
        queue = [node_id]
        visited: set[str] = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            node = self.nodes.get(current)
            if node is not None:
                node._dirty = True
            for edge in self.edges:
                if edge.source_id == current and edge.target_id not in visited:
                    queue.append(edge.target_id)

    def to_dict(self, node_positions: dict[str, tuple[float, float]] | None = None) -> dict:
        nodes = []
        for node_id, node in self.nodes.items():
            node_data = {
                "node_id": node_id,
                "node_type": node.node_type,
                "data": node.serialize(),
            }
            if node_positions and node_id in node_positions:
                x, y = node_positions[node_id]
                node_data["position"] = {"x": x, "y": y}
            nodes.append(node_data)

        edges = [{"source_id": e.source_id, "target_id": e.target_id}
                 for e in self.edges]

        return {
            "nodes": nodes,
            "edges": edges,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowGraph":
        graph = cls()
        for node_info in data.get("nodes", []):
            node_id = node_info["node_id"]
            node_type = node_info["node_type"]
            node_data = node_info.get("data", {})
            if node_type not in NODE_REGISTRY:
                raise ValueError(f"Unknown node type: {node_type}")
            node_cls = NODE_REGISTRY[node_type]
            if hasattr(node_cls, "deserialize"):
                node = node_cls.deserialize(node_id, node_data)
            else:
                node = node_cls(node_id)
                node.params.update(node_data.get("params", {}))
            graph.nodes[node_id] = node

        for edge_info in data.get("edges", []):
            source_id = edge_info["source_id"]
            target_id = edge_info["target_id"]
            if source_id in graph.nodes and target_id in graph.nodes:
                graph.edges.append(Edge(source_id, target_id))
        return graph

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
