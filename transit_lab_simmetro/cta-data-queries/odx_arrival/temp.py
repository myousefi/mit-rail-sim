from distutils.sysconfig import project_base

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar


# Load stations data
station_df = pd.read_csv(
    project_base
    + "transit_lab_simmetro" / "odx_arrival" / "data" / "blue_line_stations.csv"
)

df = pd.read_csv(
    project_base
    + "transit_lab_simmetro" / "odx_arrival" / "data" / "ODX_Journeys_Nov.csv"
)

df["Destination"] = df["first_alighting_platform"].map(
    dict(zip(station_df["STOP_ID"], station_df["STATION_NAME_IN_SIM"]))
)

# Convert 'transaction_dtm' to datetime format
df["transaction_dtm"] = pd.to_datetime(df["transaction_dtm"])

# Extract hour and determine if the day is a weekday
df["hour"] = df["transaction_dtm"].dt.hour + df["transaction_dtm"].dt.minute / 60
df["hour"] = df["hour"].round(2)  # Round to 2 decimal places
df["weekday"] = (df["transaction_dtm"].dt.weekday < 5) & (
    ~df["transaction_dtm"].dt.date.isin(USFederalHolidayCalendar().holidays())
)  # True for weekdays (Mon-Fri)

# Create bins for 15-minute intervals
time_bins = [i / 4 for i in range(24 * 4)]
df["time_bin"] = pd.cut(df["hour"], bins=time_bins, labels=time_bins[:-1], right=False)

# Group by 15-minute intervals, weekday, and boarding stations
grouped = df.groupby(["weekday", "Origin"])

grouped_df = grouped.apply(
    lambda group: sum(group["first_alighting_platform"].notnull() / len(group))
).reset_index(name="inferred_ratio")


def rate_group(group):
    num_days = len(group["transaction_dtm"].dt.date.unique())
    num_boarding = len(group)
    return num_boarding / num_days * 60 / 15


rate_df = (
    df.groupby(["time_bin", "weekday", "Origin", "Destination"])
    .apply(rate_group)
    .reset_index(name="unscaled_arrival_rate")
)

rate_df.set_index(["time_bin", "weekday", "Origin"], inplace=True)
grouped_df.set_index(["weekday", "Origin"], inplace=True)

# Use the map function on the rate_df index to get the corresponding inferred_ratio from grouped_df
rate_df["inferred_ratio_mapped"] = rate_df.index.map(
    lambda idx: grouped_df.loc[(idx[1], idx[2]), "inferred_ratio"]
)

rate_df.reset_index(inplace=True)
# Perform the division to scale arrival_rate
rate_df["arrival_rate"] = (
    rate_df["unscaled_arrival_rate"] / rate_df["inferred_ratio_mapped"]
)

rate_df.to_csv("./data/arrival_rates_Nov.csv", index=False)
