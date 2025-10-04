# /src/model/base.py
from typing import Dict, List
from utils import config
from model import graph
import shapely
from model import data

class Model:
    def __init__(self) -> None:
        # Load values from configuration file
        self.rainfall_values : List[float] = config.get_rainfall_values()
        self.floawpath_travel_cost : float = config.get_flowpath_travel_cost()
        self.road_types : Dict[str, config.RoadTypeData] = config.get_road_types()

        self.base_graph = graph.Graph()

        # TODO: Check that all CRS match

        self.base_graph.add_node( node=graph.GraphNode(point=shapely.geometry.Point(0,0), node_type=graph.NodeType.DRAIN, elevation=0.0), childNodePoint=shapely.geometry.Point(1,1), distanceToChild=2 )

        self.base_graph.add_node( node=graph.GraphNode(point=shapely.geometry.Point(1,1), node_type=graph.NodeType.DRAIN, elevation=0.0), childNodePoint=shapely.geometry.Point(2,2), distanceToChild=1 )

