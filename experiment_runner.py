import os
import shutil
import sys
from random import randint, seed
from test.test_trb_submission_experiments.factory.block_factory import BlockFactory
from test.test_trb_submission_experiments.util.data_loader import DataLoader

import hydra
from omegaconf import DictConfig

from mit_rail_sim.simulation_engine.passenger.arrival_rate import ArrivalRate
from mit_rail_sim.simulation_engine.schedule import GammaSchedule, Schedule
from mit_rail_sim.simulation_engine.simulation.replication_manager import (
    ReplicationManager,
)
from mit_rail_sim.simulation_engine.utils.logger_context import LoggerContext
from mit_rail_sim.simulation_engine.utils.logger_utils import (
    NullTrainLogger,
    PassengerLogger,
    StationLogger,
    TrainLogger,
)
from mit_rail_sim.utils import project_root


class CTABlueLineSimulator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.arrival_rates = ArrivalRate(filename=project_root / "data" / "arrival_rates.csv")
        self.data_loader = DataLoader()
        self.block_factory = BlockFactory(self.arrival_rates)
        self.current_seed = self.data_loader.load_seed() or randint(0, 2**32 - 1)
        seed(self.current_seed)

        # Construct log file paths
        base_path = os.path.join(cfg.log_file_base_path, cfg.signal_system.log_file_suffix)
        # Check if path exists and exit if it does
        if os.path.exists(base_path):
            # raise RuntimeError(f"Path {base_path} already exists. Stopping experiment.")
            print(f"Warning: Path {base_path} already exists. Clearing the directory.")
            shutil.rmtree(base_path)

        os.makedirs(base_path, exist_ok=True)
        train_log_file_path = os.path.join(base_path, "train_test.csv")
        passenger_log_file_path = os.path.join(base_path, "passenger_test.csv")
        station_log_file_path = os.path.join(base_path, "station_test.csv")

        # self.train_logger = TrainLogger(log_file_path=train_log_file_path, log_interval=10)
        self.train_logger = NullTrainLogger()
        self.passenger_logger = PassengerLogger(log_file_path=passenger_log_file_path)
        self.station_logger = StationLogger(log_file_path=station_log_file_path)

    def run_simulation(self):
        data = self.data_loader.load_data(project_root / "file.json")
        slow_zones_file_path = (
            project_root / "test_slow_zones_uniform.json"
            if self.cfg.which_slow_zones == "uniform"
            else project_root / "test_slow_zones.json"
        )
        slow_zones = (
            self.data_loader.read_slow_zones_from_json(slow_zones_file_path)
            if self.cfg.use_slow_zones
            else []
        )

        logger_context = LoggerContext(
            self.train_logger, self.passenger_logger, self.station_logger
        )
        replication_manager = ReplicationManager(
            number_of_replications=self.cfg.replication_count,
            logger_context=logger_context,
            train_speed_regulator=self.cfg.signal_system.block_type,
        )

        replication_manager.run_replications(
            schedule=GammaSchedule(num_trains=100, mean=self.cfg.headway, cv=self.cfg.cv_headway),
            path_initializer_function=lambda data, slow_zones: self.block_factory.create_path_and_control_center(
                data,
                slow_zones,
                block_type=self.cfg.signal_system.block_type,
                moving_block_safety_margin=200
                if self.cfg.signal_system.block_type == "MovingBlock"
                else None,
                offscan_blocks=[(self.cfg.offscan_symptomatic_block, self.cfg.offscan_probability)],
            ),
            data=data,
            slow_zones=slow_zones,
            total_time=7200 * 2,
        )


@hydra.main(config_path="conf", config_name="config")
def my_app(cfg: DictConfig) -> None:
    simulator = CTABlueLineSimulator(cfg)
    simulator.run_simulation()


if __name__ == "__main__":
    my_app()
