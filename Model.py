r"""°°°
Class Structure
°°°"""
#|%%--%%| <o7S3MGfNLq|d1C9LohqaR>
import shapely
from shapely.lib import create_collection
import pandas as pd
import geopandas as gpd
import rasterio
import json

class Model:
    def __init__(self, roadpath, roadtypepath, drainpath, pondpath, flowpathpath, elevationpath, configpath):
        self.rainfall_data = json.load(open(configpath))['rainfall_values']
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
        self.G = nx.DiGraph()

    # Graph access

    def add_node(self, node:GraphNode):
        self.graph[node.index] = node.node
        self.build_graph()
        pass

    def get_node(self, point:shapely.geometry.Point):
        return self.graph.get(point)

    # run() / helper functions
    def build_graph(self):
        # Add nodes and edges to the graph
        for index, node_data in self.graph.items():
            # Add node with attributes
            self.G.add_node(index, label=node_data)

            # Add edge to child if exists
            if node_data['Child_Node'] is not None:
                self.G.add_edge(index, node_data['Child_Node'])

        try:
            list(nx.topological_sort(self.G))
        except Exception as e:
            raise RuntimeError(e)

        self._pdf_graph_view()

    # Visualize
    def _pdf_graph_view(self):
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.G, k=0.9, iterations=50)

        nx.draw_networkx_nodes(self.G, pos, node_color='lightblue', 
                                node_size=3000, alpha=0.8)

        nx.draw_networkx_edges(self.G, pos, edge_color='gray', 
                                arrows=True, arrowsize=20)

        node_labels = {node: str(node) for node in self.G.nodes()}
        nx.draw_networkx_labels(self.G, pos, labels=node_labels, 
                                 font_size=8, font_weight="bold")

        plt.axis('off')
        plt.tight_layout()
        plt.savefig('network_graph.pdf', bbox_inches='tight')
        plt.close()

class Data(Model):
    def __init__(self, model:Model, roadpath, roadtypepath, drainpath, pondpath, flowpathpath, elevationpath):
        self.model = model

        self.elevation = self.Elevation(elevationpath)
        self.drains = self.Drains(drainpath)
        self.ponds = self.Ponds(pondpath)
        self.flowpaths = self.Flowpaths(flowpathpath)
        self.roads = self.Roads(self, roadpath, roadtypepath)

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

            filtered_roads = self.roads.gdf[self.roads.gdf['DRAIN_IDX'] == point]
            road_type_index = filtered_roads.groupby('TYPE')['index'].apply(list).to_dict()
            road_type_length = filtered_roads.groupby('TYPE')['LENGTH'].sum().to_dict()
            road_type_area = filtered_roads.groupby('TYPE')['AREA'].sum().to_dict()
            child_node, distance_to_child = self.find_downhill_flowpath(point)

            node = GraphNode(point=point, node_type=node_type, elevation=elevation)
            node.node['Directly_Connected_Segments']['Indices'] = road_type_index
            node.node['Directly_Connected_Segments']['Length'] = road_type_length
            node.node['Directly_Connected_Segments']['Area'] = road_type_area
            node.node['Child_Node'] = child_node
            node.node['Distance_To_Child'] = distance_to_child

            self.model.graph.add_node(node=node)

        for _, row in self.ponds.gdf.iterrows():
            point = row.geometry
            node_type = "P"
            elevation = row['ELEVATION'][0]
            child_node, distance_to_child = self.find_downhill_flowpath(point)

            node = GraphNode(point=point, node_type=node_type, elevation=elevation)
            node.node['Child_Node'] = child_node
            node.node['Distance_To_Child'] = distance_to_child

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

    def find_downhill_flowpath(self, point):
        intersecting_flowpaths = self.flowpaths.gdf[self.flowpaths.gdf.intersects(point)]
        if len(intersecting_flowpaths) == 0: return None, None

        # Read the elevation raster
        with rasterio.open(elevationpath) as elevation_raster:
            # Function to get elevation of a point
            def get_point_elevation(pt):
                # Sample the raster at the point's coordinates
                elevation = list(elevation_raster.sample([(pt.x, pt.y)]))[0][0]
                return elevation

            # Candidate flowpaths that touch the point
            candidate_flowpaths = []
            for _, flowpath in intersecting_flowpaths.iterrows():
                # Get start and end points of the flowpath
                line_coords = list(flowpath.geometry.coords)
                start_point = shapely.geometry.Point(line_coords[0])
                end_point = shapely.geometry.Point(line_coords[-1])

                # Get elevations
                start_elev = get_point_elevation(start_point)
                end_elev = get_point_elevation(end_point)

                # Check if the point matches either start or end
                if (start_point.equals(point)) and (start_elev > end_elev):
                    candidate_flowpaths.append((flowpath, end_point))
                elif (end_point.equals(point)) and (end_elev > start_elev):
                    candidate_flowpaths.append((flowpath, start_point))

            # If multiple or no candidates, raise an exception or handle accordingly
            if len(candidate_flowpaths) != 1:
                print(f"\n\n\n\n>>>>POINT:{point}\nCADIDATE_FLOWPATHS:{candidate_flowpaths}<<<<")
                raise ValueError(f"Expected exactly one downhill flowpath, found {len(candidate_flowpaths)}")

            # Check for additional intersections at the end point
            end_point = candidate_flowpaths[0][1]
            end_point_buffer = end_point.buffer(0.3)

            # Check intersection with roads
            road_intersections = self.roads.gdf[self.roads.gdf.intersects(end_point_buffer)]
            if not road_intersections.empty:
                # Return the DRAIN_IDX of the intersecting road segment
                return road_intersections.iloc[0]['DRAIN_IDX'], candidate_flowpaths[0][0].geometry.length

            # Check intersection with ponds
            pond_intersections = self.ponds.gdf[self.ponds.gdf.intersects(end_point)]
            if not pond_intersections.empty:
                # Return the existing end point and flowpath length
                return candidate_flowpaths[0][1], candidate_flowpaths[0][0].geometry.length

            # Check intersection with drains
            drain_intersections = self.drains.gdf[self.drains.gdf.intersects(end_point)]
            if not drain_intersections.empty:
                # Return the existing end point and flowpath length
                return candidate_flowpaths[0][1], candidate_flowpaths[0][0].geometry.length

            return candidate_flowpaths[0][1], candidate_flowpaths[0][0].geometry.length


    class Roads:
        def __init__(self, data, roadpath, roadtypepath):
            self.data = data
            self.gdf : gpd.GeoDataFrame = gpd.read_file(roadpath)
            self.types = json.load(open(roadtypepath))['road_types']

            self._vd_index()
            self._vd_road_types()
            self._vd_length_and_area()

            self._pp_calculate_drain_connectivity()

        # Data Validation Functions
        def _vd_index(self):
            self.gdf['index'] = self.gdf['index'] if 'index' in self.gdf.columns else range(len(self.gdf))

        def _vd_road_types(self):
            unknown_types = set(self.gdf['TYPE']) - set(self.types)
            if unknown_types: raise ValueError(f"Unknown road types: {unknown_types}")

        def _vd_length_and_area(self):
            if (zero_indexes := [idx for idx, (length, area) in enumerate(zip(self.gdf['LENGTH'], self.gdf['AREA'])) if length <= 0 or area <= 0]):
                raise ValueError(f"Zero or negative LENGTH/AREA at road indexes: {zero_indexes}")


        # Pre-Processing Functions

        def _pp_calculate_drain_connectivity(self):
            self.gdf['INCL_DRAIN'], self.gdf['DRAIN_IDX'] = False, None

            # First, mark drain-intersecting road segments
            for drain in self.data.drains.gdf.geometry:
                intersecting_roads = self.gdf[self.gdf.geometry.apply(lambda road: drain.distance(road) <= 1e-9)]

                if len(intersecting_roads) == 0:
                    raise ValueError(f"Drain point {drain} does not intersect any road.")

                # Mark the first intersecting road segment
                idx = intersecting_roads.index[0]
                self.gdf.at[idx, 'INCL_DRAIN'] = True
                self.gdf.at[idx, 'DRAIN_IDX'] = drain

            # Process segments not directly connected to drains
            unroutable_segments = []
            for idx, road_segment in self.gdf[~self.gdf['INCL_DRAIN']].iterrows():
                current_segment = road_segment
                visited_segments = set()

                while not current_segment['INCL_DRAIN']:
                    # Find touching segments excluding already visited ones
                    touching_segments = self.gdf[
                        self.gdf.touches(current_segment.geometry) &
                        (~self.gdf.index.isin(visited_segments))
                    ]

                    # If no touching segments, mark as unroutable
                    if touching_segments.empty:
                        unroutable_segments.append(current_segment)
                        break

                    # Check for drain-touching segments
                    drain_connected_segments = touching_segments[touching_segments['INCL_DRAIN']]

                    if not drain_connected_segments.empty:
                        # Assign the drain of the first drain-touching segment
                        self.gdf.at[idx, 'DRAIN_IDX'] = drain_connected_segments.iloc[0]['DRAIN_IDX']
                        break

                    # Progress to lowest elevation segment to continue tracing
                    current_segment = touching_segments.loc[touching_segments['ELEVATION'].idxmin()]
                    visited_segments.add(current_segment.name)

            # Log unroutable segments if any exist
            if unroutable_segments:
                unroutable_length = sum(seg.geometry.length for seg in unroutable_segments)
                print(f"Total unroutable segment length: {unroutable_length}")
                print(f"Number of unroutable segments: {len(unroutable_segments)}")

            # self.gdf.to_file("drain_connectivity_analysis.shp")


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
configpath = 'config.json'

m = Model(
    roadpath=roadpath,
    roadtypepath=roadtypepath,
    drainpath=drainpath,
    pondpath=pondpath,
    flowpathpath=flowpathpath,
    elevationpath=elevationpath,
    configpath=configpath
)

#|%%--%%| <d1C9LohqaR|1eSca5QkZ3>

m.graph.graph

#|%%--%%| <1eSca5QkZ3|mMfRqQPgyA>


import graphviz

def visualize_node_graph(nodes_dict):
    # Create a new directed graph
    dot = graphviz.Digraph(comment='Node Graph', format='pdf')
    
    # Add nodes to the graph
    for index, node_data in nodes_dict.items():
        # Create a node label with key information
        node_label = f"Index: {index}\n" \
                     f"Type: {node_data['Type']}\n" \
                     f"Elevation: {node_data['Elevation']}\n" \
                     f"Directly_CS: {node_data['Directly_Connected_Segments']}"
        
        # Use the string representation of the index as the node identifier
        node_id = str(index)
        
        # Add the node to the graph
        dot.node(node_id, node_label)
        
        # Add edge to child if exists
        if node_data['Child_Node'] is not None:
            child_id = str(node_data['Child_Node'])
            dot.edge(node_id, child_id)
    
    # Render the graph
    dot.render('node_graph', view=True)

# Usage example
# Assuming 'nodes' is your dictionary of nodes
visualize_node_graph(m.graph.graph)


#|%%--%%| <mMfRqQPgyA|i4VxWMoHSx>


import networkx as nx
import matplotlib.pyplot as plt

def visualize_node_graph(nodes_dict):
    # Create a new directed graph
    G = nx.DiGraph()
    
    # Add nodes and edges to the graph
    for index, node_data in nodes_dict.items():
        # Add node with attributes
        G.add_node(index, label=node_data)
        nx.topological_sort(G)

        # Add edge to child if exists
        if node_data['Child_Node'] is not None:
            G.add_edge(index, node_data['Child_Node'])

    # Create figure and draw
    plt.figure(figsize=(12, 8))

    # Use spring layout for node positioning
    pos = nx.spring_layout(G, k=0.9, iterations=50)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                            node_size=3000, alpha=0.8)

    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                            arrows=True, arrowsize=20)

    # Draw labels
    node_labels = {node: G.nodes[node] for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=node_labels, 
                             font_size=8, font_weight="bold")

    # Remove axis
    plt.axis('off')

    # Show the plot
    plt.tight_layout()
    plt.show()

# Usage
visualize_node_graph(m.graph.graph)

#|%%--%%| <i4VxWMoHSx|61WfY9YjYK>


import networkx as nx
import matplotlib.pyplot as plt
import base64
from io import BytesIO

def export_networkx_graph_to_html(nodes_dict, output_file='network_graph.html'):
    # Create a new directed graph
    G = m.graph.G

    # Create figure and draw
    plt.figure(figsize=(12, 8))

    # Use spring layout for node positioning
    pos = nx.spring_layout(G, k=0.9, iterations=50)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                            node_size=3000, alpha=0.8)

    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                            arrows=True, arrowsize=20)

    # Draw labels
    node_labels = {node: str(node) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=node_labels, 
                             font_size=8, font_weight="bold")

    # Remove axis
    plt.axis('off')

    # Tight layout
    plt.tight_layout()

    # Save plot to a base64 encoded string
    buffer = BytesIO()
    plt.savefig('network_graph.pdf', bbox_inches='tight')
    plt.close()

# Usage
export_networkx_graph_to_html(m.graph.graph)

#|%%--%%| <61WfY9YjYK|POqeFoW0bl>



#|%%--%%| <POqeFoW0bl|W2IEaMA0wo>



