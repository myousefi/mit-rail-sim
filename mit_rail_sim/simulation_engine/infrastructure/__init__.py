from typing import Union

from .block import (
    AbstractBlock,
    Block,
    DispatchingBlockDecorator,
    DispatchingMovingBlockDecorator,
    MovingBlock,
    OffScanSymptomaticBlockDecorator,
    Terminal,
)
from .moving_control_center import MovingBlockControl
from .path import Path, SlowZone
from .signal_control_center import SignalControlCenter
from .station import Station

BlockType = Union[Block, MovingBlock]

__all__ = [
    "Block",
    "Terminal",
    "OffScanSymptomaticBlockDecorator",
    "DispatchingBlockDecorator",
    "AbstractBlock",
    "MovingBlock",
    "DispatchingMovingBlockDecorator",
    "MovingBlockControl",
    "BlockType",
    "Path",
    "SlowZone",
    "SignalControlCenter",
    "Station",
]
