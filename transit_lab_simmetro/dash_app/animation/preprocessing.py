import os

import pandas as pd

from transit_lab_simmetro.utils import project_root

os.chdir(project_root / "transit_lab_simmetro" / "dash_app" / "animation")

# Read the CSV file into a DataFrame
csv_path = (
    project_root
    / "transit_lab_simmetro"
    / "validation"
    / "simulation_results"
    / "train_test.csv"
)
df = pd.read_csv(csv_path)

# Convert time_in_seconds to a Pandas Timedelta object for resampling
df["time_in_seconds"] = pd.to_timedelta(df["time_in_seconds"], unit="s")

# Define the origin timestamp: 7:00 AM of April first, 2023
origin_timestamp = pd.Timestamp("2023-04-01 07:00:00")

# Adjust the time_in_seconds to reflect the seconds passed since 7:00 AM, April 1, 2023
df["adjusted_time"] = origin_timestamp + df["time_in_seconds"]

# Create an empty DataFrame to store the final results

# Group by 'replication_id', 'train_id' and the 10-second intervals
df = (
    df.groupby(
        ["replication_id", "train_id", pd.Grouper(key="adjusted_time", freq="10S")]
    )
    .first()
    .reset_index()
)

# Optionally, convert back to time_in_seconds relative to 7:00 AM, April 1, 2023
df["time_in_seconds"] = (df["adjusted_time"] - origin_timestamp).dt.total_seconds()

# Drop the 'adjusted_time' column as it's no longer needed
df.drop(columns=["adjusted_time"], inplace=True)

# Save the resampled DataFrame
df.to_csv("./preprocessed_data.csv", index=False)
