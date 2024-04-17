from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from mit_rail_sim.simulation_engine.infrastructure import AbstractBlock

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import (
        MovingBlockControl,
        Station,
    )
    from mit_rail_sim.simulation_engine.train import Train


# class MovingBlock(AbstractBlock):
#     def __init__(self, *args, moving_block_control_center: MovingBlockControl, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.moving_block_control_center = moving_block_control_center
#         self.current_train_list: List[Train] = []

#     @property
#     def current_train(self) -> Optional[Train]:
#         return self.current_train_list[0] if self.current_train_list else None

#     @property
#     def next_train(self) -> Optional[Train]:
#         return None if len(self.current_train_list) < 2 else self.current_train_list[1]

#     @property
#     def is_occupied(self) -> bool:
#         return bool(self.current_train_list)

#     def is_occupied_by(self, train: Train) -> bool:
#         return train in self.current_train_list

#     def activate(self, entering_train: Train) -> None:
#         self.current_train_list.append(entering_train)

#     def deactivate(self, exiting_train: Train) -> None:
#         self.current_train_list.remove(exiting_train)

#     @property
#     def civil_speed_limit(self) -> float:
#         return min(self.default_speed_code, self.slow_zone_reduced_speed_limit)

#     def current_speed_code(self, requesting_train: Train) -> float:
#         return self.moving_block_control_center.get_speed_code(requesting_train, self)
