import pandas as pd

# Load CSV files
events_df = pd.read_csv("./data/events.csv", parse_dates=["event_time"])
headways_df = pd.read_csv("./data/headways.csv", parse_dates=["event_datetime"])

# Sort the dataframes
events_df.sort_values(["station", "event_time"], inplace=True)
headways_df.sort_values(["station", "event_datetime"], inplace=True)

events_df = events_df[events_df["action"] == "MOVE"]

# Initialize a list to hold the merged sub-dataframes
merged_dfs = []

# Loop through unique stations and perform asof join
for station in events_df["station"].unique():
    events_sub_df = events_df[events_df["station"] == station]
    headways_sub_df = headways_df[headways_df["station"] == station]

    merged_sub_df = pd.merge_asof(
        headways_sub_df,
        events_sub_df,
        by="station",
        left_on="event_datetime",
        right_on="event_time",
        direction="nearest",
    )

    merged_dfs.append(merged_sub_df)

# Concatenate all sub-dataframes at once
final_df = pd.concat(merged_dfs, ignore_index=True)

final_df = final_df[
    [
        # Columns from events.csv
        "event_datetime",
        "run_id",
        "station",
        "hdw_deptoarr",
        "hdw_arrtoarr",
        "dwell_arrtodep",
        "deviation",
        "headway",  # Columns from headways.csv
    ]
]

final_df.sort_values("event_datetime", inplace=True)
# Save the final result
final_df.to_csv("./data/merged_data.csv", index=False)
