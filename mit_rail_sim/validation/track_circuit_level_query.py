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

# Query to fetch event data
query_text1 = text(
    "SELECT event_time, event_type, run_id, scada, locationdesc, line_id, dir_id, track_id,"
    " qt2_trackid, deviation, headway, direction, action FROM cta01.avas_spectrum.qt2_trainevent"
    " WHERE (event_time >= :start_date AND event_time < :end_date) AND (run_id= 'B107');"
)


events_df = pd.read_sql(
    query_text1, engine, params={"start_date": start_date, "end_date": "2023-04-02"}
)

events_df.to_csv("./data/track_events_south.csv", index=False)
