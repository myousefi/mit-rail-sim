from __future__ import annotations

import random
import warnings
from copy import deepcopy
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from mit_rail_sim.simulation_engine.schedule import EmpiricalSchedule, Schedule
from mit_rail_sim.simulation_engine.simulation import Simulation, SimulationContext

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.utils.logger_context import LoggerContext


class ReplicationManager:
    def __init__(
        self,
        number_of_replications: int,
        logger_context: LoggerContext,
        train_speed_regulator: str = "CTA",
    ):
        self.number_of_replications = number_of_replications
        self.logger_context = logger_context
        self.seed_numbers: List[int] = []
        self.train_speed_regulator = train_speed_regulator

        self.generate_seed_numbers()

    def generate_seed_numbers(self) -> None:
        self.seed_numbers = [
            random.randint(0, 2**32 - 1) for _ in range(self.number_of_replications)
        ]

    def run_replications(
        self,
        schedule,
        path_initializer_function,
        data,
        slow_zones,
        total_time: float,
        start_hour: int = 5,
        seed_numbers: Optional[List[int]] = None,
    ) -> None:
        with self.logger_context:
            for seed_number in self.seed_numbers if seed_numbers is None else seed_numbers:
                random.seed(seed_number)
                schedule.generate_random_dispatch_info()

                path, signal_control_center = path_initializer_function(data, slow_zones)

                simulation = Simulation(
                    schedule=schedule,
                    path=path,
                    signal_control_center=signal_control_center,
                    train_speed_regulator=self.train_speed_regulator,
                    total_time=total_time,
                    start_hour=start_hour,
                )

                simulation.replication_id = seed_number
                simulation_context = SimulationContext(simulation)

                try:
                    with simulation_context:
                        simulation.run()
                except Exception as e:
                    warnings.warn(f"Exception {e} raised during replication {seed_number}")
                    self.seed_numbers.append(random.randint(0, 2**32 - 1))
                    continue
