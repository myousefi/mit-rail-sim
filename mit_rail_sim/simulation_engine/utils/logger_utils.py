from __future__ import annotations

import asyncio
import csv
import json
import os
from typing import TYPE_CHECKING, Any, Coroutine, Dict, Optional, Union

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import Block
    from mit_rail_sim.simulation_engine.train import Train
    from mit_rail_sim.simulation_engine.passenger import Passenger
    from mit_rail_sim.simulation_engine.infrastructure import Station
    from mit_rail_sim.simulation_engine.simulation.simulation import Simulation

from abc import ABC, abstractmethod


class LoggerStrategy(ABC):
    @abstractmethod
    def write_header(self, log_file_path: str) -> None:
        pass

    @abstractmethod
    def write_row(self, log_file_path: str, data: Dict[str, Any]) -> None:
        pass


class CSVLoggerStrategy(LoggerStrategy):
    def __init__(
        self,
        headers: Dict,
    ):
        self.headers = headers

    def write_header(self, log_file_path: str) -> None:
        with open(log_file_path, mode="w", newline="", encoding="utf-8") as log_file:
            csv_writer = csv.writer(log_file)
            csv_writer.writerow(self.headers.keys())

    def write_row(self, log_file_path: str, data: Dict[str, Any]) -> None:
        with open(log_file_path, mode="a", newline="", encoding="utf-8") as log_file:
            csv_writer = csv.writer(log_file)
            csv_writer.writerow(data.values())


class BaseLogger(ABC):
    def __init__(
        self,
        log_file_path: str,
        headers: Dict,
        logger_strategy: Optional[LoggerStrategy] = None,
    ):
        self.log_file_path = log_file_path
        self.headers = headers

        if logger_strategy is None:
            logger_strategy = CSVLoggerStrategy(headers)

        self.logger_strategy = logger_strategy
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        self.logger_strategy.write_header(self.log_file_path)

    def _collect_data(self, obj: Any) -> Dict[str, Any]:
        return {header: func(obj) for header, func in self.headers.items()}

    def set_warmup_time(self, warmup_time: float) -> BaseLogger:
        self.warmup_time = warmup_time
        return self


class TrainLogger(BaseLogger):
    def __init__(
        self,
        log_file_path: str,
        log_interval: int,
        logger_strategy: Optional[LoggerStrategy] = None,
    ):
        self.headers = {
            "replication_id": lambda train, _: train.simulation.replication_id,
            "time_in_seconds": lambda train, current_time: current_time,
            "train_id": lambda train, _: train.train_id,
            "speed": lambda train, _: train.speed,
            "acceleration": lambda train, _: train.acceleration,
            "total_travelled_distance": lambda train, _: train.total_travelled_distance,
            "location_from_terminal": lambda train, _: train.location_from_terminal,
            "current_block_id": lambda train, _: train.current_block.block_id,
            "distance_travelled_in_current_block": lambda train, _: train.distance_travelled_in_current_block,
            "train_speed_regulator_state": lambda train, _: str(train.train_speed_regulator.state),
            "train_received_speed_code": lambda train, _: train.current_block.current_speed_code(
                train
            ),
            "current_block_speed_limit": lambda train, _: train.current_block.default_speed_code,
            "current_block_reduced_speed_due_to_slow_zone": lambda train, _: train.current_block.slow_zone_reduced_speed_limit
            if train.current_block.slow_zone_reduced_speed_limit != float("inf")
            else None,
            "number_of_passengers_on_board": lambda train, _: train.passenger_manager.total_passengers,
            "starting_block_index": lambda train, _: train.starting_block_index,
            "direction": lambda train, _: train.path.direction,
            "headway": lambda train, _: train.current_block.headway,
        }
        super().__init__(log_file_path, self.headers, logger_strategy)
        self.log_interval = log_interval
        # self.current_time: Decimal = Decimal(0.0)
        self.steps_since_last_log: int = 0

        self.warning_file_path = log_file_path.replace(".csv", "_warnings.csv")
        # initiate a new warning file even if it already exists
        with open(self.warning_file_path, mode="w", newline="", encoding="utf-8") as warning_file:
            pass

    def _collect_train_data(self, train: Train, current_time: float) -> Dict[str, Any]:
        return {header: func(train, current_time) for header, func in self.headers.items()}

    def update(self, train: Train) -> Union[None, Coroutine[Any, Any, None]]:
        if train.simulation.current_time < self.warmup_time:
            return None

        if (train.steps_since_last_log % self.log_interval) == 0:  # Check if it's time to log
            train_data = self._collect_train_data(train, train.simulation.current_time)
            self.logger_strategy.write_row(self.log_file_path, train_data)

            train.steps_since_last_log = 0  # Reset the counter

        train.steps_since_last_log += 1  # Increase the counter

        return None

    def log_warning(
        self, warning_message: str, train: Train
    ) -> Union[None, Coroutine[Any, Any, None]]:
        warning_data = {
            "replication_id": train.simulation.replication_id,
            "current_time": train.simulation.current_time,
            "train_id": train.train_id,
            "warning_message": warning_message,
        }

        with open(self.warning_file_path, mode="a", newline="", encoding="utf-8") as warning_file:
            csv_writer = csv.writer(warning_file)
            csv_writer.writerow(warning_data.values())

        return None


class PassengerLogger(BaseLogger):
    def __init__(self, log_file_path: str, logger_strategy: Optional[LoggerStrategy] = None):
        self.headers = {
            "replication_id": lambda passenger: passenger.simulation.replication_id,
            "passenger_id": lambda passenger: passenger.passenger_id,
            "denied_boarding": lambda passenger: passenger.number_of_times_denied_boarding,
            "arrival_time": lambda passenger: passenger.arrival_time,
            "waiting_time": lambda passenger: passenger.waiting_time,
            "travel_time": lambda passenger: passenger.travel_time,
            "journey_time": lambda passenger: passenger.journey_time,
            "origin": lambda passenger: passenger.origin,
            "destination": lambda passenger: passenger.destination,
            "direction": lambda passenger: passenger.direction,
        }
        super().__init__(log_file_path, headers=self.headers, logger_strategy=logger_strategy)

    def log_passenger(self, passenger: Passenger) -> None:
        if passenger.boarding_time < self.warmup_time:
            return

        passenger_data = self._collect_data(passenger)
        self.logger_strategy.write_row(self.log_file_path, passenger_data)


class StationLogger(BaseLogger):
    def __init__(
        self,
        log_file_path: str,
        logger_strategy: Optional[LoggerStrategy] = None,
    ):
        self.headers = {
            "replication_id": lambda station: station.simulation.replication_id,
            "time_in_seconds": lambda data: data["current_time"],
            "station_name": lambda data: data["station_name"],
            "direction": lambda data: data["direction"],
            "headway": lambda data: data["headway"],
            "dwell_time": lambda data: data["dwell_time"],
            "applied_holding": lambda data: data["applied_holding"],
            "train_id": lambda data: data["train_id"],
            "number_of_passengers_boarded": lambda data: data["number_of_passengers_boarded"],
            "number_of_passengers_alighted": lambda data: data["number_of_passengers_alighted"],
            "number_of_passengers_on_train_after_stop": lambda data: data[
                "number_of_passengers_on_train_after_stop"
            ],
            "number_of_passengers_on_platform_after_stop": lambda data: data[
                "number_of_passengers_on_platform_after_stop"
            ],
            "number_of_passengers_on_platform_before_stop": lambda data: data[
                "number_of_passengers_on_platform_before_stop"
            ],
            "is_short_turning": lambda data: data["is_short_turning"],
            "denied_boarding": lambda data: data["denied_boarding"],
        }
        super().__init__(log_file_path, self.headers, logger_strategy)

    def log_train_visit(
        self,
        station: Station,
        current_time: float,
        train_id: str,
        dwell_time: float,
        applied_holding: float,
        number_of_passengers_boarded: int,
        number_of_passengers_alighted: int,
        number_of_passengers_on_train_after_stop: int,
        number_of_passengers_on_platform_before_stop: int,
        is_short_turning: bool,
        denied_boarding: int,
    ) -> None:
        if current_time < self.warmup_time:
            return

        station_data = {
            "replication_id": station.simulation.replication_id,
            "current_time": current_time,
            "station_name": station.name,
            "direction": station.direction,
            "headway": current_time - station.last_train_visit_time,
            "dwell_time": dwell_time,
            "applied_holding": applied_holding,
            "train_id": train_id,
            "number_of_passengers_boarded": number_of_passengers_boarded,
            "number_of_passengers_alighted": number_of_passengers_alighted,
            "number_of_passengers_on_train_after_stop": number_of_passengers_on_train_after_stop,
            "number_of_passengers_on_platform_after_stop": station.sorted_passenger_queue.size(),
            "number_of_passengers_on_platform_before_stop": number_of_passengers_on_platform_before_stop,
            "is_short_turning": is_short_turning,
            "denied_boarding": denied_boarding,
        }
        self.logger_strategy.write_row(self.log_file_path, station_data)


class NullPassengerLogger:
    def __init__(self, *args, **kwargs):
        pass

    def log_passenger(self, passenger: Passenger) -> None:
        pass


class NullTrainLogger(TrainLogger):
    def __init__(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs) -> None:
        pass

    def log_warning(self, *args, **kwargs) -> None:
        pass


class JSONLoggerStrategy(LoggerStrategy):
    def write_header(self, log_file_path: str) -> None:
        # For JSON files, we don't specifically need a header
        with open(log_file_path, mode="w", newline="", encoding="utf-8") as f:
            pass

    def write_row(self, log_file_path: str, data: Dict[str, Any]) -> None:
        with open(log_file_path, mode="a", encoding="utf-8") as log_file:
            json.dump(data, log_file, ensure_ascii=False)
            log_file.write("\n")  # Write each object on a new line for readability


class SimulationLogger(BaseLogger):
    def __init__(self, log_file_path: str, logger_strategy: Optional[LoggerStrategy] = None):
        self.headers = {
            "time_step": lambda sim: sim.time_step,
            "start_hour": lambda sim: sim._start_hour,
            "total_time": lambda sim: sim._total_time,
            "is_weekday": lambda sim: sim._is_weekday,
        }

        if logger_strategy is None:
            logger_strategy = JSONLoggerStrategy()

        super().__init__(log_file_path, self.headers, logger_strategy)

    def log_simulation(self, simulation: Simulation) -> None:
        simulation_data = self._collect_data(simulation)
        self.logger_strategy.write_row(self.log_file_path, simulation_data)

    def log_warning(self, warning_message: str) -> None:
        warning_data = {
            "warning_message": warning_message,
        }
        self.logger_strategy.write_row(self.log_file_path, warning_data)


class BlockActivationLogger(BaseLogger):
    def __init__(self, log_file_path: str, logger_strategy: Optional[LoggerStrategy] = None):
        self.headers = {
            "replication_id": lambda data: data["replication_id"],
            "time_in_seconds": lambda data: data["time_in_seconds"],
            "train_id": lambda data: data["train_id"],
            "block_id": lambda data: data["block_id"],
            "headway": lambda data: data["headway"],
            "direction": lambda data: data["direction"],
            "passengers_on_board": lambda data: data["passengers_on_board"],
        }
        super().__init__(log_file_path, self.headers, logger_strategy)

    def log_block_activation(self, block: Block, train: Train) -> None:
        if train.simulation.current_time < self.warmup_time:
            return

        block_activation_data = {
            "replication_id": train.simulation.replication_id,
            "time_in_seconds": train.simulation.current_time,
            "train_id": train.train_id,
            "block_id": block.block_alt_name,
            "headway": train.simulation.current_time - block.last_train_visit_time,
            "direction": train.path.direction,
            "passengers_on_board": train.passenger_manager.total_passengers,
        }
        self.logger_strategy.write_row(self.log_file_path, block_activation_data)


class NullBlockActivationLogger:
    def __init__(self, *args, **kwargs):
        pass

    def log_block_activation(self, *args, **kwargs) -> None:
        pass
