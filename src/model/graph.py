from dataclasses import dataclass, field
from typing import Dict, List, Optional
import shapely.geometry

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
    node_type: str
    elevation: float

    # Directly Connected Segments
    directly_connected_segments: ConnectedSegments = field(default_factory=ConnectedSegments)

    # All Connected Segments
    all_connected_segments: ConnectedSegments = field(default_factory=ConnectedSegments)

    # Runoff and Sediment Totals
    runoff_total: Optional[float] = None
    sediment_total: Optional[float] = None

    # Pond-specific properties
    pond_max_capacity: Optional[float] = None
    pond_used_capacity: Optional[float] = None
    pond_efficiency: Optional[float] = None
    sediment_trapped: Optional[float] = None

    # Node Relationships
    parent_nodes: List[shapely.geometry.Point] = field(default_factory=list)
    child_node: Optional[shapely.geometry.Point] = None
    distance_to_child: Optional[float] = None
    cost_required_to_connect_child: Optional[float] = None

    ancestor_nodes: List[shapely.geometry.Point] = field(default_factory=list)
