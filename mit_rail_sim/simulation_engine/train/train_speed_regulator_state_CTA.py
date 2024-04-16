from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Tuple

# from mit_rail_sim.simulation_engine.train import TrainSpeedRegulatorCTA


if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import (
        OffScanSymptomaticBlockDecorator,
    )
    from mit_rail_sim.simulation_engine.train import TrainSpeedRegulatorCTA

MIN_STOP_DISTANCE = 5
MAX_STOP_DISTANCE = 10


class TrainSpeedRegulatorStateCTA(ABC):
    def __init__(self, regulator: TrainSpeedRegulatorCTA):
        self.regulator = regulator

    @property
    def current_speed_code(self) -> float:
        return (
            self.regulator.train.current_block.current_speed_code(self.regulator.train)
            * self.regulator.desired_speed_fraction
        )

    def handle(self) -> None:
        self.set_the_acceleration()
        self.check_the_validity_of_the_acceleration()
        self.handle_transition_to_next_state()

    def handle_transition_to_next_state(self) -> None:
        if next_state := self.get_next_state():
            self.regulator.state = next_state

    def get_next_state(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        # if not isinstance(self, DecelerateAndWaitForClearanceStateCTA):
        (
            need_to_decelerate_for_a_double_red_signal,
            next_block_index,
        ) = self.should_stop_for_a_double_red_signal()
        if need_to_decelerate_for_a_double_red_signal:
            return DecelerateAndWaitForClearanceStateCTA(
                self.regulator, next_block_index=next_block_index
            )

        if self.should_transition_to_brake_normal_to_station():
            return BrakeNormalToStationStateCTA(self.regulator)

        return self.handle_custom_transition()

    def should_stop_for_a_double_red_signal(self) -> Tuple[bool, Optional[int]]:
        # if self.regulator.state is not KeepingTheSpeedUptoCodeStateCTA:
        #     return False, None

        (
            distance_to_red_signal,
            red_signal_index,
        ) = self.regulator.train.block_with_red_signals_in_sight()
        if red_signal_index is None:
            return False, None

        return (
            self.regulator.braking_distance + 50 > distance_to_red_signal,
            red_signal_index,
        )

    def should_transition_to_brake_normal_to_station(self) -> bool:
        # future_distance_travelled = (
        #     self.regulator.train.speed_in_fps * self.regulator.train.time_step
        #     + 0.5 * self.regulator.train.acceleration_in_fps2 * self.regulator.train.time_step**2
        # )

        future_distance_to_next_station = (
            self.regulator.train.distance_to_next_station
            # - future_distance_travelled
            - 3 * MAX_STOP_DISTANCE
        )
        return future_distance_to_next_station <= self.regulator.braking_distance_for_station

    def entered_symptomatic_block(
        self, symptomatic_block: OffScanSymptomaticBlockDecorator
    ) -> None:
        self.regulator.state = StopAtSymptomaticBlockStateCTA(self.regulator, symptomatic_block)

    @abstractmethod
    def check_the_validity_of_the_acceleration(self) -> None:
        pass

    @abstractmethod
    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorStateCTA]:
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


class KeepingTheSpeedUptoCodeStateCTA(TrainSpeedRegulatorStateCTA):
    def set_the_acceleration(self) -> None:
        if math.isclose(
            self.current_speed_code,
            self.regulator.train.speed,
            abs_tol=self.regulator.TOLERANCE,
        ):
            self.regulator.train.acceleration = 0
            self.regulator.train.speed = self.current_speed_code

        elif self.regulator.train.speed < self.current_speed_code:
            self.regulator.train.acceleration = self.regulator.normal_acceleration

        elif self.regulator.train.speed > self.current_speed_code:
            self.regulator.train.acceleration = 0
            # -self.regulator.normal_deceleration

    def check_the_validity_of_the_acceleration(self) -> None:
        if self.regulator.train.acceleration > 0 and (self.new_speed > self.current_speed_code):
            self.regulator.train.acceleration = (
                self.current_speed_code - self.regulator.train.speed
            ) / self.regulator.train.time_step

        elif (self.regulator.train.acceleration < 0) and (self.new_speed < self.current_speed_code):
            self.regulator.train.acceleration = (
                -(self.current_speed_code - self.regulator.train.speed)
                / self.regulator.train.time_step
            )

        elif self.new_speed < 0:
            self.regulator.train.acceleration = (
                -self.regulator.train.speed / self.regulator.train.time_step
            )

    def readjust_acceleration(self) -> None:
        # target_acceleration = (
        #     (
        #         self.regulator.train.current_block.current_speed_code(self.regulator.train)
        #         * self.regulator.desired_speed_fraction
        #     )
        #     - self.regulator.train.speed
        # ) / self.regulator.train.time_step
        # self.regulator.train.acceleration = target_acceleration

        super().readjust_acceleration()

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        if self.regulator.train.speed > self.regulator.train.current_speed_code:
            return DelayedDecelerateToMeetTheCodeStateCTA(
                self.regulator, self.regulator.train.simulation.current_time
            )

        return None


class DecelerateAndWaitForClearanceStateCTA(TrainSpeedRegulatorStateCTA):
    def __init__(self, regulator: TrainSpeedRegulatorCTA, next_block_index: int):
        super().__init__(regulator)
        self.next_block_index = next_block_index
        self.target_decceleration = (
            -(self.regulator.train.speed_in_fps**2)
            / (2 * (self.distance_to_block_with_red_signal - 30))
            / 5280
            * 3600
        )

        self.target_decceleration = (
            self.target_decceleration
            if self.target_decceleration < 0
            else -self.regulator.emergency_deceleration
        )

        self.regulator.train.acceleration = self.target_decceleration

    @property
    def distance_to_block_with_red_signal(self) -> float:
        return (
            sum(
                block.length
                for block in self.regulator.train.path.blocks[
                    self.regulator.train.current_block_index : self.next_block_index
                ]
            )
            - self.regulator.train.distance_travelled_in_current_block
        )

    def handle_transition_to_next_state(self) -> None:
        if next_state := self.handle_custom_transition():
            self.regulator.state = next_state

    def set_the_acceleration(self) -> None:
        if math.isclose(
            self.regulator.train.speed,
            0,
            abs_tol=self.regulator.TOLERANCE,
        ):
            # self.regulator.
            self.regulator.train.acceleration = 0
            self.regulator.train.speed = 0

        else:
            self.regulator.train.acceleration = self.target_decceleration

    def check_the_validity_of_the_acceleration(self) -> None:
        if self.new_speed < 0:
            self.readjust_acceleration()

    def readjust_acceleration(self) -> None:
        target_acceleration = self.regulator.train.speed / self.regulator.train.time_step
        self.regulator.train.acceleration = -target_acceleration

        super().readjust_acceleration()

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        if (
            self.regulator.train.path.blocks[self.next_block_index].current_speed_code(
                self.regulator.train
            )
            > 0.0
            # or self.regulator.train.speed == 0.0
        ):
            return KeepingTheSpeedUptoCodeStateCTA(self.regulator)
        return None


class DelayedDecelerateToMeetTheCodeStateCTA(TrainSpeedRegulatorStateCTA):
    def __init__(self, regulator: TrainSpeedRegulatorCTA, start_time: float):
        super().__init__(regulator)
        self.start_time = start_time
        self.random_delay_amount = random.uniform(0, 1)
        self.regulator.train.acceleration = 0

    def check_the_validity_of_the_acceleration(self) -> None:
        pass

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        if (
            self.start_time + self.random_delay_amount
        ) < self.regulator.train.simulation.current_time:
            return DecelerateToMeetTheCodeStateCTA(self.regulator)
        return None

    def set_the_acceleration(self) -> None:
        self.regulator.train.acceleration = 0

    def readjust_acceleration(self) -> None:
        pass


class StopAtSymptomaticBlockStateCTA(TrainSpeedRegulatorStateCTA):
    def __init__(
        self,
        regulator: TrainSpeedRegulatorCTA,
        symptomatic_block: OffScanSymptomaticBlockDecorator,
    ):
        super().__init__(regulator)
        self.symptomatic_block = symptomatic_block
        self.time_to_get_clearance_from_control_center = random.uniform(10, 20)
        self.time_stopped = 0.0

    def check_the_validity_of_the_acceleration(self) -> None:
        if self.new_speed < 0:
            self.readjust_acceleration()

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        if math.isclose(self.regulator.train.speed, 0, abs_tol=self.regulator.TOLERANCE):
            self.time_stopped += self.regulator.train.time_step

        if self.time_stopped > self.time_to_get_clearance_from_control_center:
            self.symptomatic_block.set_unsymptomatic()
            return KeepingTheSpeedUptoCodeStateCTA(self.regulator)
        return None

    def set_the_acceleration(self) -> None:
        self.regulator.train.acceleration = -self.regulator.normal_deceleration

    def readjust_acceleration(self) -> None:
        self.regulator.train.acceleration = (
            -self.regulator.train.speed / self.regulator.train.time_step
        )

        super().readjust_acceleration()


class DecelerateToMeetTheCodeStateCTA(TrainSpeedRegulatorStateCTA):
    def check_the_validity_of_the_acceleration(self) -> None:
        if self.new_speed < 0:
            self.readjust_acceleration()
            return
        elif self.new_speed < self.current_speed_code:
            self.regulator.train.acceleration = (
                -(self.regulator.train.speed - self.current_speed_code)
                / self.regulator.train.time_step
            )

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        if self.new_speed <= self.current_speed_code:
            return KeepingTheSpeedUptoCodeStateCTA(self.regulator)
        return None

    def set_the_acceleration(self) -> None:
        self.regulator.train.acceleration = -self.regulator.normal_deceleration

    def readjust_acceleration(self) -> None:
        self.regulator.train.acceleration = (
            -self.regulator.train.speed / self.regulator.train.time_step
        )

        super().readjust_acceleration()


class LeavingTheStationStateCTA(KeepingTheSpeedUptoCodeStateCTA):
    def __init__(self, regulator: TrainSpeedRegulatorCTA):
        super().__init__(regulator)
        if self.regulator.train.current_block.station is None:
            raise ValueError("Train is leaving a station which is not the current block")

        self.station = self.regulator.train.current_block.station

    def get_next_state(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        if (
            self.regulator.train.distance_travelled_in_current_block
            > self.station.location_relative_to_block
        ):
            return KeepingTheSpeedUptoCodeStateCTA(self.regulator)
        return None


class BrakeNormalToStationStateCTA(TrainSpeedRegulatorStateCTA):
    def __init__(self, regulator: TrainSpeedRegulatorCTA):
        super().__init__(regulator)

        self.distance_to_stop_before_station = random.randint(MIN_STOP_DISTANCE, MAX_STOP_DISTANCE)

        self.next_station = (
            self.regulator.train.distance_to_next_station
            + self.regulator.train.total_travelled_distance
        )

        self.required_deceleration_in_fps2 = (self.regulator.train.speed_in_fps**2) / (
            2
            * (self.regulator.train.distance_to_next_station - self.distance_to_stop_before_station)
        )

        self.regulator.train.acceleration = -self.required_deceleration_in_fps2 / 5280 * 3600

    def set_the_acceleration(self) -> None:
        distance_to_stop = self.next_station - self.regulator.train.total_travelled_distance

        if distance_to_stop < 0:
            raise ValueError(
                "The distance to stop is less than the distance to stop before the station"
            )

        if distance_to_stop > 2 * self.distance_to_stop_before_station:
            required_deceleration_in_fps2 = self.required_deceleration_in_fps2
        else:
            required_deceleration_in_fps2 = self.regulator.normal_decceleration_in_fps2

        self.regulator.train.acceleration = -required_deceleration_in_fps2 / 5280 * 3600

    def get_next_state(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        # if not isinstance(self, DecelerateAndWaitForClearanceStateCTA):
        (
            need_to_decelerate_for_a_double_red_signal,
            next_block_index,
        ) = self.should_stop_for_a_double_red_signal()
        if need_to_decelerate_for_a_double_red_signal:
            return DecelerateAndWaitForClearanceStateCTA(
                self.regulator, next_block_index=next_block_index
            )

        return self.handle_custom_transition()

    def handle_custom_transition(self) -> Optional[TrainSpeedRegulatorStateCTA]:
        if not math.isclose(self.regulator.train.acceleration, 0, abs_tol=1e-3):
            return None

        if not math.isclose(self.regulator.train.speed, 0, abs_tol=1e-3):
            return None

        station = self.regulator.train.current_block.station
        assert station is not None, f"Station is None | Train: {self.regulator.train}"
        self.regulator.train_stopped_at_station(station)
        return LeavingTheStationStateCTA(self.regulator)

    def check_the_validity_of_the_acceleration(self) -> None:
        if self.new_speed < 0:
            self.readjust_acceleration()

    def readjust_acceleration(self) -> None:
        # required_acceleration = self.regulator.train.speed / self.regulator.train.time_step

        required_acceleration = self.regulator.train.speed / self.regulator.train.time_step

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
        #     raise ValueError(
        #         "The distance to stop is less than the distance to stop before the station"
        #     )

        # required_acceleration_fps2 = (self.regulator.train.speed_in_fps**2) / (
        #     2 * distance_to_stop
        # )

        # required_acceleration = required_acceleration_fps2 * 3600 / 5280

        # if required_acceleration > self.regulator.emergency_deceleration * 1.2:
        #     raise ValueError(
        #         "The required deceleration is +20% more than the emergency decceleration"
        #     )

        self.regulator.train.acceleration = -required_acceleration
        super().readjust_acceleration()
