from mit_rail_sim.utils import project_root
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

start_date = "2023-11-13"
end_date = "2023-12-18"

# Connect to the database
engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}").connect()

# Load station and direction mapping from CSV
station_direction_df = pd.read_csv(
    project_root / "mit_rail_sim" / "odx_arrival" / "data" / "blue_line_stations.csv"
)

# Create a dictionary mapping from trackid to station and direction
station_trackid_direction = {
    row["qt2_trackid"]: {
        "station": row["STATION_NAME_IN_SIM"],
        "direction": row["dir_id"],
    }
    for _, row in station_direction_df.iterrows()
}

# Update the query strings to include direction
trackid_query_str = " or ".join(
    [f"qt2_trackid = {trackid}" for trackid in station_trackid_direction.keys()]
)

# Update the CASE statement to include direction
case_statement = " ".join(
    [
        f"WHEN qt2_trackid = {trackid} THEN '{info['station']}'"
        for trackid, info in station_trackid_direction.items()
    ]
)
direction_case_statement = " ".join(
    [
        f"WHEN qt2_trackid = {trackid} THEN '{info['direction']}'"
        for trackid, info in station_trackid_direction.items()
    ]
)

# Modify the query to fetch headway data to include direction
query_text2 = text(
    "SELECT event_datetime, qt2_trackid, hdw_deptoarr, hdw_arrtoarr, dwell_arrtodep, sched_stdevhdw, "
    f"CASE {case_statement} END as station, "
    f"CASE {direction_case_statement} END as direction "
    "FROM cta01.avas_spectrum.qt2_trackhdw "
    f"WHERE event_datetime >= :start_date AND event_datetime < :end_date AND ({trackid_query_str})"
)

headways_df = pd.read_sql(
    query_text2, engine, params={"start_date": start_date, "end_date": end_date}
)

# Modify the query to fetch event data to include direction
query_text1 = text(
    "SELECT event_time, run_id, action, deviation, headway, qt2_trackid, "
    f"CASE {case_statement} END as station, "
    f"CASE {direction_case_statement} END as direction "
    "FROM cta01.avas_spectrum.qt2_trainevent "
    f"WHERE event_time >= :start_date AND event_time < :end_date AND ({trackid_query_str}) AND run_id LIKE 'B%' AND action = 'MOVE'"
)

events_df = pd.read_sql(
    query_text1, engine, params={"start_date": start_date, "end_date": end_date}
)

# Sort and filter dataframes
events_df = events_df.sort_values("event_time")
headways_df = headways_df.sort_values("event_datetime")

# Filter the events dataframe for 'MOVE' action
events_df = events_df[events_df["action"] == "MOVE"]

events_df = events_df[["event_time", "run_id", "qt2_trackid", "deviation", "headway"]]

final_df = pd.merge_asof(
    left=headways_df,
    right=events_df,
    left_on="event_datetime",
    right_on="event_time",
    by=["qt2_trackid"],
    direction="nearest",
)

final_df = final_df[
    [
        "event_datetime",
        "run_id",
        "station",
        "direction",  # Include direction column
        "hdw_deptoarr",
        "hdw_arrtoarr",
        "dwell_arrtodep",
        "sched_stdevhdw",
        "deviation",
        "headway",
    ]
]

# Sort the final DataFrame
final_df.sort_values("event_datetime", inplace=True)

# Save the final result to a CSV file
final_df.to_csv("./data/sched_81.csv", index=False)
