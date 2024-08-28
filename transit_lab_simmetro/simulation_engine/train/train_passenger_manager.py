from __future__ import annotations

import random
from collections import defaultdict
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    pass


class TrainPassengerManager:
    def __init__(
        self,
        train_capacity: int,
        num_cars: int = 8,
        num_doors_per_car: int = 2,
        car_capacity: int = None,
        num_seats_per_door: int = 20,
    ):
        self.train_capacity = train_capacity
        self.num_cars = num_cars
        self.num_doors_per_car = num_doors_per_car
        self.car_capacity = car_capacity or train_capacity // num_cars
        self.passengers = defaultdict(list)
        self.cars = [[[] for _ in range(num_doors_per_car)] for _ in range(num_cars)]
        self.num_seats_per_door = num_seats_per_door

    def remaining_capacity(self) -> int:
        return self.train_capacity - sum(
            len(passengers) for passengers in self.passengers.values()
        )

    def alight_passengers(self, current_station, current_time):
        alighting_passengers = self.passengers[current_station]
        alight_counts = [
            [0 for _ in range(self.num_doors_per_car)] for _ in range(self.num_cars)
        ]

        for passenger in alighting_passengers:
            car_idx = passenger.car_assigned
            door_idx = passenger.door_assigned
            alight_counts[car_idx][door_idx] += 1
            self.cars[car_idx][door_idx].remove(passenger)
            passenger.alighting_time = current_time

        del self.passengers[current_station]
        return alight_counts

    def alight_all_passengers(self, current_station, current_time):
        alight_counts = [
            [0 for _ in range(self.num_doors_per_car)] for _ in range(self.num_cars)
        ]

        for stations in self.passengers.keys():
            alighting_passengers = self.passengers[stations]
            for passenger in alighting_passengers:
                car_idx = passenger.car_assigned
                door_idx = passenger.door_assigned
                alight_counts[car_idx][door_idx] += 1
                self.cars[car_idx][door_idx].remove(passenger)

                if stations == current_station.name:
                    passenger.alighting_time = current_time
                else:
                    current_station.sorted_passenger_queue.add_passenger(passenger)
                    passenger._transfer_alighting_time = current_time

        self.passengers = defaultdict(list)

        return alight_counts

    def board_passengers(
        self,
        passengers,
        current_time,
        car_assignment_weights: List[float] = [1, 3, 1, 1, 1, 1, 3, 1],
    ):
        boarding_counts = [
            [0 for _ in range(self.num_doors_per_car)] for _ in range(self.num_cars)
        ]

        for passenger in passengers:
            if self.remaining_capacity() <= 0:
                raise ValueError("Train is full!")

            while True:
                # car_idx = random.randint(0, self.num_cars - 1)
                car_idx = random.choices(
                    population=range(self.num_cars), weights=car_assignment_weights, k=1
                )[0]
                door_idx = random.randint(0, self.num_doors_per_car - 1)
                if len(self.cars[car_idx]) < self.car_capacity:
                    self.cars[car_idx][door_idx].append(passenger)
                    boarding_counts[car_idx][door_idx] += 1
                    passenger.boarding_time = current_time
                    passenger.car_assigned = car_idx
                    passenger.door_assigned = door_idx
                    self.passengers[passenger.destination].append(passenger)
                    break
                else:
                    car_assignment_weights[car_idx] = 0

        return boarding_counts

    def get_door_metrics(self, alight_counts, boarding_counts):
        metrics = []
        for car_idx in range(self.num_cars):
            for door_idx in range(self.num_doors_per_car):
                alightings = alight_counts[car_idx][door_idx]
                boardings = boarding_counts[car_idx][door_idx]
                through_standees = max(
                    len(self.cars[car_idx][door_idx])
                    - boardings
                    - self.num_seats_per_door,
                    0,
                )
                metrics.append((alightings, boardings, through_standees))
        return metrics

    @property
    def total_passengers(self):
        return sum(len(passengers) for passengers in self.passengers.values())
