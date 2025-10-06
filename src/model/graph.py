from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List
import shapely.geometry
import networkx as nx
import numpy as np

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

    def print(self):
        for node, data in self.__G.nodes(data=True):
            print(f"Node {node}: {data.get('nodedata')}")

    def conditionally_add_provisional_node(
        self,
        point: shapely.geometry.Point,
    ) -> None:

        from .data import elevation

        if not self.__G.has_node(point):
            terminal_node = GraphNode(point=point, node_type=NodeType.TERMINATION, elevation=elevation.sample_point(point))
            self.__G.add_node(point, nodedata=terminal_node)

    def add_node(
        self,
        node: GraphNode,
    ) -> None:
        if bool(node.child_node) != bool(node.distance_to_child):
            raise ValueError("child_node and distance_to_child must either both be None or non-None")

        self.__G.add_node(node.point, nodedata=node)

        if node.child_node is not None:
            self.conditionally_add_provisional_node(node.child_node)
            self.__G.add_edge(node.point, node.child_node, weight=node.distance_to_child)

    def add_nodes(
        self,
        nodes: List[GraphNode]
    ) -> None:
        for node in nodes: 
            self.add_node(node)
            if not nx.is_directed_acyclic_graph(self.__G):
                raise ValueError(f"Adding point {node.point} made the graph cycle.")

    def get_topological_order(self) -> List[shapely.geometry.point.Point]:
        return list(nx.topological_sort(self.__G))

    def prepare_graph(self, rainfall_event_size: float) -> None:
        from utils import config

        self.flowpath_travel_cost: float = config.get_flowpath_travel_cost()
        self.road_types: Dict[str, config.RoadTypeData] = config.get_road_types()
        self.rainfall_event_size = rainfall_event_size

        self.__G.clear_edges() # We're only going to add edges if runoff > cost

    def process_node(self, point: shapely.geometry.point.Point):
        nodedata = self.__G.nodes[point]['nodedata']

        if not isinstance(nodedata, GraphNode):
            raise ValueError("Node in processing list is somehow not in the graph, this should never happen!")

        self.__process_directly_connected_segments(nodedata.directly_connected_segments)
        self.__process_all_connected_segments(nodedata)

        nodedata.runoff_total = sum( nodedata.all_connected_segments.runoff.values() )
        nodedata.sediment_total = sum( nodedata.all_connected_segments.sediment.values() )



    def __process_directly_connected_segments(self, d_conn_seg: ConnectedSegments):

        # Process Runoff
        d_conn_seg.runoff = { key: value * (self.rainfall_event_size/1000) * self.road_types[key]['runoff_coefficient'] for key, value in d_conn_seg.area.items() }

        # Process Sediment
        d_conn_seg.sediment = { key: (self.rainfall_event_size/1000) * self.road_types[key]['erosion_rate'] * d_conn_seg.area[key] for key, value in d_conn_seg.runoff.items() if value > 0 }

    def __process_all_connected_segments(self, nodedata: GraphNode ) -> None:

        # Process Indices
        for k, v in nodedata.directly_connected_segments.indices.items():
            nodedata.all_connected_segments.indices[k] = nodedata.all_connected_segments.indices.get(k, []) + v

        # Process Length
        for k, v in nodedata.directly_connected_segments.length.items():
            nodedata.all_connected_segments.length[k] = nodedata.all_connected_segments.length.get(k, 0) + v

        # Process Area
        for k, v in nodedata.directly_connected_segments.area.items():
            nodedata.all_connected_segments.area[k] = nodedata.all_connected_segments.area.get(k, 0) + v

        # Process Runoff
        for k, v in nodedata.directly_connected_segments.runoff.items():
            nodedata.all_connected_segments.runoff[k] = nodedata.all_connected_segments.runoff.get(k, 0) + v

        # Process Sediment
        for k, v in nodedata.directly_connected_segments.sediment.items():
            nodedata.all_connected_segments.sediment[k] = nodedata.all_connected_segments.sediment.get(k, 0) + v

    def __process_pond_node(self, nodedata: GraphNode):
        # TODO: I need to clarify that when we're calculating the pond eff, is the runoff the total from before or after subtracting the pond volume
        if not nodedata.runoff_total: return # runoff_total must be calculated before
        if not nodedata.sediment_total: return # sediment_total must be calculated before
        if not nodedata.runoff_total > 0: return # Early return if no runoff
        if not nodedata.pond_max_capacity or not nodedata.pond_used_capacity: raise ValueError(f"Pond {nodedata.point} has no 'MAX_CAP' and 'USED_CAP' attribute!")

        nodedata.pond_efficiency = float(np.clip(
            -22 + ( ( 119 * ( ( nodedata.pond_max_capacity - nodedata.pond_used_capacity ) / nodedata.runoff_total ) ) / ( 0.012 + 1.02 * ((nodedata.pond_max_capacity - nodedata.pond_used_capacity) / nodedata.runoff_total ) ) ),
            0, # Minimum Efficiency
            100 # Max Efficiency
        ) / 100) # Turn to percent

        nodedata.sediment_trapped = nodedata.sediment_total * nodedata.pond_efficiency
