from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import (
        MovingBlockControl,
        Path,
        SignalControlCenter,
        Station,
    )
    from mit_rail_sim.simulation_engine.train import Train
    from mit_rail_sim.simulation_engine.utils import BlockActivationLogger


class ReleasingNotOccupiedBlock(Exception):
    pass


class AbstractBlock(ABC):
    def __init__(
        self,
        block_id: str,
        block_alt_name: str,
        visible_distance: float,
        length: float,
        default_speed_code: float,
        station: Optional[Station] = None,
    ):
        self.block_id = block_id
        self.block_alt_name: str = block_alt_name

        self.visible_distance = visible_distance
        self.length = length
        self.default_speed_code = default_speed_code

        self.slow_zone_reduced_speed_limit = float("inf")
        self.station = station

        self.dist_from_terminal: Optional[float] = None

        if self.station and self.station.location_relative_to_block > self.length:
            raise ValueError(
                f"Station location is greater than block length. {self.station.name}"
            )

    @property
    @abstractmethod
    def is_occupied(self) -> bool:
        pass

    @abstractmethod
    def is_occupied_by(self, train: Train) -> bool:
        pass

    @abstractmethod
    def current_speed_code(self, requesting_train: Train) -> float:
        pass

    def set_slow_zone(self, speed_limit: float):
        self.slow_zone_reduced_speed_limit = speed_limit


class Block(AbstractBlock):
    block_logger: Optional[BlockActivationLogger] = None

    def __init__(
        self,
        *args,
        speed_codes_to_communicate: Optional[Dict[str, float]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.current_train: Optional[Train] = None
        self.observers: List[SignalControlCenter] = []

        self.speed_codes_to_communicate = speed_codes_to_communicate or {}
        self.communicated_speed_codes: Dict[str, float] = {}
        self._last_train_visit_time: float = -float("inf")

        self.headway: float = 0.0

    @property
    def last_train_visit_time(self) -> float:
        return self._last_train_visit_time

    @last_train_visit_time.setter
    def last_train_visit_time(self, value: float) -> None:
        self.headway = value - self._last_train_visit_time
        self._last_train_visit_time = value

    @property
    def is_occupied(self) -> bool:
        return self.current_train is not None

    def is_occupied_by(self, train: Train) -> bool:
        return self.current_train == train

    def current_speed_code(self, requesting_train: Train) -> float:
        if self.current_train is not None and self.current_train != requesting_train:
            return 0.0

        communicated_min_speed = min(
            self.communicated_speed_codes.values(), default=float("inf")
        )

        return min(
            self.default_speed_code,
            communicated_min_speed,
            self.slow_zone_reduced_speed_limit,
        )

    def set_slow_zone(self, speed_limit: float):
        if self.slow_zone_reduced_speed_limit:
            self.slow_zone_reduced_speed_limit = min(
                self.slow_zone_reduced_speed_limit, speed_limit
            )

    def add_communicated_speed_code(self, block_id: str, speed_code: float) -> None:
        self.communicated_speed_codes[block_id] = speed_code

    def remove_communicated_speed_code(self, block_id: str) -> None:
        self.communicated_speed_codes.pop(block_id, None)

    def add_observer(self, observer: SignalControlCenter) -> None:
        self.observers.append(observer)

    def notify_observers(self) -> None:
        for observer in self.observers:
            observer.update(self)

    def activate(self, entering_train: Train) -> None:
        if self.current_train is not None:
            raise ValueError(
                (
                    f"The block {self.block_id} is already occupied by another train."
                    f" Replication_id {self.current_train.simulation.replication_id}, current train"
                    f" id {self.current_train.train_id}, entering train id"
                    f" {entering_train.train_id}, current_time"
                    f" {entering_train.simulation.current_time}"
                ),
            )

        self.current_train = entering_train
        self.notify_observers()

        if self.block_logger and entering_train.should_log():
            self.block_logger.log_block_activation(self, entering_train)

        self.last_train_visit_time = entering_train.simulation.current_time

        entering_train.train_speed_regulator.update_desired_speed()

    def deactivate(self, exiting_train: Train) -> None:
        if self.current_train == exiting_train:
            self.current_train = None
            self.notify_observers()

        else:
            raise ReleasingNotOccupiedBlock(
                "The block is being released by a train that is not in this block."
            )


class MovingBlock(AbstractBlock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_train_list: List[Train] = []

    def register_moving_block_control_center(self, moving_block_control) -> None:
        self.moving_block_control_center = moving_block_control

    @property
    def sorted_current_train_list(self) -> List[Train]:
        return sorted(
            self.current_train_list,
            key=lambda t: (
                t.distance_traveled_from_the_start_of_block(self),
                -t.dispatching_time,
            ),
        )

    def next_train(self, requesting_train: Train) -> Optional[Train]:
        if self.current_train_list:
            # sorted_current_train_list = self.sorted_current_train_list
            next_train_index = self.current_train_list.index(requesting_train) - 1
            if 0 <= next_train_index < len(self.current_train_list):
                return self.current_train_list[next_train_index]
        return None

    @property
    def current_train(self) -> Optional[Train]:
        return self.sorted_current_train_list[-1] if self.current_train_list else None

    @property
    def is_occupied(self) -> bool:
        return bool(self.current_train_list)

    def is_occupied_by(self, train: Train) -> bool:
        return train in self.current_train_list

    def activate(self, entering_train: Train) -> None:
        self.current_train_list.append(entering_train)

    def deactivate(self, exiting_train: Train) -> None:
        try:
            self.current_train_list.remove(exiting_train)
        except ValueError:
            raise ReleasingNotOccupiedBlock(
                "The block is being released by a train that is not in this block."
            )

    @property
    def civil_speed_limit(self) -> float:
        return min(self.default_speed_code, self.slow_zone_reduced_speed_limit)

    def current_speed_code(self, requesting_train: Train) -> float:
        return self.moving_block_control_center.get_speed_code(requesting_train, self)


class DispatchingMovingBlockDecorator(MovingBlock):
    def __init__(
        self,
        block: MovingBlock,
        path: Path,
        dispatch_margin: float = 120,
        upstream_blocks: List[str] = [],
    ):
        self.__dict__ = block.__dict__.copy()

        self.dispatch_margin = dispatch_margin
        self.upstream_blocks = upstream_blocks
        self._last_train_visit_time: float = -float("inf")
        self.path = path

    @property
    def last_train_visit_time(self) -> float:
        return self._last_train_visit_time

    @last_train_visit_time.setter
    def last_train_visit_time(self, value: float) -> None:
        self._last_train_visit_time = value

    def is_it_clear_to_dispatch(self) -> bool:
        if self.upstream_blocks:
            return all(
                not self.path.get_block_by_id(block_id).is_occupied
                for block_id in self.upstream_blocks
            )
        else:
            return True

    def ready_to_dispatch(self, train: Train) -> bool:
        return (
            self.is_it_clear_to_dispatch()
            and train.simulation.current_time
            > self.last_train_visit_time + self.dispatch_margin
        )

    def activate(self, entering_train: Train) -> None:
        super().activate(entering_train)
        self.last_train_visit_time = entering_train.simulation.current_time


class OffScanSymptomaticBlockDecorator(Block):
    def __init__(
        self,
        block: Block,
        path: Path,
        offscan_probability: float = 0.01,
    ):
        self.__dict__ = block.__dict__.copy()

        self.path = path

        self.offscan_probability = offscan_probability
        self._is_symptomatic = False

    def set_unsymptomatic(self) -> None:
        self._is_symptomatic = False

    def activate(self, entering_train: Train) -> None:
        super().activate(entering_train)

        random_number = random.uniform(0, 1)
        if random_number < self.offscan_probability:
            self._is_symptomatic = True
            entering_train.train_speed_regulator.entered_symptomatic_block(self)

    def current_speed_code(self, requesting_train: Train) -> float:
        if self.current_train is not None and self.current_train != requesting_train:
            return 0.0

        if self.current_train == requesting_train and self._is_symptomatic:
            return 0.0

        communicated_min_speed = min(
            self.communicated_speed_codes.values(), default=float("inf")
        )

        return min(
            self.default_speed_code,
            communicated_min_speed,
            self.slow_zone_reduced_speed_limit,
        )


class DispatchingBlockDecorator(Block):
    def __init__(
        self,
        block: Block,
        path: Path,
        dispatch_margin: float = 120,
        upstream_blocks: List[str] = [],
    ):
        self.__dict__ = block.__dict__.copy()

        self.current_train: Optional[Train] = None
        self.observers: List[SignalControlCenter] = []

        self.dispatch_margin = dispatch_margin
        self.upstream_blocks = upstream_blocks
        self._last_train_visit_time: float = -float("inf")
        self.path = path

    @property
    def last_train_visit_time(self) -> float:
        return self._last_train_visit_time

    @last_train_visit_time.setter
    def last_train_visit_time(self, value: float) -> None:
        self._last_train_visit_time = value

    def is_it_clear_to_dispatch(self) -> bool:
        if self.upstream_blocks:
            return all(
                not self.path.get_block_by_id(block_id).is_occupied
                for block_id in self.upstream_blocks
            )
        else:
            return True

    def ready_to_dispatch(self, train: Train) -> bool:
        return (
            self.is_it_clear_to_dispatch()
            and train.simulation.current_time
            > self.last_train_visit_time + self.dispatch_margin
        )

    def activate(self, entering_train: Train) -> None:
        super().activate(entering_train)
        self.last_train_visit_time = entering_train.simulation.current_time


class Terminal(Block):
    def __init__(
        self,
    ):
        super().__init__(
            "Terminal",
            block_alt_name="Terminal",
            visible_distance=10,
            length=100,
            default_speed_code=10,
        )
        self.speed_code_for_terminal = 10

        self.current_trains: Optional[Train] = []

        self.is_the_first_southbound_arrived = True

    def current_speed_code(self, requesting_train: Train) -> float:
        return self.speed_code_for_terminal

    def activate(self, entering_train: Train) -> None:
        # if entering_train.path.direction == "Southbound":
        #     try:
        #         if self.is_the_first_southbound_arrived:
        #             entering_train.simulation.schedule.remove_all_northbound_trains()
        #             self.is_the_first_southbound_arrived = False

        #         entering_train.simulation.schedule.adjust_next_departure(
        #             arrival_time=entering_train.simulation.current_time,
        #             arriving_train=entering_train,
        #         )
        #     except AttributeError as e:
        #         raise e
        entering_train.delete()


class ShortTurningBlock(Block):
    def __init__(
        self,
        length: float = 48 * 8 + 100,
    ):
        super().__init__(
            "ShortTurningBlock",
            block_alt_name="ShortTurningBlock",
            visible_distance=10,
            length=length,
            default_speed_code=6,
        )

        self.current_train: Optional[Train] = None

    def current_speed_code(self, requesting_train: Train) -> float:
        return self.default_speed_code

    def activate(self, entering_train: Train) -> None:
        pass
        # self.current_train = entering_train

        # if self.current_train is not None:
        #     raise ValueError("The ShortTurningBlock is already occupied by another train.")

        # self.current_train = entering_train
        # entering_train._should_log = False

    def deactivate(self, exiting_train: Train) -> None:
        pass
        # if self.current_train == exiting_train:
        #     self.current_train = None
        # else:
        #     raise ReleasingNotOccupiedBlock(
        #         "The ShortTurningBlock is being released by a train that is not in this block."
        #     )
        # if self.current_train == exiting_train:
        #     self.current_train = None
        # else:
        #     raise ReleasingNotOccupiedBlock(
        #         "The ShortTurningBlock is being released by a train that is not in this block."
        #     )


class ShortTurner(Block):
    def __init__(
        self,
    ):
        super().__init__(
            "ShortTurner",
            block_alt_name="ShortTurner",
            visible_distance=10,
            length=10,
            default_speed_code=1,
        )

    def activate(self, entering_train: Train) -> None:
        entering_train.path.short_turn(entering_train)
