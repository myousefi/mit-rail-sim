import csv
import random
import unittest
from itertools import combinations


class ArrivalRateCSVGeneratorTest(unittest.TestCase):
    def test_generate_random_arrival_rate_csv(self):
        station_names = [
            "O'Hare",
            "Rosemont",
            "Cumberland",
            "Harlem (O'Hare Branch)",
            "Jefferson Park",
            "Montrose",
            "Irving Park",
            "Addison",
            "Belmont",
            "Logan Square",
            "Western (O'Hare Branch)",
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

        output_file = "test/input_files/randomized_arrival_rate.csv"
        self.generate_random_arrival_rate_csv(station_names, output_file)

    def generate_random_arrival_rate_csv(self, station_names, output_file):
        hour_step = 0.25
        weekday = [True, False]

        with open(output_file, "w", newline="") as csvfile:
            fieldnames = [
                "hour",
                "weekday",
                "origin_stop",
                "destination_stop",
                "arrival_rate",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for day in weekday:
                for hour in [
                    round(x * hour_step, 2) for x in range(int(24 / hour_step))
                ]:
                    for origin_stop, destination_stop in combinations(station_names, 2):
                        writer.writerow(
                            {
                                "hour": hour,
                                "weekday": day,
                                "origin_stop": origin_stop,
                                "destination_stop": destination_stop,
                                "arrival_rate": round(random.uniform(0.1, 5), 8),
                            }
                        )


if __name__ == "__main__":
    unittest.main()
