import pandas as pd


def read_and_combine_data(filepaths):
    cols_to_read = [
        "transit_account_id",
        "transaction_dtm",
        "operator_nm",
        "boarding_stop",
        "inferred_alighting_gtfs_stop",
    ]
    data_list = [pd.read_csv(filepath, usecols=cols_to_read) for filepath in filepaths]
    data = pd.concat(data_list, ignore_index=True)
    data = data[data["operator_nm"] == "1-CTA Rail"]
    return data


def preprocess_data(data):
    data = data[data["inferred_alighting_gtfs_stop"].notnull()]
    data = data[data["inferred_alighting_gtfs_stop"] != "None"]
    data["transaction_dtm"] = pd.to_datetime(data["transaction_dtm"])
    data["hour"] = data["transaction_dtm"].dt.hour + data["transaction_dtm"].dt.minute / 60
    bins = [i / 4 - 0.0001 for i in range(0, 97)]  # Create bins for every 15-minute interval
    labels = [i / 4 for i in range(0, 96)]  # Create labels for the bins
    data["hour"] = pd.cut(data["hour"], bins=bins, labels=labels).astype(float)
    data["weekday"] = data["transaction_dtm"].dt.weekday < 5
    return data


def calculate_arrival_rates(data, stations):
    data["inferred_alighting_gtfs_stop"] = data["inferred_alighting_gtfs_stop"].astype(int)
    data["boarding_stop"] = data["boarding_stop"].astype(int)

    merged_data_destination = (
        data.merge(
            stations[["STOP_ID", "STATION_DESCRIPTIVE_NAME"]],
            left_on="inferred_alighting_gtfs_stop",
            right_on="STOP_ID",
            how="inner",
        )
        .rename(columns={"STATION_DESCRIPTIVE_NAME": "destination_stop"})
        .drop("STOP_ID", axis=1)
    )

    merged_data_origin = (
        merged_data_destination.merge(
            stations[["MAP_ID", "STATION_DESCRIPTIVE_NAME"]],
            left_on="boarding_stop",
            right_on="MAP_ID",
            how="inner",
        )
        .rename(columns={"STATION_DESCRIPTIVE_NAME": "origin_stop"})
        .drop("MAP_ID", axis=1)
    )

    grouped_data = (
        merged_data_origin.groupby(["hour", "weekday", "origin_stop", "destination_stop"])
        .size()
        .reset_index(name="count")
    )

    total_weekdays = len(
        pd.date_range(
            start=data["transaction_dtm"].min(),
            end=data["transaction_dtm"].max(),
            freq="B",  # Business days (weekdays)
        )
    )
    total_weekends = (
        len(
            pd.date_range(
                start=data["transaction_dtm"].min(),
                end=data["transaction_dtm"].max(),
                freq="W",  # Weekly frequency (Sundays by default)
            )
        )
        * 2
    )  # Since there are two weekend days (Saturday and Sunday)

    grouped_data["arrival_rate"] = grouped_data.apply(
        lambda x: (x["count"] / (total_weekdays if x["weekday"] else total_weekends)) * 4,
        axis=1,
    )

    grouped_data = grouped_data[
        ["hour", "weekday", "origin_stop", "destination_stop", "arrival_rate"]
    ]
    return grouped_data


def main():
    filepaths = [
        "./ODX_Simple_2022-03-01_2022-03-15.csv",
        "./ODX_Simple_2022-03-15_2022-03-31.csv",
        # "./temp.csv"
    ]
    stations_filepath = "./blue_line_stations_qt.csv"
    output_filepath = "./arrival_rates.csv"

    data = read_and_combine_data(filepaths)
    data = preprocess_data(data)
    stations = pd.read_csv(stations_filepath)
    arrival_rates = calculate_arrival_rates(data, stations)
    arrival_rates.to_csv(output_filepath, index=False)

    print("Arrival rates have been calculated and saved to 'arrival_rates.csv'")


if __name__ == "__main__":
    main()
