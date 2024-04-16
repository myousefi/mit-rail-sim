import csv

import pandas as pd

# Step 2: Read the CSV file into a DataFrame
df = pd.read_csv(
    "./data/cpc_records.csv", delimiter="|", quotechar='"', quoting=csv.QUOTE_NONNUMERIC
)

# Drop columns with more than 90% null values
df = df.dropna(thresh=len(df) * 0.1, axis=1)


# keep only rows that have Blue as part of their direction
df = df[df["line"].str.contains("Blue", na=False)]
df = df[df["direction"] != "SB"]


# Step 2: Create a new 'event_datetime' column by combining 'datec' and 'timerc'
df["event_datetime"] = pd.to_datetime(df["datec"] + " " + df["timerc"])
df.sort_values("event_datetime", inplace=True)

df.to_csv("./data/blue_line_cpc_records.csv", index=False, sep="|", quotechar='"')

# Step 3: Write the DataFrame to a new CSV, including only the required columns
df[["event_datetime", "delay", "drqbe"]].to_csv(
    "./data/blue_line_event_delay_drqe.csv", index=False
)
