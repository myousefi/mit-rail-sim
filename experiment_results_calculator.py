import os

import pandas as pd


class TravelTimeCalculator:
    def __init__(self, parameters):
        self.parameters = parameters
        self.output = []

    def calculate_sim_travel_times(self, sim_data, origin_station, destination_station):
        # Filter simulation data for origin and destination
        sim_data_filtered = sim_data[
            sim_data["station_name"].isin([origin_station, destination_station])
        ]

        # Calculate travel times for simulation data
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

        # Return mean and standard deviation of travel times
        return sim_travel_times.mean(), sim_travel_times.std()

    def calculate_headways(self, sim_data, station_name):
        # Filter simulation data for specific station
        sim_data_filtered = sim_data[sim_data["station_name"] == station_name]

        # Calculate mean of headways
        mean_headway = sim_data_filtered["headway"].mean()
        # Calculate standard deviation of headways
        std_headway = sim_data_filtered["headway"].std()

        # Return mean and Coefficient of Variation of headways
        return mean_headway, std_headway / mean_headway if mean_headway != 0 else 0

    def process_csv(self, csv_file, parameters):
        # Read CSV file
        df = pd.read_csv(csv_file)

        # Specify your origin and destination stations
        origin_station = "Forest Park"
        destination_station = "O-Hare"

        # Calculate travel times
        avg_travel_time, std_travel_time = self.calculate_sim_travel_times(
            df, origin_station, destination_station
        )
        # Calculate Coefficient of Variation of travel times
        cv_travel_time = std_travel_time / avg_travel_time if avg_travel_time != 0 else 0

        # Specify stations for headway calculations
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
            # Calculate headways
            avg_headway, cv_headway = self.calculate_headways(df, station)
            headway_stats[
                f"avg_headway_{station.replace('-', '_').replace(' ', '_')}"
            ] = avg_headway
            headway_stats[f"cv_headway_{station.replace('-', '_').replace(' ', '_')}"] = cv_headway

        # Add the results to the output
        self.output.append(
            {
                **parameters,
                "avg_travel_time": avg_travel_time,
                "cv_travel_time": cv_travel_time,
                **headway_stats,
            }
        )

    def walk_directory(self, dir):
        for root, dirs, files in os.walk(dir):
            if "station_test.csv" in files:
                parameters = self.parse_parameters_from_path(root)
                self.process_csv(os.path.join(root, "station_test.csv"), parameters)

    def parse_parameters_from_path(self, path):
        # Split the path by "/" to get the individual directories
        directories = path.split("/")

        # Initialize an empty dictionary to store the parameters
        parameters_dict = {}

        # For each parameter, find the corresponding directory and extract the value
        for param in self.parameters:
            for directory in directories:
                if directory.startswith(param):
                    # Everything after the first occurrence of parameter name is the value
                    value = directory[len(param) + 1 :]
                    parameters_dict[param] = value
                    break  # Move on to the next parameter

        return parameters_dict

    def write_to_csv(self, output_file):
        df = pd.DataFrame(self.output)
        df.to_csv(output_file, index=False)


if __name__ == "__main__":
    # Define the parameters we are interested in
    parameters = ["signal_system", "slow_zones", "mean_headway", "cv_headway"]

    calculator = TravelTimeCalculator(parameters)
    calculator.walk_directory("./trb_experiments")
    calculator.write_to_csv("output.csv")
