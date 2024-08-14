from __future__ import annotations

import random
from typing import TYPE_CHECKING, List, Optional, Tuple

from mit_rail_sim.simulation_engine.infrastructure.stored_passenger_queue import (
    SortedPassengerQueue,
)
from mit_rail_sim.simulation_engine.passenger import Passenger, PassengerGenerator

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.passenger import ArrivalRate
    from mit_rail_sim.simulation_engine.simulation.simulation import Simulation
    from mit_rail_sim.simulation_engine.train import Train
    from mit_rail_sim.simulation_engine.utils import StationLogger


class Station:
    station_logger: Optional[StationLogger] = None
    simulation: Simulation

    def __init__(
        self,
        station_name: str,
        location_relative_to_block: float,
        direction: str,
        arrival_rates: ArrivalRate,
    ):
        self.name = station_name
        self.location_relative_to_block = location_relative_to_block
        self.direction = direction

        self._last_train_visit_time: Optional[float] = None
        self.passenger_generator = PassengerGenerator(arrival_rates)
        self.sorted_passenger_queue = SortedPassengerQueue()

    @property
    def last_train_visit_time(self) -> float:
        if self._last_train_visit_time is None:
            return self.simulation.current_time - random.uniform(340, 2 * 340)
        return self._last_train_visit_time

    @last_train_visit_time.setter
    def last_train_visit_time(self, value: Optional[float]) -> None:
        self._last_train_visit_time = value

    def get_dwell_time(self, door_metrics: List[Tuple(int, int, int)]) -> float:
        return max(
            douglas_model(
                alighting_passengers_per_door=alighting,
                boarding_passengers_per_door=boarding,
                standing_through_passengers_per_door=through,
            )
            for (alighting, boarding, through) in door_metrics
        )

    def generate_and_add_passengers(
        self,
        train: Train,
        holding_time: float = 0,
    ) -> None:
        current_time = self.simulation.current_time
        current_hour = self.simulation.get_current_hour()
        current_weekday = self.simulation.is_weekday()

        delta_t = current_time - self.last_train_visit_time + holding_time
        origin_stop_name = self.name

        destination_stops = train.get_all_stops_ahead()

        # self.passenger_generator.arrival_rate.get_all_destination_stops_for_origin(origin_stop)

        for destination_stop in destination_stops:
            destination_stop_name = destination_stop.name
            passenger_arrival_times = self.passenger_generator.generate_passengers(
                current_hour,
                current_weekday,
                origin_stop_name,
                destination_stop_name,
                delta_t,
            )

            for arrival_time in (
                passenger_arrival_times
            ):  # CHANGED: Iterating over passenger_arrival_times
                # Generate Passenger objects with appropriate attributes
                passenger = Passenger(
                    # self.last_train_visit_time + arrival_time,
                    current_time
                    - arrival_time,  # CHANGED: Using arrival_time as the first argument
                    origin_stop_name,
                    self.direction,
                    destination_stop_name,
                )  # CHANGED: Using arrival_time as the first argument
                self.sorted_passenger_queue.add_passenger(passenger)

    def board_passengers_onto_train(
        self, train_capacity: int, served_destinations: List[str]
    ) -> List[Passenger]:
        return self.sorted_passenger_queue.dequeue_passengers_and_update_remaining(
            train_capacity, served_destinations
        )

    def board_passengers_based_on_destiations_and_probability(
        self,
        train_capacity: int,
        served_destinations: List[str],
        probability_of_boarding_any_train: float,
    ) -> List[Passenger]:
        return self.sorted_passenger_queue.dequeue_passengers_and_update_remaining_based_on_destinations_and_probability(
            train_capacity, served_destinations, probability_of_boarding_any_train
        )


def linear_dwell_time_model(
    boarding, alighting, c0=13.5, alpha=8 * 4 / 100, epsilon_std=3
):
    number_of_passengers = boarding + alighting
    epsilon = random.gauss(0, epsilon_std)
    dwell_time = c0 + alpha * number_of_passengers + epsilon
    return max(dwell_time, 5)


def puong_dwell_time_model(
    boarding,
    alighting,
    number_of_passengers_on_train,
    c_0=12.22,
    alpha=2.27,
    beta=1.82,
    gamma=0.00064,
):
    boarding_per_door, alighting_per_door = boarding * 0.12, alighting * 0.12
    through_standees_per_door = max(number_of_passengers_on_train * 0.12 - 40, 0)
    dwell_time = (
        c_0
        + min(beta + gamma * (through_standees_per_door**3), 3.5) * boarding_per_door
        + alpha * alighting_per_door
    )
    return dwell_time


def wirasinghe_szplett_model(
    boarding_to_alighting_ratio,
    average_alighting_per_door,
    average_boarding_per_door,
    base_time_alight=2,
    time_per_alighting_passenger=1.0,
    time_per_boarding_passenger_alight=2.4,
    base_time_mixed=2,
    time_per_alighting_passenger_mixed=0.4,
    time_per_boarding_passenger_mixed=1.4,
    base_time_board=2,
    time_per_alighting_passenger_board=1.4,
    time_per_boarding_passenger_board=1.4,
):
    if boarding_to_alighting_ratio <= 0.32:
        base_time, alight_time, board_time = (
            base_time_alight,
            time_per_alighting_passenger,
            time_per_boarding_passenger_alight,
        )
    elif 0.33 <= boarding_to_alighting_ratio <= 0.66:
        base_time, alight_time, board_time = (
            base_time_mixed,
            time_per_alighting_passenger_mixed,
            time_per_boarding_passenger_mixed,
        )
    else:
        base_time, alight_time, board_time = (
            base_time_board,
            time_per_alighting_passenger_board,
            time_per_boarding_passenger_board,
        )

    dwell_time = (
        base_time
        + alight_time * average_alighting_per_door
        + board_time * average_boarding_per_door
    )
    return dwell_time


def weston_model(
    peak_door_factor,
    through_passengers,
    seats,
    doors,
    alighting_passengers,
    boarding_passengers,
    constant_time=15,
    power_value=0.7,
    base_multiplier=1.4,
    mixed_multiplier=0.027,
):
    dwell_time = constant_time + base_multiplier * (
        1 + peak_door_factor / 35 * (through_passengers - seats) / doors
    ) * (
        (boarding_passengers / doors) ** power_value
        + (alighting_passengers / doors) ** power_value
        + mixed_multiplier
        * (boarding_passengers / doors)
        * (alighting_passengers / doors)
    )
    return dwell_time


def lam_et_al_model(
    alighting_passengers,
    boarding_passengers,
    base_time=10.5,
    alighting_coefficient=0.021,
    boarding_coefficient=0.016,
):
    dwell_time = (
        base_time
        + alighting_coefficient * alighting_passengers
        + boarding_coefficient * boarding_passengers
    )
    return dwell_time


def douglas_model(
    alighting_passengers_per_door,
    boarding_passengers_per_door,
    standing_through_passengers_per_door,
    base_time=15,
    alighting_power=0.7,
    boarding_power=0.7,
    alighting_coefficient=1.9,
    boarding_coefficient=1.4,
    combined_coefficient=0.007,
    interaction_coefficient=0.005,
):
    dwell_time = (
        base_time
        + alighting_coefficient * alighting_passengers_per_door**alighting_power
        + boarding_coefficient * boarding_passengers_per_door**boarding_power
        + combined_coefficient
        * (alighting_passengers_per_door + boarding_passengers_per_door)
        * standing_through_passengers_per_door
        + interaction_coefficient
        * alighting_passengers_per_door
        * boarding_passengers_per_door
    )
    return dwell_time
