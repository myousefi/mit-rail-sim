from mit_rail_sim.utils import project_root
import json
import unittest
from random import choice, randint, seed, uniform
from typing import List
from unittest.mock import MagicMock

from mit_rail_sim.simulation_engine.infrastructure import (
    Block,
    Path,
    SignalControlCenter,
    SlowZone,
    Station,
)
from mit_rail_sim.simulation_engine.infrastructure.path import ShortTurningPath
from mit_rail_sim.simulation_engine.passenger import ArrivalRate
from mit_rail_sim.simulation_engine.schedule import (
    EmpiricalSchedule,
    GammaSchedule,
    OHareEmpiricalSchedule,
    Schedule,
)
from mit_rail_sim.simulation_engine.simulation import ReplicationManager
from mit_rail_sim.simulation_engine.utils import (
    LoggerContext,
    PassengerLogger,
    TrainLogger,
)
from mit_rail_sim.simulation_engine.utils.logger_utils import (
    BlockActivationLogger,
    NullTrainLogger,
    SimulationLogger,
    StationLogger,
)


def read_slow_zones_from_json(file_path: str) -> List[SlowZone]:
    with open(file_path, "r") as file:
        slow_zones_data = json.load(file)
    return [SlowZone.from_dict(data) for data in slow_zones_data]


class CTABlueLineTestCase(unittest.TestCase):
    def setUp(self):
        log_folder_path = "mit_rail_sim/validation/simulation_results/"
        self.train_logger = TrainLogger(
            log_file_path=log_folder_path + "/train_test.csv",
            log_interval=50,
        )

        # self.train_logger = NullTrainLogger()

        self.passenger_logger = PassengerLogger(
            log_file_path=log_folder_path + "/passenger_test.csv",
        )

        self.station_logger = StationLogger(
            log_file_path=log_folder_path + "/station_test.csv",
        )

        self.simulation_logger = SimulationLogger(
            log_file_path=log_folder_path + "/simulation_test.json",
        )

        self.block_logger = BlockActivationLogger(
            log_file_path=log_folder_path + "/block_test.csv",
        )

        self.arrival_rates = ArrivalRate(
            filename="mit_rail_sim/odx_arrival/data/arrival_rates_April_May.csv"
        )

    def test_simulation_with_real_data_from_file(self):
        data = self.load_data(project_root / "inputs" / "infra.json")

        slow_zones = read_slow_zones_from_json(
            project_root / "inputs" / "slow_zones.json"
        )

        logger_context = LoggerContext(
            self.train_logger,
            self.passenger_logger,
            self.station_logger,
            self.simulation_logger,
            self.block_logger,
        )

        # schedule = GammaSchedule(num_trains=300, mean=10 * 60, cv=0.0)
        schedule = EmpiricalSchedule(
            cleaned_data_filepath="data/emprical_schedule/cleaned_events.csv",
            start_time_of_day=0,
            end_time_of_day=23,
        )

        schedule = OHareEmpiricalSchedule(
            file_path="inputs/empirical-schedule/data/events.csv",
            start_time_of_day=0,
            end_time_of_day=23,
            cta_day_type="Weekday",
        )

        # schedule = MagicMock()
        # schedule.generate_random_dispatch_info = lambda: None
        # schedule.dispatch_info = [
        #     (300, 0, "ShortTurning"),
        #     (300, 0, "Northbound"),
        #     (700, 0, "Southbound"),
        # ]

        replication_manager = ReplicationManager(
            number_of_replications=1,
            logger_context=logger_context,
            train_speed_regulator="CTA",
        )

        replication_manager.run_replications(
            schedule=schedule,
            path_initializer_function=self.create_path_from_data_with_offscan_symptom,
            data=data,
            slow_zones=slow_zones,
            total_time=23 * 3600,
            start_hour=0,
        )

    def load_data(self, data_filename):
        with open(data_filename, "r") as file:
            return json.load(file)

    def create_path_from_data_with_offscan_symptom(
        self, data, slow_zones=[], direction="Northbound"
    ):
        # off_scans = []
        blocks = []
        paths = {}

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
                        arrival_rates=self.arrival_rates,
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

        paths["Southbound"].make_dispatching_block(
            block_id="NWD-739", dispatch_margin=0, upstream_blocks=["NWD-739"]
        )

        paths["ShortTurning"] = ShortTurningPath(
            nb_path=paths["Northbound"],
            sb_path=paths["Southbound"],
            nb_juncture_block_id="WC-16",
            sb_juncture_block_id="WD-13",
        )

        return paths, signal_control_center
