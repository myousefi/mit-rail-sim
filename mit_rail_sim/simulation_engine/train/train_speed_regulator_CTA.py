from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Optional

from mit_rail_sim.simulation_engine.train.acceleration_profile_function import (
    get_acceleration_factor,
)
from mit_rail_sim.simulation_engine.train.train_speed_regulator_state_CTA import (
    KeepingTheSpeedUptoCodeStateCTA,
    TrainSpeedRegulatorStateCTA,
)

# from mit_rail_sim.simulation_engine.infrastructure.block import AbstractBlock, OffScanSymptomaticBlockDecorator


if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import (
        OffScanSymptomaticBlockDecorator,
        Station,
    )
    from mit_rail_sim.simulation_engine.train import Train


class TrainSpeedRegulatorCTA:
    def __init__(
        self,
        max_acceleration: float,
        normal_deceleration: float,
        emergency_deceleration: float,
        desired_speed_range: tuple[float, float] = (0.8, 1.0),
    ):
        self._train: Optional[Train] = None
        self.max_acceleration = max_acceleration
        self.normal_deceleration = normal_deceleration
        self.emergency_deceleration = emergency_deceleration
        self.state: TrainSpeedRegulatorStateCTA = KeepingTheSpeedUptoCodeStateCTA(self)
        self.desired_speed_range = desired_speed_range
        self.desired_speed_fraction = random.uniform(*self.desired_speed_range)

        self.TOLERANCE = 1e-2

    @property
    def train(self) -> Train:
        if self._train is None:
            raise ValueError("Train is not associated with this regulator")
        return self._train

    def update_desired_speed(self) -> None:
        self.desired_speed_fraction = random.uniform(*self.desired_speed_range)

    def register_train(self, train: Train) -> None:
        # if self._train is not None:
        #     raise ValueError("Train is already associated with this regulator")
        self._train = train
        train.train_speed_regulator = self

    def regulate_acceleration(self):
        self.state.handle()

    @property
    def normal_acceleration_in_fps2(self):
        return self.normal_acceleration * 5280 / 3600

    @property
    def normal_decceleration_in_fps2(self):
        return self.normal_deceleration * 5280 / 3600

    @property
    def normal_acceleration(self) -> float:
        speed = self.train.speed
        max_acceleration = 1

        acceleration_factor = get_acceleration_factor(speed)

        return 0.50 * acceleration_factor * max_acceleration

    @property
    def planning_distance(self) -> float:
        raise NotImplementedError

    @property
    def braking_distance(self) -> float:
        speed = self.train.speed_in_fps
        deceleration = self.normal_decceleration_in_fps2
        braking_distance = (speed**2) / (2 * deceleration)
        return braking_distance

    @property
    def braking_distance_for_station(self) -> float:
        speed = self.train.speed_in_fps
        deceleration = 0.5 * self.normal_decceleration_in_fps2
        braking_distance = (speed**2) / (2 * deceleration)
        return braking_distance

    def train_stopped_at_station(self, station: Station) -> None:
        self.train.speed = 0
        self.train.acceleration = 0
        self.train.set_state_to_dwelling_at_station(station)

    def update_train_speed(self) -> None:
        new_speed = self.train.speed + self.train.acceleration * self.train.time_step

        if math.isclose(new_speed, 0, abs_tol=self.TOLERANCE):
            new_speed = 0
        elif new_speed < 0:
            raise ValueError(f"New speed {new_speed} is negative!")

        self.train.speed = new_speed

    def entered_symptomatic_block(
        self, symptomatic_block: OffScanSymptomaticBlockDecorator
    ) -> None:
        self.train.train_logger.log_warning(
            f"entered symptomatic block: {symptomatic_block.block_id}",
            train=self.train,
        )
        self.state.entered_symptomatic_block(symptomatic_block)
