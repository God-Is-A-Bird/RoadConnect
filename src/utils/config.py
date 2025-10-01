import os
import json
from typing import List, Dict, TypedDict

CONFIG_PATH = os.path.join(
        os.getcwd(),
        'config', 
        'config.json'
    )

def get_rainfall_values() -> List[float]:
    try:
        with open(CONFIG_PATH, 'r') as config_file:
            config_data = json.load(config_file)

            rainfall_values = config_data['rainfall_values']

            try:
                validated_values = [float(value) for value in rainfall_values]
                return validated_values
            except (TypeError, ValueError):
                raise ValueError("rainfall_values must be a list of numbers that can be converted to float")

    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
    except KeyError:
        raise KeyError("'rainfall_values' not found in the configuration file")

def get_travel_cost() -> float:
    try:
        with open(CONFIG_PATH, 'r') as config_file:
            config_data = json.load(config_file)

            # Extract travel cost
            travel_cost = config_data['travel_cost']

            # Validate type (must be int or float)
            if not isinstance(travel_cost, (int, float)):
                raise ValueError("travel_cost must be a number (int or float)")

            # Convert to float
            travel_cost = float(travel_cost)

            # Validate non-negative
            if travel_cost < 0:
                raise ValueError("travel_cost must be zero or a positive number")

            return travel_cost

    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
    except KeyError:
        raise KeyError("'travel_cost' not found in the configuration file")

class RoadTypeData(TypedDict):
    runoff_coefficient: float
    erosion_rate: float

def get_road_types() -> Dict[str, RoadTypeData]:

    try:
        with open(CONFIG_PATH, 'r') as config_file:
            config_data = json.load(config_file)

            # Extract road types
            road_types = config_data['road_types']

            # Validate overall structure
            if not isinstance(road_types, dict):
                raise ValueError("road_types must be a dictionary")

            # Validate each road type
            validated_road_types: Dict[str, RoadTypeData] = {}
            for road_type, type_data in road_types.items():
                # Validate road type is a string
                if not isinstance(road_type, str):
                    raise ValueError(f"Road type key must be a string, got {type(road_type)}")

                # Validate each road type has the correct structure
                if not isinstance(type_data, dict):
                    raise ValueError(f"Road type data for '{road_type}' must be a dictionary")

                # Validate required keys and their types
                if set(type_data.keys()) != {'runoff_coefficient', 'erosion_rate'}:
                    raise ValueError(f"Road type '{road_type}' must have exactly 'runoff_coefficient' and 'erosion_rate' keys")

                # Validate and extract runoff coefficient
                runoff_coefficient = type_data['runoff_coefficient']
                if not isinstance(runoff_coefficient, (int, float)):
                    raise ValueError(f"runoff_coefficient for '{road_type}' must be a number")

                # Validate and extract erosion rate
                erosion_rate = type_data['erosion_rate']
                if not isinstance(erosion_rate, (int, float)):
                    raise ValueError(f"erosion_rate for '{road_type}' must be a number")

                # Store validated and converted data
                validated_road_types[road_type] = {
                    'runoff_coefficient': float(runoff_coefficient),
                    'erosion_rate': float(erosion_rate)
                }

            return validated_road_types

    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
    except KeyError:
        raise KeyError("'road_types' not found in the configuration file")
