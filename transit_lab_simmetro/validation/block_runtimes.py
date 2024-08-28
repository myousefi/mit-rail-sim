import json

import pandas as pd

from transit_lab_simmetro.utils import project_root

# Step 1: Create a list of all blocks associated with stations and the blocks that come immediately after them
with open(project_root / "alt_file_northbound_updated.json", "r") as f:
    data = json.load(f)
    scada_next = {}
    scada_len = {}
    for i, block in enumerate(data[:-1]):
        scada_next[block["BLOCK_ALT"]] = data[i + 1]["BLOCK_ALT"]
        scada_len[block["BLOCK_ALT"]] = block["DISTANCE"]

# Load the track_events dataset
track_events = pd.read_csv(
    project_root / "transit_lab_simmetro" / "validation" / "data" / "track_events.csv",
    parse_dates=["event_time"],
)

track_events = track_events[
    (track_events["event_time"] >= "2023-05-15")
    & (track_events["event_time"] < "2023-05-25")
    & (track_events["event_time"].dt.hour >= 7)
    & (track_events["event_time"].dt.hour < 9)
]


# Step 4: Sort the DataFrame by event_time
track_events = track_events.sort_values(by=["run_id", "event_time"])

track_events["next_scada"] = track_events["scada"].map(scada_next)
track_events["scada_len"] = track_events["scada"].map(scada_len)


# Step 6: Within each group, calculate the time difference between consecutive rows
# and check if the SCADA blocks are consecutive
def calculate_diff(group):
    group["time_difference"] = (-group["event_time"].diff(-1)).dt.seconds
    group["scada_consecutive"] = group["next_scada"].eq(group["scada"].shift(-1))

    # if len(group) < 2:
    #     return None

    return group


# Step 5: Group the data by run_id
grouped = track_events.groupby("run_id", as_index=False)
result_df = grouped.apply(calculate_diff)

result_df = result_df[result_df["scada_consecutive"]]

result_df["speed"] = (
    result_df["scada_len"] / result_df["time_difference"]
) * 0.681818  # feet per second to miles per hour


# filter out outliers by fence method for each scada
def filter_outliers(group):
    q1 = group["speed"].quantile(0.25)
    q3 = group["speed"].quantile(0.75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    group = group[(group["speed"] > lower_fence) & (group["speed"] < upper_fence)]
    return group


grouped = result_df.groupby("scada", as_index=False)
result_df = grouped.apply(filter_outliers)

grouped = result_df.groupby("scada", as_index=False)
result_df = grouped["speed"].mean()


sim_df = pd.read_csv(
    project_root
    / "transit_lab_simmetro"
    / "validation"
    / "simulation_results"
    / "block_test.csv"
)

sim_df.rename(columns={"block_id": "scada"}, inplace=True)
sim_df["next_scada"] = sim_df["scada"].map(scada_next)
sim_df["scada_len"] = sim_df["scada"].map(scada_len)

sim_df.sort_values(by=["replication_id", "train_id", "time_in_seconds"], inplace=True)
grouped = sim_df.groupby(by=["replication_id", "train_id"], as_index=False)


def calculate_diff(group):
    group["time_difference"] = -group["time_in_seconds"].diff(-1)
    group["scada_consecutive"] = group["next_scada"].eq(group["scada"].shift(-1))
    return group


sim_df = grouped.apply(calculate_diff)

sim_df.to_csv(
    project_root
    / "transit_lab_simmetro"
    / "validation"
    / "simulation_results"
    / "block_test_s.csv",
    index=False,
)

sim_df = sim_df[sim_df["scada_consecutive"]]

sim_df["speed"] = (
    sim_df["scada_len"] / sim_df["time_difference"]
) * 0.681818  # feet per second to miles per hour


grouped = sim_df.groupby("scada", as_index=False)


sim_df = grouped["speed"].mean()

sim_df.to_csv(
    project_root
    / "transit_lab_simmetro"
    / "validation"
    / "simulation_results"
    / "block_test_speed.csv",
    index=False,
)
# Step 7: Save the results back to a new CSV file
result_df.to_csv(
    project_root
    / "transit_lab_simmetro"
    / "validation"
    / "data"
    / "track_events_result.csv",
    index=False,
)
