from functools import total_ordering
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from transit_lab_simmetro.simulation_engine.utils import PassengerLogger


@total_ordering
class Passenger:
    _last_id = 0
    passenger_logger: Optional["PassengerLogger"] = None

    def __init__(
        self,
        arrival_time: float,
        origin: str,
        direction: str,
        destination: str,
    ):
        self.passenger_id = self._get_next_id()
        self.arrival_time = arrival_time

        self._boarding_time: Optional[float] = None
        self._alighting_time: Optional[float] = None

        self.origin = origin
        self.direction = direction
        self.destination = destination
        self.number_of_times_denied_boarding = 0

        self.should_log: bool = True

        self.car_assigned: Optional[int] = None
        self.door_assigned: Optional[int] = None

        self._transfer_alighting_time: Optional[float] = None
        self._waiting_time: Optional[float] = None

    def set_not_loggable(self):
        self.should_log = False
        return self

    @classmethod
    def _get_next_id(cls):
        cls._last_id += 1
        return cls._last_id

    def denied_boarding(self):
        self.number_of_times_denied_boarding += 1

    @property
    def boarding_time(self):
        return self._boarding_time

    @boarding_time.setter
    def boarding_time(self, value: float):
        if self._boarding_time is None:
            self._boarding_time = value
        else:
            self._waiting_time = value - self._transfer_alighting_time

    @property
    def waiting_time(self):
        if self._waiting_time is None:
            return self.boarding_time - self.arrival_time
        else:
            return self._waiting_time + (self.boarding_time - self.arrival_time)

    @property
    def travel_time(self):
        if self._waiting_time is None:
            return self.alighting_time - self.boarding_time
        else:
            return self.alighting_time - self.boarding_time - self._waiting_time

    @property
    def journey_time(self):
        return self.alighting_time - self.arrival_time

    @property
    def alighting_time(self):
        return self._alighting_time

    @alighting_time.setter
    def alighting_time(self, value: float):
        self._alighting_time = value
        if (
            self.passenger_logger and self.should_log
        ):  # TODO Update this line to use the class attribute
            self.passenger_logger.log_passenger(self)

    def __lt__(self, other: "Passenger") -> bool:
        return (
            self.arrival_time < other.arrival_time
            if isinstance(other, Passenger)
            else NotImplemented
        )
