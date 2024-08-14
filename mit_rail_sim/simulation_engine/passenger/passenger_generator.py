import math
import random

from mit_rail_sim.simulation_engine.passenger.arrival_rate import ArrivalRate


class PassengerGenerator:
    def __init__(self, arrival_rate: ArrivalRate):
        self.arrival_rate = arrival_rate

    def generate_passengers(
        self,
        current_hour: float,
        current_weekday: bool,
        boarding_stop: str,
        alighting_stop: str,
        delta_t_in_seconds: float,
    ) -> list:
        delta_t = delta_t_in_seconds / 3600
        rate_alpha = self.arrival_rate.get_smoothed_rate(
            current_hour, current_weekday, boarding_stop, alighting_stop
        )

        if True:
            # if rate_alpha * delta_t < 15:
            return self._generate_poisson_passengers(
                delta_t, rate_alpha, delta_t_in_seconds
            )
        else:
            return self._generate_normal_distribution_passengers(
                delta_t, rate_alpha, delta_t_in_seconds
            )

    def _generate_poisson_passengers(
        self, delta_t: float, rate_alpha: float, delta_t_in_seconds: float
    ) -> list:
        random_uniform = random.uniform(0, 1)
        k = 0
        probability = math.exp(-rate_alpha * delta_t)
        cumulative_probability = probability

        while cumulative_probability < random_uniform:
            k += 1
            probability *= rate_alpha * delta_t / k
            cumulative_probability += probability

        passenger_arrivals = sorted(
            [random.uniform(0, delta_t_in_seconds) for _ in range(k)]
        )
        return passenger_arrivals

    def _generate_normal_distribution_passengers(
        self, delta_t: float, rate_alpha: float, delta_t_in_seconds: float
    ) -> list:
        mean = rate_alpha * delta_t
        std_dev = math.sqrt(rate_alpha * delta_t)
        num_passengers = round(random.normalvariate(mean, std_dev))

        passenger_arrivals = sorted(
            [
                random.normalvariate(mean * 3600, std_dev * 3600) % delta_t_in_seconds
                for _ in range(num_passengers)
            ]
        )
        return passenger_arrivals
