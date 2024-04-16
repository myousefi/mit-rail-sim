import csv
from typing import List


class ArrivalRate:
    def __init__(self, filename, demand_factor: int = 1):
        self._rates = self._load_rates_from_csv(filename)
        self.demand_factor = demand_factor

    @staticmethod
    def is_southbound_trip(origin_stop, destination_stop):
        station_names = [
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

        origin_index = station_names.index(origin_stop)
        destination_index = station_names.index(destination_stop)

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
        lower_bound_hour = max(filter(lambda x: x < current_hour, self._rates.keys()))
        upper_bound_hour = min(
            filter(lambda x: x >= current_hour, self._rates.keys()),
            default=lower_bound_hour,
        )

        lower_bound_entry = self._rates[lower_bound_hour].get(current_weekday, {})
        upper_bound_entry = self._rates[upper_bound_hour].get(current_weekday, {})

        return lower_bound_hour, lower_bound_entry, upper_bound_hour, upper_bound_entry

    def get_smoothed_rate(self, current_hour, current_weekday, origin_stop, destination_stop):
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
