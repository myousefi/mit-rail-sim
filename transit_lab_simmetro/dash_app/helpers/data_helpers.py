import json

import pandas as pd
import plotly.io as pio


def get_color(index: int) -> str:
    """Get a color from the color palette based on the index."""
    color_palette = pio.templates["sophisticated"].layout.colorway
    return color_palette[index % len(color_palette)]


def calculate_absolute_distance(rail_data_json):
    # with open(filename, 'r') as f:
    #     data = json.load(f)

    # station_dict = {}
    # for direction in ["Northbound", "Southbound"]:
    distance = 0
    stations = {}
    for segment in rail_data_json:
        if "STATION" in segment:
            stations[segment["STATION"]["STATION_NAME"]] = distance + abs(
                int(segment["STATION"]["END_OF_PLATFORM_MILEPOST"])
                - int(segment["STARTSTN"])
            )
        distance += int(segment["DISTANCE"])

    # station_dict[direction] = stations
    return stations


def calculate_travel_times(station_data: pd.DataFrame) -> pd.DataFrame:
    travel_times = []

    # Group data by replication_id, station_name, and train_id, and sort by time_in_seconds
    station_data_sorted = station_data.sort_values("time_in_seconds")
    grouped_data = station_data_sorted.groupby(
        ["replication_id", "station_name", "train_id"]
    )

    # Create a dictionary for fast lookup of data frames for each group
    group_dict = {g: df for g, df in grouped_data}

    # List of unique replication_ids, station_names and train_ids
    replication_ids = station_data["replication_id"].unique()
    station_names = station_data["station_name"].unique()
    train_ids = station_data["train_id"].unique()

    for replication_id in replication_ids:
        for origin_name in station_names:
            for destination_name in station_names:
                if (
                    origin_name != destination_name
                ):  # Exclude cases where the origin and destination are the same
                    for train_id in train_ids:
                        if ((replication_id, origin_name, train_id) in group_dict) and (
                            (replication_id, destination_name, train_id) in group_dict
                        ):
                            origin_data = group_dict[
                                (replication_id, origin_name, train_id)
                            ]
                            dest_data = group_dict[
                                (replication_id, destination_name, train_id)
                            ]

                            if not origin_data.empty and not dest_data.empty:
                                # Get the first time_in_seconds value for the origin and last for the destination
                                origin_time = origin_data["time_in_seconds"].iloc[0]
                                destination_time = dest_data["time_in_seconds"].iloc[-1]

                                travel_time = destination_time - origin_time
                                if travel_time > 0:
                                    travel_times.append(
                                        {
                                            "replication_id": replication_id,
                                            "origin": origin_name,
                                            "destination": destination_name,
                                            "train_id": train_id,
                                            "travel_time": travel_time,
                                        }
                                    )

    return pd.DataFrame(travel_times)


def load_data(results_dir: str):
    train_log_file_path = f"{results_dir}/train_test.csv"
    train_data = pd.read_csv(train_log_file_path)

    station_log_file_path = f"{results_dir}/station_test.csv"
    station_data = pd.read_csv(station_log_file_path)
    station_data["time_in_seconds"] = station_data["time_in_seconds"].astype(int)

    infrastructure_file_path = "inputs/infra.json"
    with open(infrastructure_file_path, "r") as f:
        rail_data_json = json.load(f)
        rail_data_json = rail_data_json["Northbound"]

    stations_dict = calculate_absolute_distance(rail_data_json)

    travel_times_data = calculate_travel_times(station_data)

    passenger_data = pd.read_csv(f"{results_dir}/passenger_test.csv")

    return train_data, station_data, passenger_data, stations_dict, travel_times_data
