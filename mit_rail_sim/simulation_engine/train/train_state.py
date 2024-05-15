from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from mit_rail_sim import config_handler
from mit_rail_sim.simulation_engine.infrastructure import DispatchingBlockDecorator
from mit_rail_sim.simulation_engine.infrastructure.block import (
    DispatchingMovingBlockDecorator,
)
from mit_rail_sim.simulation_engine.train.train_headway_regulator import (
    TrainHeadwayRegulator,
    TrainHeadwayRegulatorAtStation,
    TrainHeadwayRegulatorAtStationInformedByCrowding,
)

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import Station
    from mit_rail_sim.simulation_engine.train import Train


class TrainState(ABC):
    def __init__(self, train: Train):
        self.train = train

    @abstractmethod
    def handle(self) -> None:
        pass

    def __str__(self) -> str:
        return self.__class__.__name__


# Update MovingBetweenStationsState class
class MovingBetweenStationsState(TrainState):
    def handle(self) -> None:
        self.train.train_speed_regulator.regulate_acceleration()
        self.train.update_distance_travelled()
        self.train.update_speed()
        self.train.update_block()


class DwellingAtStationState(TrainState):
    def __init__(self, train: Train, station: Station):
        self.dwell_elapsed_time = 0.0
        self.station = station
        self.train = train
        self.dwell_time = 0.0
        self.denied_boardings = 0
        self.rec_holding = 0.0

        if self.train.path.is_short_turned_at_this_station(self.station):
            alighting_counts = self.train.passenger_manager.alight_all_passengers(
                current_station=self.station,
                current_time=self.train.simulation.current_time,
            )

            number_of_passengers_to_board = 0

            if self.train.path.is_inspected():
                self.dwell_time += self.train.path.get_inspection_time()

        else:
            alighting_counts = self.train.passenger_manager.alight_passengers(
                current_station=self.station.name,
                current_time=self.train.simulation.current_time,
            )

            number_of_passengers_to_board = (
                self.train.passenger_manager.remaining_capacity()
            )

        if cfg := config_handler.get_config():
            if cfg.holding:
                if self.station.name == cfg.station:
                    if self.station.direction == (
                        "Northbound" if cfg.schd == "PM" else "Southbound"
                    ):
                        head_reg = TrainHeadwayRegulatorAtStation(
                            cfg.max_holding, cfg.min_holding
                        )
                        self.rec_holding = head_reg.suggested_holding(self.train)
                        # self.dwell_time = max(self.dwell_time, rec_holding)

                        print(
                            f"Hodling for {self.rec_holding} at {cfg.station}-{self.station.direction}"
                        )
        # self.rec_holding = (
        #     self.rec_holding if self.rec_holding > cfg.minimum_holding_time else 0
        # )

        self.station.generate_and_add_passengers(self.train, self.rec_holding)

        number_of_passengers_on_platform = self.station.sorted_passenger_queue.size()

        if cfg := config_handler.get_config():
            (
                boarding_passengers,
                self.denied_boardings,
            ) = self.station.board_passengers_based_on_destiations_and_probability(
                train_capacity=number_of_passengers_to_board,
                served_destinations=self.train.path.get_all_stops_ahead_which_are_served(
                    self.train.current_block_index
                ),
                probability_of_boarding_any_train=cfg.passenger.probability_of_boarding_any_train,
            )
        else:
            (
                boarding_passengers,
                self.denied_boardings,
            ) = self.station.board_passengers_onto_train(
                number_of_passengers_to_board,
                self.train.path.get_all_stops_ahead_which_are_served(
                    self.train.current_block_index
                ),
            )

        if self.denied_boardings > 0:
            print(
                f"Denied boardings: {self.denied_boardings} at {self.station.name} at time {self.train.simulation.current_time}"
            )
        if not self.train.should_log():
            boarding_passengers = [
                passenger.set_not_loggable() for passenger in boarding_passengers
            ]

        boarding_counts = self.train.passenger_manager.board_passengers(
            passengers=boarding_passengers,
            current_time=self.train.simulation.current_time + self.rec_holding,
        )

        self.door_metrics = self.train.passenger_manager.get_door_metrics(
            alight_counts=alighting_counts, boarding_counts=boarding_counts
        )

        self.dwell_time += self.station.get_dwell_time(self.door_metrics)

        self.dwell_time = max(self.dwell_time, self.rec_holding)
        # if cfg := config_handler.get_config():
        #     if cfg.headway_uic_nb:
        #         if self.station.name == "UIC-Halsted":
        #             if self.station.direction == "Northbound":
        #                 head_reg = TrainHeadwayRegulatorAtStation()
        #                 rec_holding = head_reg.suggested_holding(self.train)
        #                 self.dwell_time = max(self.dwell_time, rec_holding)

        # Raise error if station does not have a logger
        if station.station_logger is None:
            raise Exception("Station does not have a logger!")
        elif self.train.should_log():
            # Log the train visit
            station.station_logger.log_train_visit(
                station=self.station,
                current_time=self.train.simulation.current_time,
                train_id=self.train.train_id,
                dwell_time=self.dwell_time,
                applied_holding=self.rec_holding,
                number_of_passengers_boarded=sum(
                    boarding_counts for (_, boarding_counts, _) in self.door_metrics
                ),
                number_of_passengers_alighted=sum(
                    alighting_counts for (alighting_counts, _, _) in self.door_metrics
                ),
                number_of_passengers_on_train_after_stop=self.train.passenger_manager.total_passengers,
                number_of_passengers_on_platform_before_stop=number_of_passengers_on_platform,
                is_short_turning=self.train.path.is_short_turn(),
                denied_boarding=self.denied_boardings,
            )

        station._last_train_visit_time = (
            self.train.simulation.current_time + self.rec_holding
        )

    def handle(self) -> None:
        self.dwell_elapsed_time += self.train.time_step

        if self.dwell_elapsed_time >= self.dwell_time:
            if self.train.current_block.station is None:
                raise Exception("Train is dwelling at that is none!")
            self.train.state = MovingBetweenStationsState(self.train)
        else:
            pass

    def __str__(self) -> str:
        return f"DwellingAtStation:{self.station.name}"


class WaitingToBeDispatched(TrainState):
    def __init__(self, train: Train, blocks_to_deactivate=[]):
        super().__init__(train)

        self.first_block = self.train.path.blocks[self.train.starting_block_index]
        self.blocks_to_deactivate = blocks_to_deactivate
        self.rec_holding = 0.0

        self.dispatch_margin = 0

        if self.train.path.direction == "Northbound":
            self.dispatch_margin = 2 * 60

        if self.train.starting_block_index != 0:
            if cfg := config_handler.get_config():
                if cfg.headway_management:
                    head_reg = TrainHeadwayRegulator()
                    self.rec_holding = head_reg.suggested_holding(self.train)

    def handle(self) -> None:
        # if isinstance(self.first_block, DispatchingBlockDecorator):
        assert isinstance(
            self.first_block,
            (DispatchingBlockDecorator, DispatchingMovingBlockDecorator),
        )

        if self.first_block.ready_to_dispatch(self.train) and (self.rec_holding <= 0):
            self.train.state = MovingBetweenStationsState(self.train)
            self.first_block.activate(self.train)

            if self.blocks_to_deactivate:
                for block in self.blocks_to_deactivate:
                    try:
                        block.deactivate(self.train)
                    except Exception as e:
                        pass

        self.rec_holding -= self.train.time_step

    def __str__(self) -> str:
        return "WaitingToBeDispatched"


class SettingUpForShortTurning(TrainState):
    def __init__(
        self, train: Train, set_up_time: float, blocks_to_deactivate: list = []
    ):
        super().__init__(train)

        self.set_up_time = set_up_time
        self.set_up_elapsed_time = 0.0
        self.blocks_to_deactivate = blocks_to_deactivate

    def handle(self) -> None:
        self.set_up_elapsed_time += self.train.time_step

        if self.set_up_elapsed_time > self.set_up_time:
            self.train.state = WaitingToBeDispatched(
                self.train, blocks_to_deactivate=self.blocks_to_deactivate
            )


class SettingUpForShortTurningAtStation(TrainState):
    def __init__(
        self, train: Train, set_up_time: float, station: Station, blocks: list = []
    ):
        super().__init__(train)

        self.set_up_time = set_up_time

        self.blocks = blocks
        self.set_up_time += sum(block.length / 7.33 for block in self.blocks)
        self.set_up_elapsed_time = 0.0

        self.denied_boardings = 0

        self.station = station

        self.train = train

        number_of_passengers_to_board = (
            self.train.passenger_manager.remaining_capacity()
        )

        self.station.generate_and_add_passengers(self.train)

        self.number_of_passengers_on_platform = (
            self.station.sorted_passenger_queue.size()
        )

        if cfg := config_handler.get_config():
            (
                boarding_passengers,
                self.denied_boardings,
            ) = self.station.board_passengers_based_on_destiations_and_probability(
                train_capacity=number_of_passengers_to_board,
                served_destinations=self.train.path.get_all_stops_ahead_which_are_served(
                    self.train.current_block_index
                ),
                probability_of_boarding_any_train=cfg.passenger.probability_of_boarding_any_train,
            )
        else:
            (
                boarding_passengers,
                self.denied_boardings,
            ) = self.station.board_passengers_onto_train(number_of_passengers_to_board)

        if not self.train.should_log():
            boarding_passengers = [
                passenger.set_not_loggable() for passenger in boarding_passengers
            ]

        # Raise error if station does not have a logger
        self.log_train_visit(boarding_passengers, station)

    def log_train_visit(self, boarding_passengers, station):
        if station.station_logger is None:
            raise Exception("Station does not have a logger!")
        elif self.train.should_log():
            # Log the train visit
            station.station_logger.log_train_visit(
                station=self.station,
                current_time=self.train.simulation.current_time,
                train_id=self.train.train_id,
                dwell_time=0,
                number_of_passengers_boarded=len(boarding_passengers),
                number_of_passengers_alighted=0,
                number_of_passengers_on_train_after_stop=self.train.passenger_manager.total_passengers,
                number_of_passengers_on_platform_before_stop=self.number_of_passengers_on_platform,
                is_short_turning=self.train.path.is_short_turn(),
                denied_boarding=self.denied_boardings,
            )
        station._last_train_visit_time = self.train.simulation.current_time

    def handle(self) -> None:
        self.set_up_elapsed_time += self.train.time_step

        if self.set_up_elapsed_time > self.set_up_time:
            self.train.state = WaitingToBeDispatched(
                self.train, blocks_to_deactivate=self.blocks
            )
