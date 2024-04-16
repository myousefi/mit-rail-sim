import os

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(find_dotenv())

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")

start_date = os.getenv("start_date")
end_date = os.getenv("end_date")

engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}").connect()

query_text1 = text(
    f"SELECT event_time, run_id, headway, deviation, qt2_trackid "
    f"FROM cta01.avas_spectrum.qt2_trainevent WHERE "
    f"event_time >= :start_date AND event_time < :end_date "
    f"AND (qt2_trackid = 15020 OR qt2_trackid = 11020) "
    f"ORDER BY event_time;"
)


pd.read_sql(query_text1, engine, params={"start_date": start_date, "end_date": end_date}).to_csv(
    "./data/events.csv",
    index=False,
)
