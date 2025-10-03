from typing import List
import geopandas as gpd
from pathlib import Path

from model.graph import GraphNode, NodeType
from utils import config
from . import roads, flowpaths, elevation

path: Path = config.resolve_ponds_data_path()
_gdf = gpd.read_file(path)

_gdf['ELEVATION'] = _gdf['geometry'].apply(lambda point: elevation.sample_point(point) )

def get_nodes() -> List[GraphNode]:
    nodes: List[GraphNode] = []
    for _, row in _gdf.iterrows():

        point = row.geometry
        node_type = NodeType.POND
        elevation = float(row['ELEVATION']) # Already is a float, this is just for the LSP
        node = GraphNode(point=point, node_type=node_type, elevation=elevation)

        pond_max_capacity = row['MAX_CAP']
        if not isinstance(pond_max_capacity, float): raise ValueError(f"Invalid pond MAX_CAP at {point}, expected float type, got {type(pond_max_capacity)}")
        node.pond_max_capacity = pond_max_capacity

        pond_used_capacity = row['USED_CAP']
        if not isinstance(pond_used_capacity, float): raise ValueError(f"Invalid pond USED_CAP at {point}, expected float type, got {type(pond_used_capacity)}")
        node.pond_used_capacity = pond_used_capacity

        child_node, distance_to_child = flowpaths.trace_drainage_endpoint(point)
        node.child_node = child_node
        node.distance_to_child = distance_to_child

        nodes.append(node)

    return nodes
