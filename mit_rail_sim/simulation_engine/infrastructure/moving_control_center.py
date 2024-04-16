from __future__ import annotations

import math
from typing import List

from mit_rail_sim.simulation_engine.infrastructure import MovingBlock
from mit_rail_sim.simulation_engine.train import Train


class MovingBlockControl:
    def __init__(self, blocks: List[MovingBlock], safety_margin: float = 200) -> None:
        self.safety_margin = safety_margin
        for block in blocks:
            block.register_moving_block_control_center(self)

    def get_distance_to_next_train(self, asking_train: Train) -> float:
        next_blocks_list = asking_train.path.blocks[
            asking_train.current_block_index + 1 : asking_train.current_block_index + 10
        ]
        next_train = asking_train.current_block.next_train(asking_train)
        while next_train is None and next_blocks_list:
            block = next_blocks_list.pop(0)
            if block.current_train:
                next_train = block.current_train

        if next_train is None:
            return float("inf")

        distance_to_next_train = (
            (
                sum(
                    block.length
                    for block in asking_train.path.blocks[
                        asking_train.current_block_index : next_train.current_block_index
                    ]
                )
                + next_train.distance_travelled_in_current_block
            )
            - next_train.length
        ) - asking_train.distance_travelled_in_current_block

        return distance_to_next_train

    def needed_braking_distance(self, asking_train: Train) -> float:
        return self.get_distance_to_next_train(asking_train) - self.safety_margin

    def get_speed_code(self, asking_train: Train, asking_block: MovingBlock) -> float:
        needed_braking_distance = self.needed_braking_distance(asking_train)

        if needed_braking_distance < 0:
            return 0

        if asking_train.train_speed_regulator.braking_distance < needed_braking_distance:
            return asking_block.civil_speed_limit

        return min(
            math.sqrt(
                needed_braking_distance
                * 2
                * asking_train.train_speed_regulator.normal_decceleration_in_fps2
            )
            / 5280
            * 3600,
            asking_block.civil_speed_limit,
        )
