from __future__ import annotations

import math
from abc import ABC, abstractmethod
from random import randint
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import BlockType
    from mit_rail_sim.simulation_engine.train import TrainSpeedRegulator

MIN_STOP_DISTANCE = 5
MAX_STOP_DISTANCE = 10


class TrainSpeedRegulatorState(ABC):
    def __init__(self, regulator: TrainSpeedRegulator):
        self.regulator = regulator

    def handle(self) -> None:
        self.set_the_acceleration()
        self.check_the_validity_of_the_acceleration()
        self.handle_transition_to_next_state()

    def handle_transition_to_next_state(self) -> None:
        if next_state := self.get_next_state():
            self.regulator.state = next_state

    def get_next_state(self) -> Optional[TrainSpeedRegulatorState]:
        if self.should_transition_to_break_with_maximum_rate_state():
            return BrakeWithMaximumRateState(self.regulator)
        if (
            self.regulator.state is not BrakeNormalToStationState
            and self.should_transition_to_brake_normal_to_station()
        ):
            return BrakeNormalToStationState(self.regulator)
        return self.handle_custom_transition()

    def should_transition_to_brake_normal_to_station(self) -> bool:
        future_distance_travelled = (
            self.regulator.train.speed_in_fps * self.regulator.train.time_step
            + 0.5
            * self.regulator.train.acceleration_in_fps2
            * self.regulator.train.time_step**2
        )

        future_distance_to_next_station = (
            self.regulator.train.distance_to_next_station
            - future_distance_travelled
            - MAX_STOP_DISTANCE
        )
        return (future_distance_to_next_station) <= self.regulator.braking_distance

    def should_transition_to_break_with_maximum_rate_state(self) -> bool:
        return (
            self.regulator.train.speed > self.regulator.train.current_speed_code * 1.05
        )

    @abstractmethod
    def check_the_validity_of_the_acceleration(self) -> None:
        pass

    @abstractmethod
    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorState]:
        pass

    @abstractmethod
    def set_the_acceleration(self) -> None:
        pass

    @abstractmethod
    def readjust_acceleration(self) -> None:
        self.regulator.train.acceleration = min(
            self.regulator.train.acceleration, self.regulator.normal_acceleration
        )
        self.regulator.train.acceleration = max(
            self.regulator.train.acceleration,
            -self.regulator.emergency_deceleration,
        )

    @property
    def new_speed(self) -> float:
        return (
            self.regulator.train.speed
            + self.regulator.train.acceleration * self.regulator.train.time_step
        )

    def __str__(self) -> str:
        return self.__class__.__name__


class KeepingTheSpeedUptoCodeState(TrainSpeedRegulatorState):
    def set_the_acceleration(self) -> None:
        current_speed_code = self.regulator.train.current_block.current_speed_code(
            self.regulator.train
        )

        if math.isclose(
            current_speed_code,
            self.regulator.train.speed,
            abs_tol=self.regulator.TOLERANCE,
        ):
            self.regulator.train.acceleration = 0
            self.regulator.train.speed = current_speed_code

        if self.regulator.train.speed < current_speed_code:
            # if self.new_speed < current_speed_code:
            self.regulator.train.acceleration = self.regulator.normal_acceleration

        if self.regulator.train.speed > current_speed_code:
            # if self.new_speed > current_speed_code:
            self.regulator.train.acceleration = -self.regulator.normal_deceleration

    def check_the_validity_of_the_acceleration(self) -> None:
        if self.new_speed > self.regulator.train.current_block.current_speed_code(
            self.regulator.train
        ):
            self.readjust_acceleration(True)
        if self.new_speed < 0:
            self.readjust_acceleration()

    def readjust_acceleration(self, Overspeeding: bool = False) -> None:
        target_acceleration = (
            self.regulator.train.current_block.current_speed_code(self.regulator.train)
            - self.regulator.train.speed
        ) / self.regulator.train.time_step
        self.regulator.train.acceleration = target_acceleration

        super().readjust_acceleration()

    def future_planning_distance(self) -> Tuple[float, BlockType]:
        current_index = self.regulator.train.current_block_index
        three_next_blocks = self.regulator.train.path.blocks[
            current_index + 1 : current_index + 3
        ]

        distance_to_reach_target_speed = (
            lambda block: (
                self.regulator.train.speed_in_fps**2
                - (block.current_speed_code(self.regulator.train) * 5200 / 3600) ** 2
            )
            / (2 * self.regulator.normal_decceleration_in_fps2)
            + 20
        )

        braking_distances = [
            (distance_to_reach_target_speed(block), block)
            for block in three_next_blocks
        ]
        cummulative_block_lengths = [
            sum(b.length for b in three_next_blocks[:i])
            for i in range(1, len(three_next_blocks))
        ]

        for i in range(1, len(braking_distances)):
            braking_distances[i] = (
                braking_distances[i][0] - cummulative_block_lengths[i - 1],
                braking_distances[i][1],
            )

        max_distance, restricting_block = max(braking_distances, key=lambda x: x[0])

        if (
            restricting_block.current_speed_code(self.regulator.train)
            >= self.regulator.train.speed
        ):
            return 0, restricting_block

        return max_distance, restricting_block

    # def future_planning_distance(self) -> float:
    #     future_speed_in_fps = (
    #         self.regulator.train.speed_in_fps
    #         + self.regulator.train.acceleration_in_fps2 * self.regulator.train.time_step
    #     )
    #     next_speed_code_in_fps = (
    #         self.regulator.train.next_block.current_speed_code(self.regulator.train) * 5280 / 3600
    #     )

    #     delta_speed = next_speed_code_in_fps - future_speed_in_fps

    #     if delta_speed >= 0:
    #         return 0

    #     acceleration = -self.regulator.normal_decceleration_in_fps2 * 0.8

    #     future_distance_travelled = (
    #         self.regulator.train.speed_in_fps * self.regulator.train.time_step
    #         + 0.5 * self.regulator.train.acceleration_in_fps2 * self.regulator.train.time_step**2
    #     )

    #     distance_to_reach_target_speed = (
    #         next_speed_code_in_fps**2 - future_speed_in_fps**2
    #     ) / (2 * acceleration)

    #     return future_distance_travelled + distance_to_reach_target_speed

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorState]:
        max_distance, restricting_block = self.future_planning_distance()
        if self.regulator.train.distance_to_next_block < max_distance:
            return DecelerateToSpeedNormalRateForPlanningState(
                self.regulator,
                restricting_block=restricting_block,
            )

        return None


class LeavingTheStationState(KeepingTheSpeedUptoCodeState):
    def __init__(self, regulator: TrainSpeedRegulator):
        super().__init__(regulator)
        if self.regulator.train.current_block.station is None:
            raise ValueError(
                "Train is leaving a station which is not the current block"
            )

        self.station = self.regulator.train.current_block.station

    def get_next_state(self) -> Optional[TrainSpeedRegulatorState]:
        if self.should_transition_to_break_with_maximum_rate_state():
            return BrakeWithMaximumRateState(self.regulator)
        if (
            self.regulator.train.distance_travelled_in_current_block
            > self.station.location_relative_to_block
        ):
            return KeepingTheSpeedUptoCodeState(self.regulator)
        return None


class DecelerateToSpeedNormalRateForPlanningState(TrainSpeedRegulatorState):
    def __init__(self, regulator: TrainSpeedRegulator, restricting_block: BlockType):
        super().__init__(regulator)
        self.restricting_block = restricting_block

    @property
    def min_speed_code(self) -> float:
        return min(
            # self.regulator.train.next_block.current_speed_code(self.regulator.train),
            self.restricting_block.current_speed_code(self.regulator.train),
            self.regulator.train.current_block.current_speed_code(self.regulator.train),
        )

    def set_the_acceleration(self) -> None:
        if self.regulator.train.speed > self.min_speed_code:
            self.regulator.train.acceleration = -self.regulator.normal_deceleration
        else:
            self.regulator.train.acceleration = 0

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorState]:
        if (
            self.regulator.train.current_block == self.restricting_block
            or self.regulator.train.speed == 0
        ):
            return KeepingTheSpeedUptoCodeState(self.regulator)
        return None

    def check_the_validity_of_the_acceleration(self) -> None:
        if self.new_speed < self.min_speed_code:
            self.readjust_acceleration()

    def readjust_acceleration(self) -> None:
        target_acceleration = (
            self.min_speed_code - self.regulator.train.speed
        ) / self.regulator.train.time_step

        self.regulator.train.acceleration = target_acceleration

        if self.regulator.train.acceleration > self.regulator.normal_acceleration:
            self.regulator.train.acceleration = self.regulator.normal_acceleration
            self.regulator.state = KeepingTheSpeedUptoCodeState(self.regulator)

        super().readjust_acceleration()


class BrakeWithMaximumRateState(TrainSpeedRegulatorState):
    def set_the_acceleration(self) -> None:
        if (
            self.regulator.train.speed
            > self.regulator.train.current_block.current_speed_code(
                self.regulator.train
            )
        ):
            self.regulator.train.acceleration = -self.regulator.emergency_deceleration
        else:
            self.regulator.train.acceleration = 0

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorState]:
        if (
            self.regulator.train.speed
            <= self.regulator.train.current_block.current_speed_code(
                self.regulator.train
            )
        ):
            return KeepingTheSpeedUptoCodeState(self.regulator)

        return None

    def check_the_validity_of_the_acceleration(self) -> None:
        speed_code = self.regulator.train.current_speed_code
        if self.new_speed < speed_code:
            self.readjust_acceleration()

    def readjust_acceleration(self) -> None:
        target_acceleration = (
            self.regulator.train.current_speed_code - self.regulator.train.speed
        ) / self.regulator.train.time_step

        self.regulator.train.acceleration = target_acceleration

        super().readjust_acceleration()


class BrakeNormalToStationState(TrainSpeedRegulatorState):
    def __init__(self, regulator: TrainSpeedRegulator):
        super().__init__(regulator)

        self.distance_to_stop_before_station = randint(
            MIN_STOP_DISTANCE, MAX_STOP_DISTANCE
        )
        self.absolute_location_of_station = (
            self.regulator.train.total_travelled_distance
            + self.regulator.train.distance_to_next_station
        )

    def get_next_state(self) -> Optional[TrainSpeedRegulatorState]:
        if self.should_transition_to_break_with_maximum_rate_state():
            return BrakeWithMaximumRateState(self.regulator)
        return self.handle_custom_transition()

    def set_the_acceleration(self) -> None:
        # future_distance_travelled = (
        #     self.regulator.train.speed_in_fps * self.regulator.train.time_step
        #     + 0.5 * self.regulator.train.acceleration_in_fps2 * self.regulator.train.time_step**2
        # )

        distance_to_stop = (
            self.absolute_location_of_station
            - self.regulator.train.total_travelled_distance
            - self.distance_to_stop_before_station
            - 5
            # - future_distance_travelled
        )

        if distance_to_stop < 0:
            # required_deceleration = self.regulator.train.speed / self.regulator.train.time_step
            # required_deceleration_in_fps2 = (self.regulator.train.speed_in_fps**2) / (
            #     distance_to_stop + 5
            # )
            required_deceleration = self.regulator.emergency_deceleration
            # raise ValueError(
            #     "The distance to stop is less than the distance to stop before the station"
            # )
        else:
            required_deceleration_in_fps2 = (self.regulator.train.speed_in_fps**2) / (
                2 * (distance_to_stop)
            )

            required_deceleration = required_deceleration_in_fps2 / 5280 * 3600

        # if required_deceleration > 1.8 * self.regulator.emergency_deceleration:
        #     raise ValueError(
        #         "The required deceleration is more than the emergency deceleration by 80%"
        #     )

        self.regulator.train.acceleration = -required_deceleration

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorState]:
        if math.isclose(self.regulator.train.speed, 0, abs_tol=1e-2) or math.isclose(
            self.regulator.train.acceleration, 0, abs_tol=1e-1
        ):
            station = self.regulator.train.current_block.station
            assert station is not None, "Station is None"
            self.regulator.train_stopped_at_station(station)
            return LeavingTheStationState(self.regulator)

        return None

    def check_the_validity_of_the_acceleration(self) -> None:
        if self.new_speed < 0:
            self.readjust_acceleration()

    def readjust_acceleration(self) -> None:
        # required_acceleration = self.regulator.train.speed / self.regulator.train.time_step

        # future_distance_travelled = (
        #     self.regulator.train.speed_in_fps * self.regulator.train.time_step
        #     + 0.5 * self.regulator.train.acceleration_in_fps2 * self.regulator.train.time_step**2
        # )

        # distance_to_stop = (
        #     self.regulator.train.distance_to_next_station
        #     - future_distance_travelled
        #     - self.distance_to_stop_before_station
        # )

        # if distance_to_stop < -self.distance_to_stop_before_station:
        #     required_acceleration = (self.regulator.train.speed) / self.regulator.train.time_step
        #     # raise ValueError(
        #     # "The distance to stop is less than the distance to stop before the station"
        #     # )

        # else:
        # required_acceleration_fps2 = (self.regulator.train.speed_in_fps**2) / (2 * 5)

        # required_acceleration = required_acceleration_fps2 * 3600 / 5280
        required_acceleration = (
            self.regulator.train.speed / self.regulator.train.time_step
        )
        # required_acceleration = self.regulator.train.speed / self.regulator.train.time_step

        # if required_acceleration > self.regulator.emergency_deceleration:
        #     raise ValueError("The required deceleration is more than the emergency decceleration")

        self.regulator.train.acceleration = -required_acceleration
        super().readjust_acceleration()
