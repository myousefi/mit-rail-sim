import csv
from typing import List


class ArrivalRate:
    def __init__(self, filename, demand_factor: int = 1):
        self._rates = self._load_rates_from_csv(filename)
        self.demand_factor = demand_factor

        self.station_names = [
            "O-Hare",
            "Rosemont",
            "Cumberland",
            "Harlem (O-Hare Branch)",
            "Jefferson Park",
            "Montrose",
            "Irving Park",
            "Addison",
            "Belmont",
            "Logan Square",
            "California",
            "Western (O-Hare Branch)",
            "Damen",
            "Division",
            "Chicago",
            "Grand",
            "Clark/Lake",
            "Washington",
            "Monroe",
            "Jackson",
            "LaSalle",
            "Clinton",
            "UIC-Halsted",
            "Racine",
            "Illinois Medical District",
            "Western (Forest Park Branch)",
            "Kedzie-Homan",
            "Pulaski",
            "Cicero",
            "Austin",
            "Oak Park",
            "Harlem (Forest Park Branch)",
            "Forest Park",
        ]

    def sort_stations_by_direction(self, direction) -> List[str]:
        if direction == "Southbound":
            return self.station_names
        elif direction == "Northbound":
            return self.station_names[::-1]
        else:
            raise ValueError(f"Invalid direction: {direction}")

    def is_southbound_trip(self, origin_stop, destination_stop):
        origin_index = self.station_names.index(origin_stop)
        destination_index = self.station_names.index(destination_stop)

        return destination_index > origin_index

    def _load_rates_from_csv(self, filename):
        rates = {}
        try:
            with open(filename, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    origin_stop = row["Origin"]
                    destination_stop = row["Destination"]

                    # if not self.is_southbound_trip(origin_stop, destination_stop):
                    if True:
                        hour = float(row["time_bin"])
                        weekday = row["weekday"].lower() == "true"
                        arrival_rate = float(row["arrival_rate"])

                        rates.setdefault(hour, {}).setdefault(weekday, {}).setdefault(
                            origin_stop, {}
                        )[destination_stop] = arrival_rate
            return rates
        except Exception as exception:
            raise ValueError(f"Error loading CSV file: {exception}") from exception

    def _get_bound_entries(self, current_hour, current_weekday):
        try:
            lower_bound_hour = max(
                filter(lambda x: x <= current_hour, self._rates.keys())
            )
        except ValueError:
            raise ValueError(f"No matching hour found for {current_hour}")

        upper_bound_hour = min(
            filter(lambda x: x >= current_hour, self._rates.keys()),
            default=lower_bound_hour,
        )

        lower_bound_entry = self._rates[lower_bound_hour].get(current_weekday, {})
        upper_bound_entry = self._rates[upper_bound_hour].get(current_weekday, {})

        return lower_bound_hour, lower_bound_entry, upper_bound_hour, upper_bound_entry

    def get_smoothed_rate(
        self, current_hour, current_weekday, origin_stop, destination_stop
    ):
        (
            lower_bound_hour,
            lower_bound_entry,
            upper_bound_hour,
            upper_bound_entry,
        ) = self._get_bound_entries(current_hour, current_weekday)

        lower_origin_data = lower_bound_entry.get(origin_stop, {})
        upper_origin_data = upper_bound_entry.get(origin_stop, {})

        if destination_stop in lower_origin_data:
            if destination_stop in upper_origin_data:
                lower_rate = lower_origin_data[destination_stop]
                upper_rate = upper_origin_data[destination_stop]
                rate_diff = upper_rate - lower_rate
                hour_diff = upper_bound_hour - lower_bound_hour

                if hour_diff == 0:
                    smoothed_rate = lower_rate
                else:
                    smoothed_rate = lower_rate + (rate_diff / hour_diff) * (
                        current_hour - lower_bound_hour
                    )
            else:
                smoothed_rate = lower_origin_data[destination_stop]
        elif destination_stop in upper_origin_data:
            smoothed_rate = upper_origin_data[destination_stop]
        else:
            return 0  # No matching entry found

        return smoothed_rate * self.demand_factor

    def get_all_destination_stops_for_origin(self, origin_stop: str) -> List[str]:
        stops = set()

        for _, weekday_data in self._rates.items():
            for _, origin_data in weekday_data.items():
                if origin_stop in origin_data:
                    stops.update(origin_data[origin_stop].keys())

        return list(stops)

    def get_all_previous_stops_for_station_and_direction(
        self, station: str, direction: str
    ) -> List[str]:
        stations = self.sort_stations_by_direction(direction)

        station_index = stations.index(station)

        stations = stations[:station_index]

        return stations

    def get_all_destination_stops_for_origin_and_direction(
        self, origin_stop, direction
    ) -> List[str]:
        stations = self.sort_stations_by_direction(direction)

        origin_index = stations.index(origin_stop)

        stations = stations[origin_index + 1 :]

        return stations

    def get_lambda_for_station(
        self, current_hour: float, current_weekday: bool, station: str, direction: str
    ) -> float:
        lambda_i = 0
        all_destinations = self.get_all_destination_stops_for_origin_and_direction(
            origin_stop=station, direction=direction
        )

        for destination in all_destinations:
            lambda_i += self.get_smoothed_rate(
                current_hour,
                current_weekday,
                origin_stop=station,
                destination_stop=destination,
            )

        return lambda_i * self.demand_factor

    def get_p_for_station(
        self, current_hour: float, current_weekday: bool, station: str, direction: str
    ) -> float:
        previous_stops = self.get_all_previous_stops_for_station_and_direction(
            station, direction
        )
        next_stops = self.get_all_destination_stops_for_origin_and_direction(
            station, direction
        )

        total_rate = 0
        through_rate = 0

        for origin in previous_stops:
            for destination in [station] + next_stops:
                rate = self.get_smoothed_rate(
                    current_hour,
                    current_weekday,
                    origin_stop=origin,
                    destination_stop=destination,
                )
                total_rate += rate
                if destination != station:
                    through_rate += rate

        return through_rate / total_rate if total_rate > 0 else 0

    def get_a_i(
        self,
        current_hour: float,
        current_weekday: bool,
        start_station: str,
        critical_station: str,
        direction: str,
    ) -> float:
        stations = self.sort_stations_by_direction(direction)
        start_index = stations.index(start_station)
        critical_index = stations.index(critical_station)

        a_i = 1.0
        for k in stations[start_index + 1 : critical_index + 1]:
            p_k = self.get_p_for_station(current_hour, current_weekday, k, direction)
            a_i *= p_k

        return a_i

    def get_lambda_bar(
        self,
        current_hour: float,
        current_weekday: bool,
        start_station: str,
        critical_station: str,
        direction: str,
    ) -> float:
        stations = self.sort_stations_by_direction(direction)
        start_index = stations.index(start_station)
        critical_index = stations.index(critical_station)

        stations = stations[start_index:critical_index]

        lambda_bar = 0.0
        for i, station in enumerate(stations):
            a_i = self.get_a_i(
                current_hour, current_weekday, station, critical_station, direction
            )
            lambda_i = self.get_lambda_for_station(
                current_hour, current_weekday, station, direction
            )
            lambda_bar += a_i * lambda_i

        # Add λ for the critical station
        lambda_bar += self.get_lambda_for_station(
            current_hour, current_weekday, critical_station, direction
        )

        return lambda_bar
