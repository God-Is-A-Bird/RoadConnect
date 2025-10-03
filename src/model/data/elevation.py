import rasterio
import shapely
from pathlib import Path

from utils import config

path: Path = config.resolve_elevation_data_path()
__src = rasterio.open(path)

def sample_point(point: shapely.geometry.Point) -> float:
    return float(list(__src.sample( [point.xy] ))[0][0])
