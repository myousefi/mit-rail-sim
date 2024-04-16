from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.utils import BlockActivationLogger
    from mit_rail_sim.simulation_engine.utils import TrainLogger, PassengerLogger, StationLogger
    from mit_rail_sim.simulation_engine.utils.logger_utils import SimulationLogger

from mit_rail_sim.simulation_engine.infrastructure import Block, Station
from mit_rail_sim.simulation_engine.passenger import Passenger
from mit_rail_sim.simulation_engine.simulation import Simulation
from mit_rail_sim.simulation_engine.train import Train


class LoggerContext:
    def __init__(
        self,
        train_logger: TrainLogger,
        passenger_logger: PassengerLogger,
        station_logger: StationLogger,
        simulation_logger: SimulationLogger,
        block_logger: BlockActivationLogger,
        warmup_time=0,
    ):
        self.train_logger = train_logger.set_warmup_time(warmup_time)
        self.passenger_logger = passenger_logger.set_warmup_time(warmup_time)
        self.station_logger = station_logger.set_warmup_time(warmup_time)
        self.simulation_logger = simulation_logger.set_warmup_time(warmup_time)
        self.block_logger = block_logger.set_warmup_time(warmup_time)

    def __enter__(self):
        Train.train_logger = self.train_logger
        Passenger.passenger_logger = self.passenger_logger
        Station.station_logger = self.station_logger
        Simulation.simulation_logger = self.simulation_logger
        Block.block_logger = self.block_logger

    def __exit__(self, exc_type, exc_value, traceback):
        Train.train_logger = None
        Passenger.passenger_logger = None
        Station.station_logger = None
        Simulation.simulation_logger = None
        Block.block_logger = None
