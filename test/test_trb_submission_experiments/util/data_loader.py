import json
import os
from typing import List

from mit_rail_sim.simulation_engine.infrastructure.path import SlowZone


class DataLoader:
    def load_data(self, data_filename):
        with open(data_filename, "r") as file:
            return json.load(file)

    def load_seed(self):
        if os.path.exists("./latest_seed.txt"):
            with open("latest_seed.txt", "r") as seed_file:
                seed_value = int(seed_file.read())
                return seed_value
        return None

    def read_slow_zones_from_json(self, file_path: str) -> List[SlowZone]:
        with open(file_path, "r") as file:
            slow_zones_data = json.load(file)
        return [SlowZone.from_dict(data) for data in slow_zones_data]
