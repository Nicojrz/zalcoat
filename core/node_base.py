from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class NodeParam:
    """Descriptor de un parámetro de nodo para generar UI dinámicamente."""
    name: str
    label: str
    type: str          # "int", "float", "bool", "choice"
    default: Any
    min: Any = None
    max: Any = None
    step: Any = None
    choices: list = field(default_factory=list)


class BaseNode(ABC):
    node_type: str = ""
    label: str = ""
    category: str = "General"
    color: str = "#4A90D9"
    max_inputs: int = 1
    max_outputs: int = 1

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.params: dict = {p.name: p.default for p in self.param_descriptors()}
        self._cache: np.ndarray | None = None
        self._dirty: bool = True

    @abstractmethod
    def param_descriptors(self) -> list[NodeParam]:
        """Define los parámetros y sus tipos para generar el panel de detalles."""
        return []

    @abstractmethod
    def process(self, inputs: list[np.ndarray]) -> np.ndarray:
        """Lógica PDI del nodo. Recibe lista de imágenes, retorna una."""
        ...

    def set_param(self, name: str, value: Any):
        self.params[name] = value
        self._dirty = True

    def get_output(self, inputs: list[np.ndarray]) -> np.ndarray:
        if self._dirty or self._cache is None:
            self._cache = self.process(inputs)
            self._dirty = False
        return self._cache

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "params": self.params,
        }
