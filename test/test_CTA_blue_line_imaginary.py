import asyncio
import json
import os
import random
import unittest
from random import choice, randint, seed, uniform
from test.base_test_case import TrainMovementVisualizationMixin
from typing import List, Optional
from unittest.mock import MagicMock

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import plotly.io as pio
import plotly.subplots as sp
from plotly.subplots import make_subplots

from mit_rail_sim.simulation_engine.infrastructure import (
    Block,
    MovingBlock,
    MovingBlockControl,
    Path,
    SignalControlCenter,
    SlowZone,
    Station,
)
from mit_rail_sim.simulation_engine.passenger import ArrivalRate
from mit_rail_sim.simulation_engine.schedule import (
    EmpiricalSchedule,
    GammaSchedule,
    Schedule,
    WeibullSchedule,
)
from mit_rail_sim.simulation_engine.simulation import (
    ReplicationManager,
    SimulationContext,
)
from mit_rail_sim.simulation_engine.simulation.simulation import Simulation
from mit_rail_sim.simulation_engine.train import Train, TrainSpeedRegulator
from mit_rail_sim.simulation_engine.train.train import NextBlockNotFoundError
from mit_rail_sim.simulation_engine.utils import (
    BlockActivationLogger,
    LoggerContext,
    PassengerLogger,
    TrainLogger,
)
from mit_rail_sim.simulation_engine.utils.logger_utils import (
    SimulationLogger,
    StationLogger,
)
from mit_rail_sim.utils import project_root


def read_slow_zones_from_json(file_path: str) -> List[SlowZone]:
    with open(file_path, "r") as file:
        slow_zones_data = json.load(file)
    return [SlowZone.from_dict(data) for data in slow_zones_data]


class CTABlueLineTestCase(unittest.TestCase):
    def setUp(self):
        self.current_seed = self.load_seed() or randint(0, 2**32 - 1)
        seed(self.current_seed)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        HEADWAY = 700
        self.schedule = Schedule(40, HEADWAY, (-150, 150), alternate_start_block_index=79)

        self.train_logger = AsyncTrainLogger(
            log_file_path="./test/output_files/train_test.csv",
            log_interval=1,
        )
        self.passenger_logger = PassengerLogger(
            log_file_path="./test/output_files/passenger_test.csv",
        )

        self.station_logger = StationLogger(
            log_file_path="./test/output_files/station_test.csv",
        )

        self.simulation_logger = SimulationLogger(
            log_file_path="./test/output_files/simulation_test.json",
        )

        self.arrival_rates = ArrivalRate(filename="data/arrival_rates.csv")

    def tearDown(self):
        self.loop.close()

    def test_simulation_with_passengers(self):
        logger_context = LoggerContext(
            self.train_logger, self.passenger_logger, self.station_logger, self.simulation_logger
        )

        simulation = Simulation(
            schedule=self.schedule,
            path=self.path,
        )

        simulation_context = SimulationContext(simulation)

        with logger_context, simulation_context:
            simulation.run(7200 * 2)

    def test_moving_block_simulation_with_real_data_from_file(self):
        data = self.load_data(project_root / "file.json")
        slow_zones = read_slow_zones_from_json("test_slow_zones.json")

        logger_context = LoggerContext(
            self.train_logger, self.passenger_logger, self.station_logger, self.simulation_logger
        )

        replication_manager = ReplicationManager(
            number_of_replications=10, logger_context=logger_context
        )

        replication_manager.run_replications(
            schedule=Schedule(40, 40, (-1, 1), alternate_start_block_index=79),
            path_initializer_function=self.create_path_from_data_moving_block,
            data=data,
            slow_zones=[],
            total_time=7200 * 2,
        )

    async def test_simulation_with_real_data_from_file(self):
        data = self.load_data(project_root / "file.json")
        slow_zones = read_slow_zones_from_json("test_slow_zones.json")

        logger_context = LoggerContext(
            self.train_logger, self.passenger_logger, self.station_logger, self.simulation_logger
        )

        schedule = EmpiricalSchedule(
            cleaned_data_filepath="data/emprical_schedule/cleaned_events.csv",
            start_time_of_day=7,
            end_time_of_day=11,
        )

        # schedule = GammaSchedule(num_trains=20, mean=20, cv=0.2)

        replication_manager = ReplicationManager(
            number_of_replications=50, logger_context=logger_context, train_speed_regulator="CTA"
        )

        replication_manager.run_replications(
            schedule=schedule,
            path_initializer_function=self.create_path_from_data_with_offscan_symptom,
            data=data,
            slow_zones=slow_zones,
            total_time=7200 * 2,
        )

    def load_data(self, data_filename):
        with open(data_filename, "r") as file:
            return json.load(file)

    def create_path_from_data_with_offscan_symptom(self, data, slow_zones=[]):
        off_scans = []
        blocks = []

        for block_data in data:
            block_id = block_data["BLOCK"]
            visible_distance = randint(50, 1000)
            length = int(block_data["DISTANCE"])
            default_speed_code = min(block_data["SPEED"], 55)
            speed_codes_to_communicate = block_data["SPEED_CODES_TO_COMMUNICATE"]

            if "STATION" in block_data:
                station_data = block_data["STATION"]
                end_of_platform_milepost = int(station_data["END_OF_PLATFORM_MILEPOST"])
                start_stn = block_data["STARTSTN"]
                location_relative_to_block = end_of_platform_milepost - start_stn

                if location_relative_to_block < 0:
                    print(station_data["STATION_NAME"])

                station = Station(
                    station_name=station_data["STATION_NAME"],
                    location_relative_to_block=location_relative_to_block,
                    arrival_rates=self.arrival_rates,
                )
            else:
                station = None

            block = Block(
                block_id=block_id,
                visible_distance=visible_distance,
                length=length,
                default_speed_code=default_speed_code,
                speed_codes_to_communicate=speed_codes_to_communicate,
                station=station,
            )

            blocks.append(block)

        signal_control_center = SignalControlCenter(blocks)
        path = Path(blocks, slow_zones=slow_zones)
        path.make_dispatching_block(block_index=0, dispatch_margin=0, upstream_blocks=["WC-470"])
        path.make_dispatching_block(
            block_index=79,
            dispatch_margin=10,
            upstream_blocks=["321", "WC-26", "WC-22", "311", "WC-16", "WC-11", "WC-8"],
        )

        for offscan_block_index, offscan_probability in off_scans:
            path.make_offscan_block(offscan_block_index, offscan_probability)

        return path, signal_control_center

    def create_path_from_data(self, data, slow_zones=[]):
        blocks = []

        for block_data in data:
            block_id = block_data["BLOCK"]
            visible_distance = randint(50, 1000)
            length = int(block_data["DISTANCE"])
            default_speed_code = min(block_data["SPEED"], 55)
            speed_codes_to_communicate = block_data["SPEED_CODES_TO_COMMUNICATE"]

            if "STATION" in block_data:
                station_data = block_data["STATION"]
                end_of_platform_milepost = int(station_data["END_OF_PLATFORM_MILEPOST"])
                start_stn = block_data["STARTSTN"]
                location_relative_to_block = end_of_platform_milepost - start_stn

                if location_relative_to_block < 0:
                    print(station_data["STATION_NAME"])

                station = Station(
                    station_name=station_data["STATION_NAME"],
                    location_relative_to_block=location_relative_to_block,
                    arrival_rates=self.arrival_rates,
                )
            else:
                station = None

            block = Block(
                block_id=block_id,
                visible_distance=visible_distance,
                length=length,
                default_speed_code=default_speed_code,
                speed_codes_to_communicate=speed_codes_to_communicate,
                station=station,
            )

            blocks.append(block)

        signal_control_center = SignalControlCenter(blocks)
        path = Path(blocks, slow_zones=slow_zones)
        path.make_dispatching_block(block_index=0, dispatch_margin=0, upstream_blocks=["WC-470"])
        path.make_dispatching_block(
            block_index=79,
            dispatch_margin=110,
            upstream_blocks=["WC-32", "321", "WC-26", "WC-22", "311", "WC-16", "WC-11", "WC-8"],
        )

        return path, signal_control_center

    def create_path_from_data_moving_block(self, data, slow_zones=[]):
        blocks = []

        for block_data in data:
            block_id = block_data["BLOCK"]
            visible_distance = randint(50, 1000)
            length = int(block_data["DISTANCE"])
            default_speed_code = min(block_data["SPEED"], 55)

            if "STATION" in block_data:
                station_data = block_data["STATION"]
                end_of_platform_milepost = int(station_data["END_OF_PLATFORM_MILEPOST"])
                start_stn = block_data["STARTSTN"]
                location_relative_to_block = end_of_platform_milepost - start_stn

                if location_relative_to_block < 0:
                    print(station_data["STATION_NAME"])

                station = Station(
                    station_name=station_data["STATION_NAME"],
                    location_relative_to_block=location_relative_to_block,
                    arrival_rates=self.arrival_rates,
                )
            else:
                station = None

            block = MovingBlock(
                block_id=block_id,
                visible_distance=visible_distance,
                length=length,
                default_speed_code=default_speed_code,
                station=station,
            )

            blocks.append(block)

        moving_block_control = MovingBlockControl(blocks)
        path = Path(blocks, slow_zones=slow_zones)
        path.make_dispatching_block(block_index=0, dispatch_margin=0, upstream_blocks=[])
        path.make_dispatching_block(
            block_index=79,
            dispatch_margin=110,
            upstream_blocks=["WC-32", "321", "WC-26", "WC-22", "311", "WC-16"],
        )

        return path, moving_block_control

    def create_the_randomized_path(self):
        print(f"Using seed: {self.current_seed}")

        total_length = 26.93 * 1609.34
        speed_codes_mph = [25, 35, 45, 55]
        speed_codes_to_communicate_to_two_previous_blocks = [5, 10, 15, 20]
        num_blocks_between_stations = [3, 4, 5]
        station_names = [
            "O'Hare",
            "Rosemont",
            "Cumberland",
            "Harlem (O'Hare Branch)",
            "Jefferson Park",
            "Montrose",
            "Irving Park",
            "Addison",
            "Belmont",
            "Logan Square",
            "Western (O'Hare Branch)",
            "Damen",
            "Division",
            "Chicago",
            "Grand",
            "Clark/Lake",
            "Washington",
            "Monroe",
            "Jackson",
            "LaSalle",
            "Clinton",
            "UIC-Halsted",
            "Racine",
            "Illinois Medical District",
            "Western (Forest Park Branch)",
            "California",
            "Kedzie-Homan",
            "Pulaski",
            "Cicero",
            "Austin",
            "Oak Park",
            "Harlem (Forest Park Branch)",
            "Forest Park",
        ]

        avg_block_length = total_length / sum(num_blocks_between_stations)

        blocks = []
        block_id = 1
        for idx, station_name in enumerate(station_names[:-1]):
            num_blocks = choice(num_blocks_between_stations)
            for i in range(num_blocks):
                is_station = i == num_blocks - 1

                visible_distance = randint(50, 1000)
                length = int(avg_block_length / num_blocks)
                default_speed_code = choice(speed_codes_mph)
                speed_codes_to_communicate = (
                    {
                        f"Block_{block_id - 1:03}": 0,
                        f"Block_{block_id - 2:03}": choice(
                            speed_codes_to_communicate_to_two_previous_blocks[:-1]
                        ),
                    }
                    if block_id > 1
                    else {}
                )

                station = (
                    Station(
                        station_name=station_name,
                        location_relative_to_block=length // 2,
                        arrival_rates=self.arrival_rates,
                    )
                    if is_station
                    else None
                )

                block = AbstractBlock(
                    block_id=f"Block_{block_id:03}",
                    visible_distance=visible_distance,
                    length=length,
                    default_speed_code=default_speed_code,
                    speed_codes_to_communicate=speed_codes_to_communicate,
                    station=station,
                )

                blocks.append(block)
                block_id += 1

        self.signal_control_center = SignalControlCenter(blocks)
        self.path = Path(blocks)

    def save_seed(self, seed_value):
        with open("./latest_seed.txt", "w") as seed_file:
            seed_file.write(str(seed_value))

    def load_seed(self):
        if os.path.exists("./latest_seed.txt"):
            with open("latest_seed.txt", "r") as seed_file:
                seed_value = int(seed_file.read())
                return seed_value
        return None


class TestCTABlueLineTrainMovement(TrainMovementVisualizationMixin, CTABlueLineTestCase):
    @unittest.skip("Test is visual only")
    def test_single_train_movement(self):
        (
            speeds,
            times,
            distances,
            accelerations,
            planned_distances,
            current_speed_codes,
            distance_to_next_station_list,
            train_speed_regulator_states,
        ) = self._collect_train_data(1)

        self.visualize_time_profile(
            times,
            distances,
            "Distance from Start",
            train_speed_regulator_states=train_speed_regulator_states,
        )
        self.visualize_time_profile(
            times,
            speeds,
            "Speed",
            train_speed_regulator_states=train_speed_regulator_states,
        )
        self.visualize_distance_profiles(
            distances,
            distance_to_next_station_list,
            "Distance to Station",
            train_speed_regulator_states=train_speed_regulator_states,
        )
        self.visualize_distance_profiles(
            distances,
            speeds,
            "Speed",
            train_speed_regulator_states=train_speed_regulator_states,
            current_speed_codes=current_speed_codes,
        )
        self.visualize_distance_profiles(
            distances,
            accelerations,
            "Acceleration",
            train_speed_regulator_states=train_speed_regulator_states,
        )
        self.visualize_distance_profiles(
            distances,
            planned_distances,
            "Planning Distance",
            train_speed_regulator_states=train_speed_regulator_states,
        )


if __name__ == "__main__":
    unittest.main()
