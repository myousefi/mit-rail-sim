from random import randint
from typing import Any, Dict, Optional, Union

from transit_lab_simmetro.simulation_engine.infrastructure.block import (
    Block,
    MovingBlock,
)
from transit_lab_simmetro.simulation_engine.infrastructure.moving_control_center import (
    MovingBlockControl,
)
from transit_lab_simmetro.simulation_engine.infrastructure.path import Path
from transit_lab_simmetro.simulation_engine.infrastructure.signal_control_center import (
    SignalControlCenter,
)
from transit_lab_simmetro.simulation_engine.infrastructure.station import Station


class BlockFactory:
    DEFAULT_SPEED_LIMIT = 55
    VISIBLE_DISTANCE_RANGE = (50, 1000)

    def __init__(self, arrival_rates):
        self.arrival_rates = arrival_rates

    def create_block(self, block_data: Dict[str, Any], block_type: str):
        block_id = block_data["BLOCK"]
        visible_distance = self.generate_visible_distance()
        length = int(block_data["DISTANCE"])
        default_speed_code = self.get_default_speed_code(block_data)
        speed_codes_to_communicate = self.get_speed_codes_to_communicate(block_data)
        station = self.create_station(block_data)

        block_params = {
            "block_id": block_id,
            "visible_distance": visible_distance,
            "length": length,
            "default_speed_code": default_speed_code,
            "speed_codes_to_communicate": speed_codes_to_communicate,
            "station": station,
        }

        if block_type == "MovingBlock":
            block_params.pop("speed_codes_to_communicate")
            return MovingBlock(**block_params)

        return Block(**block_params)

    def create_path_and_control_center(
        self,
        data,
        slow_zones,
        block_type,
        moving_block_safety_margin: Optional[float] = None,
        offscan_blocks=None,
    ):
        blocks = self.create_blocks(data, block_type)

        control_center: Union[SignalControlCenter, MovingBlockControl]

        if block_type == "FixedBlock":
            control_center = SignalControlCenter(blocks)
        elif block_type == "MovingBlock":
            if moving_block_safety_margin:
                control_center = MovingBlockControl(blocks, moving_block_safety_margin)
            else:
                control_center = MovingBlockControl(blocks)
        else:
            raise ValueError(f"Invalid block type: {block_type}")

        path = Path(blocks, slow_zones=slow_zones)
        self.make_dispatching_blocks(path, block_type)

        for offscan_block_index, offscan_probability in offscan_blocks:
            path.make_offscan_block(offscan_block_index, offscan_probability)

        return path, control_center

    def make_dispatching_blocks(self, path, block_type):
        if block_type == "FixedBlock":
            path.make_dispatching_block(
                block_index=0, dispatch_margin=0, upstream_blocks=["WC-470"]
            )
        elif block_type == "MovingBlock":
            path.make_dispatching_block(
                block_index=0, dispatch_margin=0, upstream_blocks=[]
            )

        path.make_dispatching_block(
            block_index=79,
            dispatch_margin=110,
            upstream_blocks=[
                "WC-32",
                "321",
                "WC-26",
                "WC-22",
                "311",
                "WC-16",
                "WC-11",
                "WC-8",
            ],
        )

    def create_blocks(self, data, block_type):
        blocks = []
        for block_data in data:
            block = self.create_block(block_data, block_type)
            blocks.append(block)
        return blocks

    def generate_visible_distance(self):
        return randint(*self.VISIBLE_DISTANCE_RANGE)

    def get_default_speed_code(self, block_data):
        return min(block_data["SPEED"], self.DEFAULT_SPEED_LIMIT)

    def get_speed_codes_to_communicate(self, block_data):
        return block_data.get("SPEED_CODES_TO_COMMUNICATE", None)

    def get_location_relative_to_block(self, station_data, start_stn):
        end_of_platform_milepost = int(station_data["END_OF_PLATFORM_MILEPOST"])
        location_relative_to_block = end_of_platform_milepost - start_stn
        if location_relative_to_block < 0:
            print(station_data["STATION_NAME"])
        return location_relative_to_block

    def create_station(self, block_data):
        if "STATION" not in block_data:
            return None

        station_data = block_data["STATION"]
        location_relative_to_block = self.get_location_relative_to_block(
            station_data, block_data["STARTSTN"]
        )

        return Station(
            station_name=station_data["STATION_NAME"],
            location_relative_to_block=location_relative_to_block,
            arrival_rates=self.arrival_rates,
        )
