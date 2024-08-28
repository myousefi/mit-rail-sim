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

engine = create_engine(
    f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
).connect()

station_trackid = {
    "Forest Park": 11020,
    "Harlem (Forest Park Branch)": 11040,
    "Oak Park": 11060,
    "Austin": 11080,
    "Cicero": 11100,
    "Pulaski": 11120,
    "Kedzie-Homan": 11140,
    "Western (Forest Park Branch)": 11160,
    "Illinois Medical District": 11180,
    "Racine": 11220,
    "UIC-Halsted": 11240,
    "Clinton": 11260,
    "LaSalle": 11280,
    "Jackson": 11300,
    "Monroe": 11320,
    "Washington": 11340,
    "Clark/Lake": 11360,
    "Grand": 11380,
    "Chicago": 11400,
    "Division": 11420,
    "Damen": 11440,
    "Western (O-Hare Branch)": 11460,
    "California": 11480,
    "Logan Square": 11500,
    "Belmont": 11520,
    "Addison": 11540,
    "Irving Park": 11560,
    "Montrose": 11580,
    "Jefferson Park": 11600,
    "Harlem (O-Hare Branch)": 11620,
    "Cumberland": 11640,
    "Rosemont": 11660,
    "O-Hare": 11700,
}

trackid_query_str = " or ".join(
    [f"qt2_trackid = {trackid}" for trackid in station_trackid.values()]
)

query_text1 = text(
    "SELECT *, CASE "
    + " ".join(
        [
            f"WHEN qt2_trackid = {trackid} THEN '{station}'"
            for station, trackid in station_trackid.items()
        ]
    )
    + " END as station FROM cta01.avas_spectrum.qt2_trainevent WHERE event_time >="
    f" :start_date AND event_time < :end_date AND ({trackid_query_str}) ORDER BY"
    " run_id, event_time;"
)

pd.read_sql(
    query_text1, engine, params={"start_date": start_date, "end_date": end_date}
).to_csv(
    "./data/events.csv",
    index=False,
)
