import json
from random import randint
from typing import List, Dict, Tuple

from transit_lab_simmetro import config_handler
from transit_lab_simmetro.simulation_engine.infrastructure import (
    SlowZone,
    Path,
    SignalControlCenter,
    Station,
    Block,
)
from transit_lab_simmetro.simulation_engine.infrastructure.path import (
    ShortTurningPath,
    ShortTurningAtWestern,
)
from transit_lab_simmetro.simulation_engine.passenger import ArrivalRate


class PathConfigLoader:
    def __init__(self, path_config_file):
        with open(path_config_file, "r") as f:
            self.config = json.load(f)

    def get_directions(self):
        return self.config["directions"]

    def get_dispatching_blocks(self):
        return self.config["dispatching_blocks"]

    def get_short_turning_config(self, short_turning_type):
        return self.config["short_turning"][short_turning_type]


def read_slow_zones_from_json(file_path: str) -> List[SlowZone]:
    with open(file_path, "r") as file:
        slow_zones_data = json.load(file)
    return [SlowZone.from_dict(data) for data in slow_zones_data]


def load_data(data_filename: str):
    with open(data_filename, "r") as file:
        return json.load(file)


def create_path_from_data_with_offscan_symptom(
    data: Dict,
    slow_zones: List[SlowZone],
    arrival_rates: ArrivalRate,
    path_config_loader: PathConfigLoader,
) -> Tuple[Dict[str, Path], SignalControlCenter]:
    blocks = []
    paths = {}

    cfg = config_handler.get_config()

    for direction in path_config_loader.get_directions():
        path_blocks = []
        for block_data in data[direction]:
            block_id = block_data["BLOCK"]
            block_alt_name = block_data["BLOCK_ALT"]
            visible_distance = randint(50, 1000)
            length = int(block_data["DISTANCE"])
            default_speed_code = min(block_data["SPEED"], 55)
            speed_codes_to_communicate = block_data["SPEED_CODES_TO_COMMUNICATE"]

            if "STATION" in block_data:
                station_data = block_data["STATION"]
                end_of_platform_milepost = int(station_data["END_OF_PLATFORM_MILEPOST"])
                start_stn = block_data["STARTSTN"]

                location_relative_to_block = abs(start_stn - end_of_platform_milepost)

                if location_relative_to_block < 0:
                    print(station_data["STATION_NAME"])

                station = Station(
                    station_name=station_data["STATION_NAME"],
                    location_relative_to_block=location_relative_to_block,
                    direction=direction,
                    arrival_rates=arrival_rates,
                )

            else:
                station = None

            block = Block(
                block_id=block_id,
                block_alt_name=block_alt_name,
                visible_distance=visible_distance,
                length=length,
                default_speed_code=default_speed_code,
                speed_codes_to_communicate=speed_codes_to_communicate,
                station=station,
            )

            blocks.append(block)
            path_blocks.append(block)

        paths[direction] = Path(direction, path_blocks, slow_zones=slow_zones)

    signal_control_center = SignalControlCenter(blocks)

    for dispatching_block in path_config_loader.get_dispatching_blocks():
        paths[dispatching_block["direction"]].make_dispatching_block(
            block_id=dispatching_block["block_id"],
            dispatch_margin=dispatching_block["dispatch_margin"],
            upstream_blocks=dispatching_block["upstream_blocks"],
        )

    short_turning_config = path_config_loader.get_short_turning_config(
        cfg.short_turning
    )
    if cfg.short_turning == "UIC":
        paths["ShortTurning"] = ShortTurningPath(
            nb_path=paths["Northbound"],
            sb_path=paths["Southbound"],
            nb_juncture_block_id=short_turning_config["nb_juncture_block_id"],
            sb_juncture_block_id=short_turning_config["sb_juncture_block_id"],
        )
    elif cfg.short_turning == "Western":
        paths["ShortTurning"] = ShortTurningAtWestern(
            nb_path=paths["Northbound"],
            sb_path=paths["Southbound"],
            nb_juncture_block_id=short_turning_config["nb_juncture_block_id"],
            sb_juncture_block_id=short_turning_config["sb_juncture_block_id"],
        )
    else:
        raise Exception("Invalid short turning type")

    return paths, signal_control_center
