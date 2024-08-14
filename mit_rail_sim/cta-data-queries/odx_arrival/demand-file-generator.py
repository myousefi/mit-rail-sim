from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from sqlalchemy import text

from mit_rail_sim.utils.db_con import engine
from mit_rail_sim.utils.root_path import project_root


start_date = "2023-11-13"
end_date = "2024-02-07"

# Load stations data
station_df = pd.read_csv(Path(__file__).parent / "data" / "blue_line_stations.csv")

# Generate query text
query_text = text(
    """
    SELECT transaction_dtm, boarding_stop, route_sequence, direction_sequence, boarding_platform_sequence, alighting_platform_sequence
    FROM planning_models_spectrum.odx_journeys
    WHERE
        boarding_stop IN :boarding_stops_list AND
        transaction_dtm BETWEEN :start_date AND :end_date
    """
)
# Execute the query and fetch the results
result = engine.execute(
    query_text,
    boarding_stops_list=tuple(station_df["MAP_ID"].unique().tolist()),
    start_date=start_date,
    end_date=end_date,
).fetchall()

# Convert the result to a DataFrame
result_df = pd.DataFrame(
    result,
    columns=[
        "transaction_dtm",
        "boarding_stop",
        "route_sequence",
        "direction_sequence",
        "boarding_platform_sequence",
        "alighting_platform_sequence",
    ],
)


for col in [
    "route_sequence",
    "direction_sequence",
    "boarding_platform_sequence",
    "alighting_platform_sequence",
]:
    result_df["first_" + col.replace("_sequence", "")] = (
        result_df[col].str.split("|").str[1]
    )
    result_df.drop(columns=col, inplace=True)
result_df["Origin"] = (
    result_df["boarding_stop"]
    .astype(str)
    .map(dict(zip(station_df["MAP_ID"].astype(str), station_df["STATION_NAME_IN_SIM"])))
)

# Convert transaction_dtm to datetime, extract time component, and determine the day type
result_df["transaction_dtm"] = pd.to_datetime(result_df["transaction_dtm"])

result_df["time"] = result_df["transaction_dtm"].dt.hour
result_df["day_type"] = result_df["transaction_dtm"].dt.dayofweek.apply(
    lambda x: "Weekday" if x < 5 else "Saturday" if x == 5 else "Sunday"
)

result_df.sort_values(["transaction_dtm"], inplace=True)

# Define columns to fill
fill_columns = [
    "first_route",
    "first_direction",
    "first_boarding_platform",
    "first_alighting_platform",
]


# Function to impute missing data within each group
def impute_within_group(group):
    non_nan_rows = group.dropna(subset=fill_columns)
    if non_nan_rows.empty:
        # If there are no rows to impute from, return the group as is
        return group

    # For rows with NaN in the current column, fill them with values from a randomly chosen row
    nan_rows = group[fill_columns].isna().any(axis=1)
    group.loc[nan_rows, fill_columns] = (
        non_nan_rows[fill_columns].sample(n=nan_rows.sum(), replace=True).values
    )

    return group


# Apply the imputation function to each group
result_df = (
    result_df.groupby(["boarding_stop", "time", "day_type"])
    .apply(impute_within_group)
    .reset_index(drop=True)
)


result_df["Destination"] = result_df["first_alighting_platform"].map(
    dict(zip(station_df["STOP_ID"].astype(str), station_df["STATION_NAME_IN_SIM"]))
)

# Extract hour and determine if the day is a weekday
result_df["hour"] = (
    result_df["transaction_dtm"].dt.hour + result_df["transaction_dtm"].dt.minute / 60
)
result_df["hour"] = result_df["hour"].round(2)  # Round to 2 decimal places
result_df["weekday"] = (result_df["transaction_dtm"].dt.weekday < 5) & (
    ~result_df["transaction_dtm"].dt.date.isin(USFederalHolidayCalendar().holidays())
)  # True for weekdays (Mon-Fri)

# Create bins for 15-minute intervals
time_bins = [i / 4 for i in range(24 * 4)]
result_df["time_bin"] = pd.cut(
    result_df["hour"], bins=time_bins, labels=time_bins[:-1], right=False
)


def rate_group(group):
    num_days = len(group["transaction_dtm"].dt.date.unique())
    num_boarding = len(group)
    return num_boarding / num_days * 60 / 15


rate_df = result_df.groupby(["time_bin", "weekday", "Origin", "Destination"]).apply(
    rate_group, include_groups=True
)

rate_df = rate_df.reset_index(name="arrival_rate")  # Reset the index to create new

output_file_path = (
    project_root
    / "inputs"
    / "demand"
    / f"odx_imputed_demand_{start_date}_{end_date}.csv"
)

rate_df.to_csv(output_file_path, index=False)
print(f"Saved imputed demand data to {output_file_path}")
