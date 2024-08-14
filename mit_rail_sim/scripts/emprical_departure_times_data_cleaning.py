import pandas as pd

# Load the dataset
df = pd.read_csv("data/emprical_schedule/events.csv")

# Convert to datetime and create date column
df["event_time"] = pd.to_datetime(df["event_time"])
df["date"] = df["event_time"].dt.date

# Filter data to keep only the working days
df["day_of_week"] = df["event_time"].dt.dayofweek
df = df[df["day_of_week"].isin(range(5))]  # Keep only Monday (0) to Friday (4)


# Define the function that marks pairs of MOVE and REMOVE actions
def remove_move_and_remove_pairs(group):
    time_window = pd.Timedelta(minutes=1)
    group = group.sort_values("event_time")
    actions_to_remove = []
    for i, row in group.iterrows():
        if row["action"] == "MOVE":
            remove_action = group[
                (group["event_time"] >= row["event_time"])
                & (group["event_time"] < row["event_time"] + time_window)
                & (group["action"] == "REMOVE")
            ]
        else:  # 'REMOVE'
            remove_action = group[
                (group["event_time"] > row["event_time"] - time_window)
                & (group["event_time"] <= row["event_time"])
                & (group["action"] == "MOVE")
            ]
        if not remove_action.empty:
            actions_to_remove.extend([i, remove_action.index[0]])
    group.loc[actions_to_remove, "to_be_removed"] = True
    return group


# Apply the function to each group
df = df.groupby(["run_id", "station", "date"]).apply(remove_move_and_remove_pairs)

# Remove rows marked to be removed
df = df[df["to_be_removed"] != True]
df = df.drop(columns="to_be_removed")

# Reset index again
df = df.reset_index(drop=True)

# Calculate time_period_before for short_turning
station_to_time = {
    "Forest Park": 14,
    "Harlem (Forest Park Branch)": 14,
    "Oak Park": 14,
    "Austin": 14,
    "Cicero": 14,
    "Pulaski": 31,
    "Kedzie-Homan": 31,
    "Western (Forest Park Branch)": 31,
    "Illinois Medical District": 31,
    "Racine": 31,
    "UIC-Halsted": 31,
    "Clinton": 40,
    "LaSalle": 40,
    "Jackson": 40,
    "Monroe": 40,
    "Washington": 40,
    "Clark/Lake": 40,
    "Grand": 54,
    "Chicago": 54,
    "Division": 54,
    "Damen": 54,
    "Western (O-Hare Branch)": 54,
    "California": 54,
    "Logan Square": 54,
    "Belmont": 64,
    "Addison": 64,
    "Irving Park": 64,
    "Montrose": 64,
    "Jefferson Park": 64,
    "Harlem (O-Hare Branch)": 79,
    "Cumberland": 79,
    "Rosemont": 79,
    "O-Hare": 79,
}

# Multiply the values by 1.5 and convert them to hours
station_to_time = {k: int(v * 1.5 / 60) for k, v in station_to_time.items()}

df["time_period_before"] = pd.to_timedelta(df["station"].map(station_to_time), unit="h")
df["time_period_before"] = df["event_time"] - df["time_period_before"]


# Define the function that identifies short-turning trips
def check_short_turning(group):
    group = group.sort_values("event_time")
    for i, row in group.iterrows():
        # Get the events in the 3-hour period before the current event
        prev_events = group[
            (group["event_time"] >= row["time_period_before"])
            & (group["event_time"] < row["event_time"])
        ]

        if list(station_to_time.keys()).index(row["station"]) <= 9:
            group.loc[i, "is_short_turning"] = 0
        elif (
            "Forest Park" in prev_events["station"].values
            or row["station"] == "LV Forest Park"
        ):
            group.loc[i, "is_short_turning"] = 0
        elif "Cicero" in prev_events["station"].values or row["station"] == "Cicero":
            group.loc[i, "is_short_turning"] = 0
        else:
            group.loc[i, "is_short_turning"] = 1
    return group


# Check short turning based on the stations visited
df = df.groupby(["run_id", "date"]).apply(check_short_turning)


# Reset index again
df = df.reset_index(drop=True)

# Save the DataFrame into a new CSV file
df.to_csv("data/emprical_schedule/cleaned_events.csv", index=False)
