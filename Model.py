r"""°°°
Class Structure
°°°"""
#|%%--%%| <o7S3MGfNLq|d1C9LohqaR>
import shapely
import geopandas as gpd
import rasterio
import json

class Model:
    def __init__(self, roadpath, roadtypepath, drainpath, pondpath, flowpathpath, elevationpath):
        self.graph = Graph()
        self.data = Data(roadpath=roadpath, roadtypepath=roadtypepath, drainpath=drainpath, pondpath=pondpath, flowpathpath=flowpathpath, elevationpath=elevationpath)

class GraphNode:
    def __init__(
            self,
            point : shapely.geometry.Point,
            node_type : str,
            elevation : float,
    ):
        self.index = point
        self.node = {
            'Type': node_type,  # Pond or Drain
            'Elevation': elevation,

            'Directly_Connected_Segments': {
                'Indices': {},  # Map organizing indices by ROAD_TYPE
                'Length': {},   # Total length per ROAD_TYPE
                'Area': {},     # Total area per ROAD_TYPE
                'Runoff': {},   # Total runoff from each ROAD_TYPE
                'Sediment': {}, # Total sediment from each ROAD_TYPE
            },

            'All_Connected_Segments': {
                'Indices': {},
                'Length': {},
                'Area': {},
                'Runoff': {},
                'Sediment': {},
            },

            'Runoff_Total': None,
            'Sediment_Total': None,

            'Pond_Max_Capacity': None,
            'Pond_Used_Capacity': None,

            'Parent_Nodes': [],
            'Child_Node': None,
            'Distance_To_Child': None,

            'Ancestor_Nodes': []
        }

class Graph(Model):
    def __init__(self):
        self.graph = {}  # Dictionary of GraphNodes

    # Graph access

    def add_node(self, node:GraphNode):
        self.graph[node.index] = node.node
        pass

    def get_node(self, point:shapely.geometry.Point):
        return self.graph.get(point)

    # run() / helper functions

    def run(self):
        pass

    def _vd_detect_cycles(self):
        pass

    def _pp_topological_sort(self):
        pass


    # Visualize
    def _html_graph_view(self):
        pass

class Data(Model):
    def __init__(self, roadpath, roadtypepath, drainpath, pondpath, flowpathpath, elevationpath):
        self.roads = self.Roads(roadpath, roadtypepath)
        self.drains = self.Drains(drainpath)
        self.ponds = self.Ponds(pondpath)
        self.flowpaths = self.Flowpaths(flowpathpath)
        self.elevation = self.Elevation(elevationpath)
        
        self._vd_projections()

    def _vd_projections(self):
        # TODO: `to_epsg()` should be same for all
        pass

    def create_graph(self):

        self._vd_data()

        # For point in drains+ponds, create a node in the graph, calculating Directly Connected Segments, Type, Elevation, Child Node, and Distance to Child
        for _, row in self.data.drains.gdf.itterows():
            point = row.geometry
            node_type = "D"
            elevation = 

            node = GraphNode(point=point, node_type=node_type, elevation=elevation)
            node.index = row.geometry
            node.node['Type'] = 'D'

            self.graph.add_node()

        for pond in self.data.ponds.gdf:
            self.graph.add_node()
        pass

    def _vd_data(self):

        # Roads
        self.roads._vd_road_types()
        self.roads._vd_length_and_area()

        # Flowpaths
        self.flowpaths._vd_lines()

        # Validate that Drains/Ponds are valid with Flowpaths
        # TODO: Validate that for all drain and pond points, there is only a single (or perhaps zero) flowpath connected to it that goes downhill.

        # Validate that Drains/Ponds are valid with Elevation
        # TODO: Make sure that is valid elevation data for all points

        # Validation Continued...
        # TODO: This validation is incomplete, complete validation would require checking for intersecting flowpaths, ...

        pass

    class Roads:
        def __init__(self, roadpath, roadtypepath):
            self.gdf : gpd.GeoDataFrame = gpd.read_file(roadpath)
            self.types = json.load(open(roadtypepath))['road_types']

        # Data Validation Functions
        def _vd_road_types(self):
            pass

        def _vd_length_and_area(self):
            pass

        # Pre-Processing Functions
        def _pp_calculate_idx(self):
            pass

        def _pp_calculate_drain_idx(self):
            pass

    class Drains:
        def __init__(self, drainpath):
            self.gdf : gpd.GeoDataFrame = gpd.read_file(drainpath)

        def _calculate_elevation(self):
            pass

        def _add_to_graph(self):
            pass

    class Ponds:
        def __init__(self, pondpath):
            self.gdf = gpd.read_file(pondpath)

        def read(self, drainpath):
            pass

        def _calculate_elevation(self):
            pass

        def _add_to_graph(self):
            pass

    class Flowpaths:
        def __init__(self, flowpathpath):
            self.gdf = gpd.read_file(flowpathpath)

        def _vd_lines(self):
            # TODO: Is non-branching
            pass

    class Elevation:
        def __init__(self, elevationpath):

            with rasterio.open(elevationpath) as src:
                self.array = src.read()
                self.md = src.meta


        def read(self, dempath):
            pass


#|%%--%%| <d1C9LohqaR|1eSca5QkZ3>

roadpath = 'roads.shp'
roadtypepath = 'roadtypes.ini'
drainpath = 'drains.shp'
pondpath = 'ponds.shp'
flowpathpath = 'flowpaths.shp'
elevationpath = 'elevation.tiff'

d = Data(
    roadpath=roadpath,
    roadtypepath=roadtypepath,
    drainpath=drainpath,
    pondpath=pondpath,
    flowpathpath=flowpathpath,
    elevationpath=elevationpath
)

#|%%--%%| <1eSca5QkZ3|tMPv2Swdwf>

import rasterio

with rasterio.open('../../CACHE/__EPSG_6566__EXTENT_-65_303_18_277_-65_281_18_302/DEM/dem.tif') as src:
    array = src.read()
    md = src.meta


md['crs'].to_epsg()
#|%%--%%| <tMPv2Swdwf|Wf4TDGZBFP>

import geopandas as gpd

gpd = gpd.read_file('../../CACHE/__EPSG_6566__EXTENT_-65_303_18_277_-65_281_18_302/ROAD/road_edges.shp')

gpd.crs.to_epsg()



#|%%--%%| <Wf4TDGZBFP|W2IEaMA0wo>



