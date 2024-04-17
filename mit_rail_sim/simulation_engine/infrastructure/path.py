from __future__ import annotations

import json
import random
from copy import deepcopy
from typing import TYPE_CHECKING, List

import numpy as np
from scipy import stats
from scipy.stats import truncnorm

from mit_rail_sim.config_handler import get_config


def get_truncated_normal(mean=0, sd=1, low=0, upp=10):
    return truncnorm((low - mean) / sd, (upp - mean) / sd, loc=mean, scale=sd)


from mit_rail_sim.simulation_engine.infrastructure import (
    Block,
    DispatchingBlockDecorator,
    DispatchingMovingBlockDecorator,
    MovingBlock,
    Terminal,
)
from mit_rail_sim.simulation_engine.infrastructure.block import (
    OffScanSymptomaticBlockDecorator,
    ShortTurner,
    ShortTurningBlock,
)
from mit_rail_sim.simulation_engine.train.train_state import (
    SettingUpForShortTurning,
    SettingUpForShortTurningAtStation,
)

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure.station import Station
    from mit_rail_sim.simulation_engine.train import Train

import os

from mit_rail_sim.utils import project_root

PARAMS_FILE_PATH = project_root / "inputs/insepction_time_distribution.json"
PARAMS_DICT = None


def load_params():
    global PARAMS_DICT
    if PARAMS_DICT is None:
        with open(PARAMS_FILE_PATH, "r") as f:
            PARAMS_DICT = json.load(f)


def get_high_inspection_time():
    load_params()

    # Get the distribution name and parameters
    distribution_name = PARAMS_DICT["Distribution"]
    params = PARAMS_DICT["Parameters"]

    # Get the distribution from scipy.stats
    distribution = getattr(stats, distribution_name)

    return float(distribution.rvs(*params) * 60)


def get_medium_inspection_time():
    return min(4 * 60, get_high_inspection_time())


def get_low_inspection_time():
    return min(1 * 60, get_high_inspection_time())


class SlowZone:
    def __init__(self, block_id: str, reduced_speed_limit: float):
        self.block_id = block_id
        self.reduced_speed_limit = reduced_speed_limit

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "reduced_speed_limit": self.reduced_speed_limit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SlowZone":
        return cls(
            block_id=str(data.get("block_id")),
            reduced_speed_limit=float(data.get("reduced_speed_limit")),
        )


class Path:
    def __init__(
        self,
        direction: str,
        blocks: List[MovingBlock | Block],
        slow_zones: List[SlowZone] = [],
    ):
        self.blocks = blocks

        terminal_block = Terminal()

        self.blocks.append(terminal_block)

        self.direction = direction

        for slow_zone in slow_zones:
            try:
                self.set_block_slow_zone(slow_zone.block_id, slow_zone.reduced_speed_limit)
            except ValueError as e:
                pass
                # print(e)

        self.path_distance_alignment()

    def path_distance_alignment(self) -> None:
        if self.direction == "Northbound":
            dist = 0.0
            for nb_block in self.blocks:
                nb_block.dist_from_terminal = dist
                dist += nb_block.length
        else:
            dist = sum(block.length for block in self.blocks)
            for sb_block in self.blocks:
                sb_block.dist_from_terminal = dist
                dist -= sb_block.length

    def is_short_turn(self) -> bool:
        return False

    def is_short_turned_at_this_station(self, station: Station) -> bool:
        return False

    def is_inspected(self) -> bool:
        return False

    def short_turn(self, train: Train):
        raise NotImplementedError

    def set_block_slow_zone(self, block_id: str, speed_limit: float):
        block = self.get_block_by_id(block_id)
        block.set_slow_zone(speed_limit)

    def get_block_by_id(self, block_id: str) -> MovingBlock | Block:
        for block in self.blocks:
            if block.block_id == block_id:
                return block
        raise ValueError(f"No block found with id {block_id}")

    def get_block_index_by_id(self, block_id: str) -> int:
        for i, block in enumerate(self.blocks):
            if block.block_id == block_id:
                return i
        raise ValueError(f"No block found with id {block_id}")

    def make_offscan_block(self, block_index: int, offscan_probability: float):
        block = self.blocks[block_index]

        if isinstance(block, MovingBlock):
            raise ValueError("Cannot make offscan block for moving block")

        offscan_block = OffScanSymptomaticBlockDecorator(
            block=block, path=self, offscan_probability=offscan_probability
        )

        self.blocks[block_index] = offscan_block

    def make_dispatching_block(
        self,
        block_id: str,
        dispatch_margin: float = 120,
        upstream_blocks: List[str] = [],
    ):
        # block = self.blocks[block_index]
        block = self.get_block_by_id(block_id)
        block_index = self.get_block_index_by_id(block_id)

        dispatching_block: DispatchingBlockDecorator | DispatchingMovingBlockDecorator

        if isinstance(block, Block):
            dispatching_block = DispatchingBlockDecorator(
                block=block,
                path=self,
                dispatch_margin=dispatch_margin,
                upstream_blocks=upstream_blocks,
            )
        else:
            dispatching_block = DispatchingMovingBlockDecorator(
                block=block,
                path=self,
                dispatch_margin=dispatch_margin,
                upstream_blocks=upstream_blocks,
            )
        # dispatching_block.set_path(self)
        self.blocks[block_index] = dispatching_block

    def get_total_length(self) -> float:
        return sum(block.length for block in self.blocks)

    def get_all_stops_ahead(self, block_index: int) -> List[Station]:
        stops_ahead = [block.station for block in self.blocks[block_index + 1 :] if block.station]
        return stops_ahead

    def get_all_stops_ahead_which_are_served(self, block_index: int) -> List[Station]:
        stops_ahead = [
            block.station.name for block in self.blocks[block_index + 1 :] if block.station
        ]
        return stops_ahead

    def get_distance_to_the_next_station(
        self, current_block_index: int, current_location_on_block: float
    ) -> float:
        distance_to_the_next_station = 0.0

        for block in self.blocks[current_block_index:]:
            if (
                block.station
                and current_location_on_block < block.station.location_relative_to_block
            ):
                distance_to_the_next_station += (
                    block.station.location_relative_to_block - current_location_on_block
                )
                return distance_to_the_next_station
            distance_to_the_next_station += block.length - current_location_on_block
            current_location_on_block = 0.0

        return float("inf")

    def get_total_travelled_distance(
        self, current_block_index: int, distance_travelled_in_current_block: float
    ) -> float:
        if self.direction == "Northbound":
            return (
                self.blocks[current_block_index].dist_from_terminal
                + distance_travelled_in_current_block
            )
        elif self.direction == "Southbound":
            return (
                self.blocks[current_block_index].dist_from_terminal
                - distance_travelled_in_current_block
            )

    def get_next_train(self, current_block_index: int) -> Train | None:
        for block in self.blocks[current_block_index:]:
            if block.current_train:
                return block.current_train
        return None

    def get_previous_train(self, current_block_index: int) -> Train | None:
        for block in reversed(self.blocks[:current_block_index]):
            if following_train := block.current_train:
                if following_train.current_block_index != current_block_index:
                    return following_train
                # return block.current_train
        return None

    def copy(self):
        return deepcopy(self)


class ShortTurningPath(Path):
    def __init__(
        self,
        sb_path: Path,
        nb_path: Path,
        sb_juncture_block_id: str,
        nb_juncture_block_id: str,
        # set_up_time_distribution: any,
    ):
        self.sb_path = sb_path
        self.nb_path = nb_path
        self.sb_juncture_block_id = sb_juncture_block_id
        self.nb_juncture_block_id = nb_juncture_block_id

        # self.set_up_time_distribution = set_up_time_distribution
        self.direction = self.sb_path.direction

        self.blocks = sb_path.blocks[: sb_path.get_block_index_by_id(sb_juncture_block_id) + 1]

        short_turning_block = ShortTurningBlock()
        short_turner = ShortTurner()

        short_turning_block.dist_from_terminal = (
            self.blocks[-1].dist_from_terminal - self.blocks[-1].length
        )

        short_turner.dist_from_terminal = (
            short_turning_block.dist_from_terminal - short_turning_block.length
        )

        self.blocks.append(short_turning_block)
        self.blocks.append(short_turner)

    def get_all_stops_ahead(self, block_index: int) -> List[Station]:
        stops_ahead = [
            block.station for block in self.sb_path.blocks[block_index + 1 :] if block.station
        ]
        return stops_ahead

    def get_all_stops_ahead_which_are_served(self, block_index: int) -> List[Station]:
        stops_ahead = [
            block.station.name for block in self.blocks[block_index + 1 :] if block.station
        ]
        return stops_ahead

    def get_total_travelled_distance(
        self, current_block_index: int, distance_travelled_in_current_block: float
    ) -> float:
        if current_block_index > len(self.blocks) - 2:
            return self.nb_path.get_block_by_id(self.nb_juncture_block_id).dist_from_terminal

        if self.direction == "Northbound":
            return (
                self.blocks[current_block_index].dist_from_terminal
                + distance_travelled_in_current_block
            )
        elif self.direction == "Southbound":
            return (
                self.blocks[current_block_index].dist_from_terminal
                - distance_travelled_in_current_block
            )

    def is_short_turn(self) -> bool:
        return True

    def is_short_turned_at_this_station(self, station: Station) -> bool:
        last_station = None
        for block in reversed(self.blocks):
            if block.station:
                last_station = block.station
                break

        return station == last_station

    def is_inspected(self):
        return True

    # def get_inspection_time(self):
    #     if cfg := get_config():
    #         inspection = cfg.inspection_time
    #         if inspection == "Low":
    #             return random.uniform(1 * 60, 2 * 60)
    #         elif inspection == "Medium":
    #             return random.uniform(2 * 60, 6 * 60)
    #         elif inspection == "High":
    #             return random.uniform(4 * 60, 8 * 60)

    #     else:
    #         return random.uniform(4 * 60, 6 * 60)

    def get_inspection_time(self):
        if cfg := get_config():
            inspection = cfg.inspection_time

            # Define mean and standard deviation for each case
            if inspection == "Low":
                return get_low_inspection_time()
            elif inspection == "Medium":
                return get_medium_inspection_time()
            elif inspection == "High":
                return get_high_inspection_time()

        else:
            return get_high_inspection_time()

    def short_turn(self, train: Train):
        train.speed = 0.0
        train.acceleration = 0.0
        train.distance_travelled_in_current_block = 0.0

        train.path = self.nb_path
        train.starting_block_index = self.nb_path.get_block_index_by_id(self.nb_juncture_block_id)
        train.current_block_index = train.starting_block_index
        train.distance_travelled_in_current_block = 0.0

        train.state = SettingUpForShortTurning(train, random.uniform(2 * 60, 3 * 60))


class ShortTurningAtWestern(Path):
    def __init__(
        self,
        sb_path: Path,
        nb_path: Path,
        sb_juncture_block_id: str,
        nb_juncture_block_id: str,
        # set_up_time_distribution: any,
    ):
        self.sb_path = sb_path
        self.nb_path = nb_path
        self.sb_juncture_block_id = sb_juncture_block_id
        self.nb_juncture_block_id = nb_juncture_block_id

        # self.set_up_time_distribution = set_up_time_distribution
        self.direction = self.sb_path.direction

        self.blocks = sb_path.blocks[: sb_path.get_block_index_by_id(sb_juncture_block_id) + 1]

        short_turning_block = ShortTurningBlock(length=10)
        short_turner = ShortTurner()

        short_turning_block.dist_from_terminal = (
            self.blocks[-1].dist_from_terminal - self.blocks[-1].length
        )

        short_turner.dist_from_terminal = (
            short_turning_block.dist_from_terminal - short_turning_block.length
        )

        self.blocks.append(short_turning_block)
        self.blocks.append(short_turner)

    def get_all_stops_ahead(self, block_index: int) -> List[Station]:
        stops_ahead = [
            block.station for block in self.sb_path.blocks[block_index:] if block.station
        ]
        return stops_ahead

    def get_all_stops_ahead_which_are_served(self, block_index: int) -> List[Station]:
        stops_ahead = [block.station.name for block in self.blocks[block_index:] if block.station]
        return stops_ahead

    def get_total_travelled_distance(
        self, current_block_index: int, distance_travelled_in_current_block: float
    ) -> float:
        if current_block_index > len(self.blocks) - 2:
            return self.nb_path.get_block_by_id(self.nb_juncture_block_id).dist_from_terminal

        if self.direction == "Northbound":
            return (
                self.blocks[current_block_index].dist_from_terminal
                + distance_travelled_in_current_block
            )
        elif self.direction == "Southbound":
            return (
                self.blocks[current_block_index].dist_from_terminal
                - distance_travelled_in_current_block
            )

    def is_short_turn(self) -> bool:
        return True

    def is_short_turned_at_this_station(self, station: Station) -> bool:
        last_station = None
        for block in reversed(self.blocks):
            if block.station:
                last_station = block.station
                break

        return station == last_station

    def short_turning_station(self) -> Station:
        return next(
            (
                block.station
                for block in reversed(
                    self.nb_path.blocks[
                        : self.nb_path.get_block_index_by_id(self.nb_juncture_block_id)
                    ]
                )
                if block.station
            ),
            None,
        )

    def is_inspected(self) -> bool:
        return False

    def short_turn(self, train: Train):
        train.speed = 0.0
        train.acceleration = 0.0
        train.distance_travelled_in_current_block = 0.0

        train.path = self.nb_path

        train.starting_block_index = self.nb_path.get_block_index_by_id(self.nb_juncture_block_id)
        train.current_block_index = train.starting_block_index
        train.distance_travelled_in_current_block = 0.0

        blocks = [
            self.sb_path.get_block_by_id("WD-111"),
            self.sb_path.get_block_by_id("WD-106"),
            self.sb_path.get_block_by_id("623"),
        ]

        train.state = SettingUpForShortTurningAtStation(
            train,
            random.uniform(4 * 60, 5 * 60),
            station=self.short_turning_station(),
            blocks=blocks,
        )
