r"""°°°
Class Structure
°°°"""
#|%%--%%| <o7S3MGfNLq|d1C9LohqaR>
import shapely
import pandas as pd
import geopandas as gpd
import rasterio
import json

class Model:
    def __init__(self, roadpath, roadtypepath, drainpath, pondpath, flowpathpath, elevationpath):
        self.graph = Graph(model=self)
        self.data = Data(model=self, roadpath=roadpath, roadtypepath=roadtypepath, drainpath=drainpath, pondpath=pondpath, flowpathpath=flowpathpath, elevationpath=elevationpath)

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
    def __init__(self, model:Model):
        self.model = model

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
    def __init__(self, model:Model, roadpath, roadtypepath, drainpath, pondpath, flowpathpath, elevationpath):
        self.model = model

        self.elevation = self.Elevation(elevationpath)
        self.roads = self.Roads(roadpath, roadtypepath)
        self.drains = self.Drains(drainpath)
        self.ponds = self.Ponds(pondpath)
        self.flowpaths = self.Flowpaths(flowpathpath)

        self._vd_projections()
        self.create_graph()

    def _vd_projections(self):
        epsg_codes = [ obj.gdf.crs.to_epsg() for obj in [self.roads, self.drains, self.ponds, self.flowpaths] ]
        epsg_codes.extend( [ obj.md['crs'].to_epsg() for obj in [self.elevation] ] )

        if len(set(epsg_codes)) != 1: raise RuntimeError("Mismatching CRS")

    def create_graph(self):

        self._vd_data()

        # For point in drains+ponds, create a node in the graph, calculating Directly Connected Segments, Type, Elevation, Child Node, and Distance to Child
        for _, row in self.drains.gdf.iterrows():
            point = row.geometry
            node_type = "D"
            elevation = row['ELEVATION'][0]
            node = GraphNode(point=point, node_type=node_type, elevation=elevation)
            self.model.graph.add_node(node=node)

        for _, row in self.ponds.gdf.iterrows():
            point = row.geometry
            node_type = "P"
            elevation = row['ELEVATION'][0]
            node = GraphNode(point=point, node_type=node_type, elevation=elevation)
            self.model.graph.add_node(node=node)

    def _vd_data(self):

        # Roads - already called during Roads.__init__() but we run again in case changes were made
        self.roads._vd_road_types()
        self.roads._vd_length_and_area()


        # Flowpaths - already called during Flowpaths.__init__() but we run again in case changes were made
        self.flowpaths._vd_lines()


        # Validate that for all drain and pond points, there is only a single (or perhaps zero) flowpath connected to it that goes downhill.
        points_gdf = pd.concat([self.drains.gdf, self.ponds.gdf], ignore_index=True)
        invalid_flowpath_indexes = []

        with rasterio.open(elevationpath) as src:
            for _, point in points_gdf.iterrows():
                intersecting_paths = self.flowpaths.gdf[self.flowpaths.gdf.intersects(point['geometry'])]

                # Count downhill flowpaths
                downhill_paths = []
                for path_idx, path in intersecting_paths.iterrows():
                    # Sample start and end point elevations
                    start = shapely.geometry.Point(path.geometry.coords[0])
                    end = shapely.geometry.Point(path.geometry.coords[-1])

                    start_elev = list(src.sample([(start.x, start.y)]))[0]
                    end_elev = list(src.sample([(end.x, end.y)]))[0]

                    # Check if path goes downhill
                    if (start.intersects(point.geometry) and end_elev < point['ELEVATION']) or \
                       (end.intersects(point.geometry) and start_elev < point['ELEVATION']):
                        downhill_paths.append(path_idx)

                # Track invalid flowpath indexes
                if len(downhill_paths) > 1:
                    invalid_flowpath_indexes.extend(downhill_paths)

        if invalid_flowpath_indexes: raise ValueError(f"Multiple downhill flowpaths connected to the same node: {invalid_flowpath_indexes}")

        # Validation Continued...
        # TODO: This validation is incomplete, complete validation would require checking for intersecting flowpaths, ...

        pass

    class Roads:
        def __init__(self, roadpath, roadtypepath):
            self.gdf : gpd.GeoDataFrame = gpd.read_file(roadpath)
            self.types = json.load(open(roadtypepath))['road_types']

            self._vd_road_types()
            self._vd_length_and_area()

        # Data Validation Functions
        def _vd_road_types(self):
            unknown_types = set(self.gdf['TYPE']) - set(self.types)
            if unknown_types: raise ValueError(f"Unknown road types: {unknown_types}")

        def _vd_length_and_area(self):
            if (zero_indexes := [idx for idx, (length, area) in enumerate(zip(self.gdf['LENGTH'], self.gdf['AREA'])) if length <= 0 or area <= 0]):
                raise ValueError(f"Zero or negative LENGTH/AREA at road indexes: {zero_indexes}")


        # Pre-Processing Functions
        def _pp_calculate_idx(self):
            pass

        def _pp_calculate_drain_idx(self):
            pass

    class Drains:
        def __init__(self, drainpath):
            self.gdf : gpd.GeoDataFrame = gpd.read_file(drainpath)
            self._calculate_elevation()

        def _calculate_elevation(self):
            with rasterio.open(elevationpath) as src:
                self.gdf['ELEVATION'] = list(src.sample([(x, y) for x, y in zip(self.gdf["geometry"].x, self.gdf["geometry"].y)]))
                if (null_indexes := [i for i, x in enumerate(self.gdf['ELEVATION']) if x == src.nodata]):
                    raise ValueError(f"Features with null elevation at drain indexes: {null_indexes}")

        def _add_to_graph(self):
            pass

    class Ponds:
        def __init__(self, pondpath):
            self.gdf : gpd.GeoDataFrame = gpd.read_file(pondpath)
            self._calculate_elevation()

        def _calculate_elevation(self):
            with rasterio.open(elevationpath) as src:
                self.gdf['ELEVATION'] = list(src.sample([(x, y) for x, y in zip(self.gdf["geometry"].x, self.gdf["geometry"].y)]))
                if (null_indexes := [i for i, x in enumerate(self.gdf['ELEVATION']) if x == src.nodata]):
                    raise ValueError(f"Features with null elevation at pond indexes: {null_indexes}")

        def _add_to_graph(self):
            pass

    class Flowpaths:
        def __init__(self, flowpathpath):
            self.gdf = gpd.read_file(flowpathpath)
            self._vd_lines()

        def _vd_lines(self):
            invalid_indexes =  [idx for idx, line in enumerate(self.gdf.geometry) if not line.is_simple]
            if invalid_indexes: raise ValueError(f"Self-intersecting lines at indexes: {invalid_indexes}")

        def _is_downhill_path(self, path, point, elevation_src):
            start = shapely.geometry.Point(path.geometry.coords[0])
            end = shapely.geometry.Point(path.geometry.coords[-1])

            start_elev = list(elevation_src.sample([(start.x, start.y)]))[0]
            end_elev = list(elevation_src.sample([(end.x, end.y)]))[0]

            return (start.intersects(point.geometry) and end_elev < point['ELEVATION']) or \
                   (end.intersects(point.geometry) and start_elev < point['ELEVATION'])


    class Elevation:
        def __init__(self, elevationpath):

            with rasterio.open(elevationpath) as src:
                self.array = src.read()
                self.md = src.meta


roadpath = 'roads.shp'
roadtypepath = 'roadtypes.json'
drainpath = 'drains.shp'
pondpath = 'ponds.shp'
flowpathpath = 'flowpaths.shp'
elevationpath = 'elevation.tif'

m = Model(
    roadpath=roadpath,
    roadtypepath=roadtypepath,
    drainpath=drainpath,
    pondpath=pondpath,
    flowpathpath=flowpathpath,
    elevationpath=elevationpath
)

#|%%--%%| <d1C9LohqaR|1eSca5QkZ3>

m.graph.graph

#|%%--%%| <1eSca5QkZ3|W2IEaMA0wo>



