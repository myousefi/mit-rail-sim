from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import Path
    from mit_rail_sim.simulation_engine.utils.logger_utils import SimulationLogger
    from mit_rail_sim.simulation_engine.infrastructure import (
        SignalControlCenter,
        MovingBlockControl,
    )

    from mit_rail_sim.simulation_engine.schedule import Schedule
    from mit_rail_sim.simulation_engine.schedule_refactored import BaseSchedule

from mit_rail_sim.simulation_engine.infrastructure import Station
from mit_rail_sim.simulation_engine.passenger import Passenger
from mit_rail_sim.simulation_engine.train import (
    DummyTrainDecorator,
    Train,
    TrainPassengerManager,
    TrainSpeedRegulator,
    TrainSpeedRegulatorCTA,
)


class Simulation:
    simulation_logger: Optional[SimulationLogger] = None

    def __init__(
        self,
        schedule: Schedule | BaseSchedule,
        path: Dict[str, Path],
        signal_control_center: MovingBlockControl | SignalControlCenter,
        train_speed_regulator: str,
        time_step: float = 0.5,
        start_hour: float = 5.0,
        is_weekday: bool = True,
        total_time: float = 14400,
    ):
        self.schedule = schedule
        self.paths = path
        self.signal_control_center = signal_control_center
        self.time_step = round(time_step, 2)
        self.current_time = start_hour * 3600
        self.replication_id: int = -1
        self._start_hour = start_hour
        self._is_weekday = is_weekday

        self.train_speed_regulator = (
            TrainSpeedRegulatorCTA
            if train_speed_regulator == "CTA"
            else TrainSpeedRegulator
        )

        self.trains: List[Train] = [
            DummyTrainDecorator(
                self._create_train(0, self.current_time, self.paths["Northbound"])
            ),
            DummyTrainDecorator(
                self._create_train(0, self.current_time, self.paths["Southbound"])
            ),
        ]

        self._total_time = total_time + self.current_time

    def is_weekday(self) -> bool:
        return self._is_weekday

    def get_current_hour(self) -> float:
        return self.current_time / 3600

    def run(self) -> None:
        while self.current_time <= self._total_time:
            self._dispatch_trains()
            self._update_trains()
            self.current_time += self.time_step
        return

    def _create_train(
        self,
        starting_block_index: int,
        dispatching_time: float,
        path: Path,
        runid: Optional[str] = None,
    ) -> Train:
        return Train(
            train_speed_regulator=self.train_speed_regulator(
                max_acceleration=4,
                normal_deceleration=1 * 2.17,
                emergency_deceleration=1 * 4.10,
            ),
            train_passenger_manager=TrainPassengerManager(train_capacity=960),
            path=path,
            starting_block_index=starting_block_index,
            dispatching_time=dispatching_time,
            # runid=runid,
        )

    def _dispatch_trains(self) -> None:
        if (
            self.schedule.dispatch_info
            and self.current_time >= self.schedule.dispatch_info[0][0]
        ):
            dispatching_time, starting_block_index, path, run_id = (
                self.schedule.dispatch_info.pop(0)
            )
            new_train = self._create_train(
                starting_block_index, dispatching_time, self.paths[path], run_id
            )
            self.trains.append(new_train)

    def _update_trains(self) -> None:
        for train in self.trains:
            train.update()

    def remove_train(self, train: Train) -> None:
        self.trains.remove(train)


class SimulationContext:
    def __init__(self, simulation: Simulation):
        self.simulation = simulation

    def __enter__(self):
        Train.simulation = self.simulation
        DummyTrainDecorator.simulation = self.simulation
        Passenger.simulation = self.simulation
        Station.simulation = self.simulation

        Train._last_id = 0
        Passenger._last_id = 0

    def __exit__(self, exc_type, exc_value, traceback):
        Train.simulation = None
        Passenger.simulation = None
        Station.simulation = None
