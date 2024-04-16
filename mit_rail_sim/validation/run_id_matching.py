# Loading static data
import json
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

with open("/Users/moji/Projects/mit_rail_sim/alt_file_northbound_updated.json", "r") as f:
    data = json.load(f)
    track_dist = {}
    distance = 0
    for block in data:
        distance += block["DISTANCE"]
        track_dist[block["BLOCK_ALT"]] = distance

df = pd.read_csv(
    "/Users/moji/Projects/mit_rail_sim/mit_rail_sim/validation/data/track_events.csv",
    parse_dates=["event_time"],
    usecols=["event_time", "scada", "run_id"],
)

df = df[df["event_time"].dt.date == pd.to_datetime("04-01-2023").date()]

# df = df[df["run_id"] == "B102"]

df["track_dist"] = df["scada"].map(track_dist)
df = df[(df["track_dist"] >= 1805) & (df["track_dist"] <= 145200)]

df.sort_values("event_time", inplace=True)
df.reset_index(inplace=True, drop=True)

for run_id in df["run_id"].unique():
    run_index = df["run_id"] == run_id
    df.loc[run_index, "run_id"] = f"{run_id}_0"
    split_indices = df[run_index].index[abs(df[run_index]["track_dist"].diff()) > 5000].to_list()
    if split_indices:
        split_indices.append(df.index[-1] + 1)
    for i in range(len(split_indices) - 1):
        df.loc[
            run_index & (df.index >= split_indices[i]) & (df.index < split_indices[i + 1]), "run_id"
        ] = f"{run_id}_{i+1}"


def is_start_valid(start, start_threshold):
    return (
        (abs(start["track_dist"] - 1805) <= start_threshold)
        or (abs(start["track_dist"] - 45896) <= start_threshold)
        or (start["event_time"] - pd.to_datetime("04-01-2023 00:00:00") <= timedelta(seconds=180))
    )


def is_end_valid(end, end_threshold):
    return abs(end["track_dist"] - 143600) <= end_threshold


@dataclass
class RunIDClass:
    run_id: str
    start: pd.DataFrame
    end: pd.DataFrame
    valid_start: bool
    valid_end: bool

    @property
    def is_valid(self):
        return self.valid_start and self.valid_end

    def __add__(self, other):
        df.loc[df["run_id"] == self.run_id, "run_id"] = self.run_id + "_" + other.run_id
        df.loc[df["run_id"] == other.run_id, "run_id"] = self.run_id + "_" + other.run_id

        return RunIDClass(
            self.run_id + "_" + other.run_id,
            other.end,
            self.end,
            other.valid_start,
            self.valid_end,
        )

    def __le__(self, other):
        return (
            abs((self.start["event_time"] - other.end["event_time"])).total_seconds() < 80
        ) and (abs(self.start["track_dist"] - other.end["track_dist"]) <= 1000)

    def __sub__(self, other):
        if self.start["event_time"] > other.end["event_time"]:
            return (self.start["track_dist"] - other.end["track_dist"]) + (
                self.start["event_time"] - other.end["event_time"]
            ).total_seconds()
        else:
            return float("inf")


trips = []

for run_id in df["run_id"].unique():
    run_index = df["run_id"] == run_id
    start, end = df.loc[run_index].iloc[0], df.loc[run_index].iloc[-1]

    trips.append(
        RunIDClass(
            run_id,
            start,
            end,
            is_start_valid(start, 500),
            is_end_valid(end, 500),
        )
    )

valid_trips = [trip for trip in trips if trip.is_valid]
unmatched_trips = [trip for trip in trips if not trip.is_valid]

for trip in unmatched_trips:
    if trip.valid_start:
        continue
    candidate = min(
        [t for t in unmatched_trips if trip <= t and t != trip and trip - t < 1000],
        default=None,
        key=lambda t: trip - t,
    )

    if candidate is not None:
        combined_trip = trip + candidate
        if combined_trip.is_valid:
            valid_trips.append(combined_trip)
        else:
            unmatched_trips.append(combined_trip)

        unmatched_trips.remove(candidate)
        unmatched_trips.remove(trip)

    else:
        valid_trips.append(trip)
        unmatched_trips.remove(trip)

df.to_csv("/Users/moji/Projects/mit_rail_sim/mit_rail_sim/validation/data/sample_split.csv")
