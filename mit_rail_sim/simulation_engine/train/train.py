from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Optional, Tuple

from mit_rail_sim.simulation_engine.infrastructure.block import (
    ReleasingNotOccupiedBlock,
)

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.utils.logger_utils import AsyncTrainLogger
    from mit_rail_sim.simulation_engine.train.train_passenger_manager import (
        TrainPassengerManager,
    )
    from mit_rail_sim.simulation_engine.train import (
        TrainSpeedRegulator,
        TrainSpeedRegulatorCTA,
    )
    from mit_rail_sim.simulation_engine.train.train_state import TrainState
    from mit_rail_sim.simulation_engine.infrastructure import Path, BlockType, Station
    from mit_rail_sim.simulation_engine.utils import TrainLogger
    from mit_rail_sim.simulation_engine.simulation.simulation import Simulation

from mit_rail_sim.simulation_engine.train.train_state import (
    DwellingAtStationState,
    WaitingToBeDispatched,
)

SIGHT_DISTANCE = 2000


class Train:
    simulation: Simulation
    train_logger: Optional[TrainLogger] = None
    _last_id = 0

    def __init__(
        self,
        train_speed_regulator: TrainSpeedRegulator | TrainSpeedRegulatorCTA,
        train_passenger_manager: TrainPassengerManager,
        path: Path,
        starting_block_index: int = 0,
        dispatching_time: Optional[float] = None,
        runid: Optional[str] = None,
        # simulation: Simulation,
    ):
        self.train_id = runid if runid else Train.generate_train_id()

        self.steps_since_last_log: int = 0  # Added steps_since_last_log attribute

        self.train_speed_regulator = train_speed_regulator
        self.train_speed_regulator.register_train(self)

        self.passenger_manager = train_passenger_manager

        self.path: Path = path

        self.starting_block_index = starting_block_index
        self.current_block_index = starting_block_index

        self.distance_travelled_in_current_block = 0.0
        self.speed = 0.0
        self.acceleration = 0.0

        self.dispatching_time = dispatching_time

        self.state: TrainState = WaitingToBeDispatched(self)

        self.length = 48 * 8

        self._should_log = True

    @classmethod
    def generate_train_id(cls):
        train_id = f"train_{cls._last_id}"
        cls._last_id += 1
        return train_id

    def update(self) -> None:
        self.state.handle()
        self.log()  # Add this line

    def should_log(self) -> bool:
        return self._should_log

    def log(self) -> None:
        assert self.train_logger is not None
        if not isinstance(self.state, WaitingToBeDispatched) and self.should_log():
            self.train_logger.update(self)

    @property
    def speed_in_fps(self) -> float:
        return self.speed * 5280 / 3600

    @property
    def acceleration_in_fps2(self) -> float:
        return self.acceleration * 5280 / 3600

    @property
    def time_step(self) -> float:
        if self.simulation is None:
            raise ValueError("Simulation is not set!")

        return self.simulation.time_step

    @property
    def location_from_terminal(self) -> float:
        return self.path.get_total_travelled_distance(
            self.current_block_index, self.distance_travelled_in_current_block
        )

    @property
    def total_travelled_distance(self) -> float:
        return self.distance_travelled_in_current_block + sum(
            block.length for block in self.path.blocks[: self.current_block_index]
        )

    @property
    def total_travelled_distance_from_dispatch(self) -> float:
        return self.distance_travelled_in_current_block + sum(
            block.length
            for block in self.path.blocks[
                self.starting_block_index : self.current_block_index
            ]
        )

    @property
    def previous_block(self) -> BlockType:
        return self.path.blocks[self.current_block_index - 1]

    @property
    def current_block(self) -> BlockType:
        return self.path.blocks[self.current_block_index]

    @property
    def next_block(self) -> BlockType:
        try:
            return self.path.blocks[self.current_block_index + 1]
        except IndexError as index_error:
            raise NextBlockNotFoundError(
                "Next block not found in the path"
            ) from index_error

    @property
    def first_block_after_station(self) -> Optional[BlockType]:
        for i in range(self.current_block_index + 1, len(self.path.blocks)):
            if self.path.blocks[i].station is not None:
                if i + 1 < len(self.path.blocks):
                    return self.path.blocks[i + 1]
                else:
                    return None
        return None

    @property
    def distance_to_next_block(self) -> float:
        return self.current_block.length - self.distance_travelled_in_current_block

    @distance_to_next_block.setter
    def distance_to_next_block(self, distance: float) -> None:
        self.distance_travelled_in_current_block = self.current_block.length - distance

    def block_with_red_signals_in_sight(self) -> Tuple[Optional[float], Optional[int]]:
        distance_to_next_block = self.distance_to_next_block
        i = 1
        while distance_to_next_block < SIGHT_DISTANCE:
            try:
                if (
                    self.path.blocks[self.current_block_index + i].current_speed_code(
                        self
                    )
                    == 0.0
                ):
                    return distance_to_next_block, self.current_block_index + i

                distance_to_next_block += self.next_block.length
                i = i + 1
            except:
                break

        return None, None

    def get_all_stops_ahead(self) -> list[Station]:
        return self.path.get_all_stops_ahead(self.current_block_index)

    def update_speed(self) -> None:
        self.train_speed_regulator.update_train_speed()

    def update_distance_travelled(self) -> float:
        distance_travelled_in_time_step = (
            self.speed_in_fps * self.time_step
            + 0.5 * self.acceleration_in_fps2 * self.time_step**2
        )

        if math.isclose(
            distance_travelled_in_time_step,
            0,
            rel_tol=0,
            abs_tol=self.train_speed_regulator.TOLERANCE,
            # abs_tol=1,
        ):
            distance_travelled_in_time_step = 0

        if distance_travelled_in_time_step < 0:
            distance_travelled_in_time_step = 0
            # raise ValueError(
            #     f"Distance travelled in time step {distance_travelled_in_time_step} is negative"
            # )

        self.distance_travelled_in_current_block += distance_travelled_in_time_step

        return distance_travelled_in_time_step

    def update_block(self) -> None:
        if self.distance_travelled_in_current_block >= self.current_block.length:
            self.distance_travelled_in_current_block -= self.current_block.length

            self.current_block_index += 1
            self.current_block.activate(self)

        train_rear_position = self.distance_travelled_in_current_block - self.length

        for block in self.path.blocks[self.current_block_index - 1 :: -1]:
            if train_rear_position > 0:
                try:
                    block.deactivate(self)
                except ReleasingNotOccupiedBlock:
                    break
            train_rear_position += block.length

    def distance_traveled_from_the_start_of_block(
        self, asking_block: BlockType
    ) -> float:
        distance = self.distance_travelled_in_current_block
        blocks_list = self.path.blocks[self.current_block_index :: -1]

        for block in blocks_list:
            if block == asking_block:
                break
            distance += block.length

        return distance

    @property
    def distance_to_next_station(self) -> float:
        return self.path.get_distance_to_the_next_station(
            self.current_block_index, self.distance_travelled_in_current_block
        )

    @property
    def current_speed_code(self) -> float:
        return self.current_block.current_speed_code(self)

    def set_state_to_dwelling_at_station(self, station: Station) -> None:
        self.state = DwellingAtStationState(self, station)

    def delete(self) -> None:
        for block in self.path.blocks[self.current_block_index - 1 :: -1]:
            # if block.is_occupied_by(self):
            try:
                block.deactivate(self)
            except ReleasingNotOccupiedBlock:
                break

        self.simulation.remove_train(self)


class DummyTrain(Train):
    simulation: Simulation

    def log(self) -> None:
        pass

    def should_log(self) -> bool:
        return False

    def layover_and_turnback(self) -> None:
        self.delete()


class DummyTrainDecorator(DummyTrain):
    simulation: Simulation

    def __init__(self, train: Train):
        # Copy properties from DummyTrain to this
        self.__dict__ = train.__dict__.copy()
        self.train_id = f"dummy_{train.train_id}"
        self.state: TrainState = WaitingToBeDispatched(self)
        self.train_speed_regulator.register_train(self)


class NextBlockNotFoundError(Exception):
    pass
