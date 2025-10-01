from utils import config

class Model:
    def __init__(self):
        print(config.get_rainfall_values())
        print(config.get_travel_cost())
        print(config.get_road_types())
