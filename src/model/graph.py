from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List
import shapely.geometry
import networkx as nx

class NodeType(Enum):
    DRAIN = 1 # Anywhere you have runoff converging (i.e., road drains and converging flowpaths)
    POND = 2
    TERMINATION = 3

@dataclass
class ConnectedSegments:
    indices: Dict[str, List[int]] = field(default_factory=dict)
    length: Dict[str, float] = field(default_factory=dict)
    area: Dict[str, float] = field(default_factory=dict)
    runoff: Dict[str, float] = field(default_factory=dict)
    sediment: Dict[str, float] = field(default_factory=dict)

@dataclass
class GraphNode:
    point: shapely.geometry.Point
    node_type: NodeType
    elevation: float

    # Directly Connected Segments
    directly_connected_segments: ConnectedSegments = field(default_factory=ConnectedSegments)

    # All Connected Segments
    all_connected_segments: ConnectedSegments = field(default_factory=ConnectedSegments)

    # Runoff and Sediment Totals
    runoff_total: float | None = None
    sediment_total: float | None = None

    # Pond-specific properties
    pond_max_capacity: float | None = None
    pond_used_capacity: float | None = None
    pond_efficiency: float | None = None
    sediment_trapped: float | None = None

    # Node Relationships
    parent_nodes: List[shapely.geometry.Point] = field(default_factory=list)
    child_node: shapely.geometry.Point | None = None
    distance_to_child: float | None = None
    cost_required_to_connect_child: float | None = None

    ancestor_nodes: List[shapely.geometry.Point] = field(default_factory=list)

class Graph:
    def __init__(self) -> None:
        self.__G : nx.DiGraph = nx.DiGraph()

    def add_node(
            self, 
            node : GraphNode, 
            childNodePoint : shapely.geometry.Point | None = None, 
            distanceToChild : float | None = None
    ) -> None:
        if bool(childNodePoint) != bool(distanceToChild):
            raise ValueError("childNodePoint and distanceToChild must either both be None or non-None")

        self.__G.add_node(node.point, nodedata=node)

        if childNodePoint is not None:
            if not self.__G.has_node(childNodePoint):
                n = GraphNode(point=childNodePoint, )
                self.__G.add_node(childNodePoint, )

        self.__G.add_edge(node.point, childNodePoint, weight=distanceToChild)
