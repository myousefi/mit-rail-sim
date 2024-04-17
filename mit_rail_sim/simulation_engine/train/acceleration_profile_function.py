from __future__ import annotations

from typing import List, Optional, Tuple


def get_acceleration_factor(
    speed: float, breakpoints: Optional[List[Tuple[float, float]]] = None
) -> float:
    if breakpoints is None:
        breakpoints = [
            (22, 3.94),
            (29.3, 3.85),
            (37.7, 3.69),
            (44, 2.9),
            (51.3, 2.35),
            (58.7, 1.71),
            (66, 1.22),
        ]
    # speed /= 1.467  # Convert the input speed from ft/s to mph

    if speed <= breakpoints[0][0]:
        return breakpoints[0][1]
    # * 1.467  # Convert the output acceleration from mph/s to ft/s^2

    for i in range(1, len(breakpoints)):
        if speed <= breakpoints[i][0]:
            x_1, y_1 = breakpoints[i - 1]
            x_2, y_2 = breakpoints[i]
            slope = (y_2 - y_1) / (x_2 - x_1)
            return y_1 + slope * (speed - x_1)
            # * 1.467  # Convert the output acceleration from mph/s to ft/s^2

    return breakpoints[-1][1]


# * 1.467  # Convert the output acceleration from mph/s to ft/s^2
