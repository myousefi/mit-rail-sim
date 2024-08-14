# %%

import os

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv(find_dotenv())

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")
start_date = os.getenv("start_date")
end_date = os.getenv("end_date")

# Connect to the database
engine = create_engine(
    f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
).connect()

# %%
query_text = text(
    """
    SELECT transaction_dtm,boarding_stop,route_sequence,direction_sequence,boarding_platform_sequence,alighting_platform_sequence
    FROM planning_models_spectrum.odx_journeys
    WHERE
        boarding_stop = 40670 AND
        transaction_dtm BETWEEN '2023-02-24 07:00:00' AND '2023-02-24 10:00:00'
    """,
)


# Execute the query
afc_df = pd.read_sql(
    query_text,
    engine,
)

# %%


query_text = text(
    """
    SELECT event_datetime, qt2_trackid, hdw_deptoarr, hdw_arrtoarr, dwell_arrtodep, sched_stdevhdw
    FROM cta01.avas_spectrum.qt2_trackhdw
    WHERE
        event_datetime BETWEEN '2023-02-24 07:00:00' AND '2023-02-24 10:00:00' AND
        (qt2_trackid = 11460)
    """
)

avl_df = pd.read_sql(query_text, engine)

# %%
import matplotlib.pyplot as plt

# Assuming 'transaction_dtm' is the datetime column for afc_df
afc_df["transaction_dtm"] = pd.to_datetime(afc_df["transaction_dtm"])
afc_df.sort_values("transaction_dtm", inplace=True)

# Assuming 'event_datetime' is the datetime column for avl_df
avl_df["event_datetime"] = pd.to_datetime(avl_df["event_datetime"])
avl_df.sort_values("event_datetime", inplace=True)

# %%
# Assuming 'transaction_dtm' is the datetime column for afc_df
afc_df["transaction_dtm"] = pd.to_datetime(afc_df["transaction_dtm"])
afc_df.sort_values("transaction_dtm", inplace=True)

afc_df["numpax"] = 1
# Assuming 'boarding_stop' is the column to sum over for the number of entries
afc_df["cumulative_entries"] = afc_df["numpax"].cumsum()

# Plotting the accumulative sum of afc_df over time
plt.figure(figsize=(12, 6))
plt.plot(afc_df["transaction_dtm"], afc_df["cumulative_entries"])
plt.xlabel("Time")
plt.ylabel("Cumulative Entries")
plt.title("Accumulative Sum of AFC Data Over Time")
plt.show()
# %%


# %%
# Reset the cumulative sum at the times specified in avl_df
reset_times = avl_df["event_datetime"].tolist()
for reset_time in reset_times:
    # Find the index in afc_df where the reset should occur
    reset_index = afc_df[afc_df["transaction_dtm"] >= reset_time].index.min()
    if pd.notna(reset_index):
        # Reset the cumulative sum from this point forward
        cumulative_sum = afc_df.at[reset_index + 1, "cumulative_entries"]
        afc_df.loc[reset_index:, "cumulative_entries"] = afc_df.loc[
            reset_index:, "cumulative_entries"
        ].apply(lambda x: x - cumulative_sum)

# %%
# Plot the cumulative sum
plt.figure(figsize=(12, 6))
plt.plot(
    afc_df["transaction_dtm"],
    afc_df["cumulative_entries"],
    label="Cumulative Passengers",
)
plt.xlabel("Time")
plt.ylabel("Number of Passengers")
plt.title("Accumulative Sum of Passengers Through Time")
plt.legend()
plt.show()

# %%
