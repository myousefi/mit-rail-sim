import os

import pandas as pd
import yaml

from mit_rail_sim.utils import project_root


class TravelTimeCalculator:
    def __init__(self):
        self.output = []

    def calculate_sim_travel_times(self, sim_data, origin_station, destination_station):
        sim_data_filtered = sim_data[
            sim_data["station_name"].isin([origin_station, destination_station])
        ]

        sim_travel_times = (
            sim_data_filtered.groupby(["replication_id", "train_id"])
            .apply(
                lambda x: (
                    x[x["station_name"] == destination_station]["time_in_seconds"].min()
                    - x[x["station_name"] == origin_station]["time_in_seconds"].max()
                )
                / 60
            )
            .dropna()
        )

        return sim_travel_times.mean(), sim_travel_times.std()

    def calculate_headways(self, sim_data, station_name):
        sim_data_filtered = sim_data[sim_data["station_name"] == station_name]
        mean_headway = sim_data_filtered["headway"].mean()
        std_headway = sim_data_filtered["headway"].std()

        return mean_headway, std_headway / mean_headway if mean_headway != 0 else 0

    def process_experiment(self, experiment_dir):
        # Extract parameters from the config file
        with open(os.path.join(experiment_dir, ".hydra", "config.yaml"), "r") as config_file:
            parameters = yaml.safe_load(config_file)

        # Process the station_test.csv file
        df = pd.read_csv(os.path.join(experiment_dir, "station_test.csv"))

        origin_station = "Forest Park"
        destination_station = "O-Hare"
        avg_travel_time, std_travel_time = self.calculate_sim_travel_times(
            df, origin_station, destination_station
        )
        cv_travel_time = std_travel_time / avg_travel_time if avg_travel_time != 0 else 0

        stations = [
            "Forest Park",
            "Cicero",
            "UIC-Halsted",
            "Clark/Lake",
            "Logan Square",
            "Jefferson Park",
            "O-Hare",
        ]
        headway_stats = {}
        for station in stations:
            avg_headway, cv_headway = self.calculate_headways(df, station)
            headway_stats[
                f"avg_headway_{station.replace('-', '_').replace(' ', '_')}"
            ] = avg_headway
            headway_stats[f"cv_headway_{station.replace('-', '_').replace(' ', '_')}"] = cv_headway

        result = {
            **parameters,
            "avg_travel_time": avg_travel_time,
            "cv_travel_time": cv_travel_time,
            **headway_stats,
        }
        self.output.append(result)

    def save_output(self, output_filename):
        df = pd.DataFrame(self.output)
        df.to_csv(output_filename, index=False)


if __name__ == "__main__":
    calculator = TravelTimeCalculator()

    experiments_root = project_root / "multirun" / "2023-08-15" / "11-30-08"
    experiment_directories = [
        os.path.join(experiments_root, d)
        for d in os.listdir(experiments_root)
        if os.path.isdir(os.path.join(experiments_root, d))
    ]
    for experiment_dir in experiment_directories:
        calculator.process_experiment(experiment_dir)

    calculator.save_output("output_slow_zones.csv")
