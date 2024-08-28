from __future__ import annotations

import random
from bisect import insort
from typing import List

from transit_lab_simmetro.simulation_engine.passenger import Passenger


class SortedPassengerQueue:
    def __init__(self):
        self.sorted_passengers = []

    def __len__(self):
        return len(self.sorted_passengers)

    def size(self):
        return len(self.sorted_passengers)

    def add_passenger(self, passenger: Passenger):
        insort(self.sorted_passengers, passenger)

    def dequeue_passengers_and_update_remaining(
        self, train_capacity: int, served_destinations: List[str]
    ) -> List[Passenger]:
        passengers_to_board = []
        passengers_not_served = []
        denied_boardings = 0

        while self.sorted_passengers and train_capacity > 0:
            passenger = self.sorted_passengers.pop(0)
            if passenger.destination in served_destinations:
                passengers_to_board.append(passenger)
                train_capacity -= 1
            else:
                passengers_not_served.append(passenger)

        for passenger in self.sorted_passengers:
            if passenger.destination in served_destinations:
                passenger.denied_boarding()
                denied_boardings += 1

        for passenger in passengers_not_served:
            insort(self.sorted_passengers, passenger)

        return passengers_to_board, denied_boardings

    def dequeue_passengers_and_update_remaining_based_on_destinations_and_probability(
        self,
        train_capacity: int,
        served_destinations: List[str],
        probability_of_boarding_any_train: float,
    ) -> List[Passenger]:
        passengers_to_board = []
        passengers_not_served = []
        denied_boardings = 0

        while self.sorted_passengers and train_capacity > 0:
            passenger = self.sorted_passengers.pop(0)
            if passenger.destination in served_destinations:
                passengers_to_board.append(passenger)
                train_capacity -= 1
            elif random.random() < probability_of_boarding_any_train:
                passengers_to_board.append(passenger)
                train_capacity -= 1
            else:
                passengers_not_served.append(passenger)

        for passenger in self.sorted_passengers:
            if passenger.destination in served_destinations:
                passenger.denied_boarding()
                denied_boardings += 1

        for passenger in passengers_not_served:
            insort(self.sorted_passengers, passenger)

        return passengers_to_board, denied_boardings
