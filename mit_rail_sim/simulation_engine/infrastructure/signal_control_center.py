from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import Block


class SignalControlCenter:
    def __init__(self, blocks: List[Block]):
        self.blocks = blocks

        for block in self.blocks:
            block.add_observer(self)

    def update(self, block: Block) -> None:
        if block.is_occupied:
            self.send_speed_codes_to_upstream_blocks(block)
        else:
            self.restore_speed_codes_to_upstream_blocks(block)

    # def get_upstream_blocks(self, block: Block) -> List[Block]:
    #     # Implement the logic to find and return the upstream blocks of a given block
    #     return []

    def get_block_by_id(self, block_id: str) -> Optional[Block]:
        return next((block for block in self.blocks if block.block_id == block_id), None)

    def send_speed_codes_to_upstream_blocks(self, block: Block) -> None:
        for upstream_block_id, speed_code in block.speed_codes_to_communicate.items():
            upstream_block = self.get_block_by_id(upstream_block_id)
            if upstream_block is not None:
                upstream_block.add_communicated_speed_code(block.block_id, speed_code)

    def restore_speed_codes_to_upstream_blocks(self, block: Block) -> None:
        for upstream_block_id in block.speed_codes_to_communicate.keys():
            upstream_block = self.get_block_by_id(upstream_block_id)
            if upstream_block is not None:
                upstream_block.remove_communicated_speed_code(block.block_id)
