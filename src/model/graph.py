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

# Pond-specific properties
@dataclass
class PondInformation:
    max_capacity: float
    used_capacity: float

    @property
    def available_capacity(self) -> float:
        return self.max_capacity - self.used_capacity

    # Computed Values
    efficiency: float | None = None
    trapped_sediment: float | None = None
    trapped_runoff: float | None = None


@dataclass
class GraphNode:
    point: shapely.geometry.point.Point
    node_type: NodeType
    elevation: float

    # Directly Connected Segments
    directly_connected_segments: ConnectedSegments = field(default_factory=ConnectedSegments)

    # All Connected Segments
    all_connected_segments: ConnectedSegments = field(default_factory=ConnectedSegments)

    # Node Specific Data
    pond: PondInformation | None = None

    # Runoff and Sediment Totals
    total_runoff: float | None = None
    total_sediment: float | None = None

    # Node Relationships
    child: shapely.geometry.point.Point | None = None
    distance_to_child: float | None = None
    cost_to_connect_child: float | None = None

class Graph:
    def __init__(self) -> None:
        self.__G : nx.DiGraph = nx.DiGraph()

    def print(self):
        for node, data in self.__G.nodes(data=True):
            print(f"Node {node}: {data.get('nodedata')}")

    def conditionally_add_provisional_node(
        self,
        point: shapely.geometry.point.Point,
    ) -> None:

        from .data import elevation

        if not self.__G.has_node(point):
            terminal_node = GraphNode(point=point, node_type=NodeType.TERMINATION, elevation=elevation.sample_point(point))
            self.__G.add_node(point, nodedata=terminal_node)

    def add_node(
        self,
        node: GraphNode,
    ) -> None:
        if bool(node.child) != bool(node.distance_to_child):
            raise ValueError("child_node and distance_to_child must either both be None or non-None")

        self.__G.add_node(node.point, nodedata=node)

        if node.child is not None:
            self.conditionally_add_provisional_node(node.child)
            self.__G.add_edge(node.point, node.child, weight=node.distance_to_child)

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
        if nodedata.node_type == NodeType.POND: self.__process_pond_node(nodedata)

        nodedata.total_runoff = sum( nodedata.all_connected_segments.runoff.values() )
        nodedata.total_sediment = sum( nodedata.all_connected_segments.sediment.values() )

        if nodedata.child is not None:
            self.__process_child_node(
                parent_node_data=nodedata,
                child_node_data=self.__G.nodes[nodedata.child]['nodedata']
            )

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
        # TODO: Get the bulk density of sediments to update used_capacity between rainfall events

        if not nodedata.pond: raise ValueError(f"Pond node {nodedata.point} does not have have a pond structure!") # This should never be the case
        if not nodedata.total_runoff: return # total_runoff must be calculated before
        if not nodedata.total_sediment: return # total_sediment must be calculated before
        if not nodedata.total_runoff > 0: return # Early return if no runoff

        # Doesn't get used anywhere but I want this value in the output graph
        nodedata.pond.trapped_runoff = min(nodedata.pond.max_capacity, nodedata.total_runoff)

        # Don't worry, this can't be negative because of the calculation above
        runoff_out = nodedata.total_runoff - nodedata.pond.trapped_runoff

        if runoff_out == 0:
           nodedata.pond.efficiency = 1.0
        else:
            nodedata.pond.efficiency = float(np.clip(
                -22 + ( ( 119 * ( nodedata.pond.available_capacity / nodedata.total_runoff ) ) / ( 0.012 + 1.02 * (nodedata.pond.available_capacity / nodedata.total_runoff ) ) ),
                0, # Minimum Efficiency
                100 # Max Efficiency
            ) / 100) # Convert to percent

        nodedata.pond.trapped_sediment = nodedata.total_sediment * nodedata.pond.efficiency

    def __process_child_node(self, parent_node_data: GraphNode, child_node_data: GraphNode) -> None:
        if parent_node_data.total_runoff == None or parent_node_data.cost_to_connect_child == None: raise ValueError(f"{parent_node_data.node_type} {parent_node_data.point} is incomplete to compute child node (missing total_runoff and cost_to_connect_child)")

        match parent_node_data.node_type:
            case NodeType.POND:
                if parent_node_data.pond == None or parent_node_data.pond.trapped_runoff == None: raise ValueError(f"Pond node {parent_node_data.point} is incomplete to compute child node (missing pond.trapped_runoff)")

                volume_reaching_child = parent_node_data.total_runoff - parent_node_data.pond.trapped_runoff - parent_node_data.cost_to_connect_child

            case _:
                volume_reaching_child = parent_node_data.total_runoff - parent_node_data.cost_to_connect_child

        if volume_reaching_child <= 0: return

        # NOTE: What if for connected segmetns, we stored the values for each road type as a ratio? It'd make future calculations much easier

    def __calculate_delivery_ratio(self, volume_reaching_child: float, total_runoff: float) -> float:
        return volume_reaching_child / total_runoff
