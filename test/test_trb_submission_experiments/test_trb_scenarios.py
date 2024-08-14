import unittest
from random import randint, seed
from unittest import TestCase

from mit_rail_sim.simulation_engine.passenger.arrival_rate import ArrivalRate
from mit_rail_sim.simulation_engine.schedule import WeibullSchedule
from mit_rail_sim.simulation_engine.simulation.replication_manager import (
    ReplicationManager,
)
from mit_rail_sim.simulation_engine.utils.logger_context import LoggerContext
from mit_rail_sim.simulation_engine.utils.logger_utils import (
    PassengerLogger,
    StationLogger,
    TrainLogger,
)
from mit_rail_sim.utils import project_root

from .factory.block_factory import BlockFactory
from .util.data_loader import DataLoader


class CTABlueLineTestCase(TestCase):
    def setUp(self):
        self.arrival_rates = ArrivalRate(filename="data/arrival_rates.csv")

        self.data_loader = DataLoader()
        self.block_factory = BlockFactory(self.arrival_rates)

        self.current_seed = self.data_loader.load_seed() or randint(0, 2**32 - 1)
        seed(self.current_seed)

        self.train_logger = TrainLogger(
            log_file_path="./test/test_trb_submission_experiments/results/train_test.csv",
            log_interval=50,
        )
        self.passenger_logger = PassengerLogger(
            log_file_path="./test/test_trb_submission_experiments/results/passenger_test.csv",
        )
        self.station_logger = StationLogger(
            log_file_path="./test/test_trb_submission_experiments/results/station_test.csv",
        )

        self.schedule = WeibullSchedule(
            num_trains=50,
            path_to_params_json_file=project_root / "weibull_params.json",
        )

    def test_moving_block_simulation_with_real_data_from_file(self):
        data = self.data_loader.load_data(project_root / "file.json")
        slow_zones = self.data_loader.read_slow_zones_from_json("test_slow_zones.json")

        logger_context = LoggerContext(
            self.train_logger, self.passenger_logger, self.station_logger
        )
        replication_manager = ReplicationManager(
            number_of_replications=10,
            logger_context=logger_context,
            train_speed_regulator="MovingBlock",
        )
        replication_manager.run_replications(
            schedule=self.schedule,
            path_initializer_function=lambda data,
            slow_zones: self.block_factory.create_path_and_control_center(
                data, slow_zones, "MovingBlock"
            ),
            data=data,
            slow_zones=slow_zones,
            total_time=7200 * 2,
        )

    def test_simulation_with_real_data_from_file(self):
        data = self.data_loader.load_data(project_root / "file.json")
        slow_zones = self.data_loader.read_slow_zones_from_json("test_slow_zones.json")

        logger_context = LoggerContext(
            self.train_logger, self.passenger_logger, self.station_logger
        )
        replication_manager = ReplicationManager(
            number_of_replications=10,
            logger_context=logger_context,
            train_speed_regulator="MovingBlock",
        )

        replication_manager.run_replications(
            schedule=self.schedule,
            path_initializer_function=lambda data,
            slow_zones: self.block_factory.create_path_and_control_center(
                data, slow_zones, block_type="FixedBlock"
            ),
            data=data,
            slow_zones=slow_zones,
            total_time=7200 * 2,
        )


if __name__ == "__main__":
    unittest.main()
