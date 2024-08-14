import json
from random import randint
from typing import List, Dict, Tuple

from mit_rail_sim import config_handler
from mit_rail_sim.simulation_engine.infrastructure import SlowZone, Path, SignalControlCenter, Station, Block
from mit_rail_sim.simulation_engine.infrastructure.path import ShortTurningPath, ShortTurningAtWestern
from mit_rail_sim.simulation_engine.passenger import ArrivalRate


def read_slow_zones_from_json(file_path: str) -> List[SlowZone]:
    with open(file_path, "r") as file:
        slow_zones_data = json.load(file)
    return [SlowZone.from_dict(data) for data in slow_zones_data]


def load_data(data_filename: str):
    with open(data_filename, "r") as file:
        return json.load(file)


def create_path_from_data_with_offscan_symptom(
    data: Dict, slow_zones: List[SlowZone], arrival_rates: ArrivalRate
) -> Tuple[Dict[str, Path], SignalControlCenter]:
    # off_scans = []
    blocks = []
    paths = {}

    cfg = config_handler.get_config()

    for direction in ["Northbound", "Southbound"]:
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

    paths["Northbound"].make_dispatching_block(
        block_id="WC-470", dispatch_margin=0, upstream_blocks=["WC-470"]
    )

    paths["Northbound"].make_dispatching_block(
        block_id="WC-16",
        dispatch_margin=80,
        upstream_blocks=[
            "WC-35",
            "WC-32",
            "321",
            "WC-26",
            "WC-22",
            "311",
            "WC-16",
            # "WC-11",
            # "WC-8",
        ],
    )

    paths["Northbound"].make_dispatching_block(
        block_id="WC-104",
        dispatch_margin=80,
        upstream_blocks=[
            "WC-104",
            "621",
            "WC-111",
            "WC-117",
            "WC-125",
            "WC-130",
            "WC-138",
            "WC-144",
            "WC-151",
            "WC-158",
        ],
    )

    paths["Southbound"].make_dispatching_block(
        block_id="NWD-739", dispatch_margin=0, upstream_blocks=["NWD-739"]
    )

    if cfg.short_turning == "UIC":
        paths["ShortTurning"] = ShortTurningPath(
            nb_path=paths["Northbound"],
            sb_path=paths["Southbound"],
            nb_juncture_block_id="WC-16",
            sb_juncture_block_id="WD-13",
        )
    elif cfg.short_turning == "Western":
        paths["ShortTurning"] = ShortTurningAtWestern(
            nb_path=paths["Northbound"],
            sb_path=paths["Southbound"],
            nb_juncture_block_id="WC-104",
            sb_juncture_block_id="WD-111",
        )

    else:
        raise Exception("Invalid short turning type")

    return paths, signal_control_center
