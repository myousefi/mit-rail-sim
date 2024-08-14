# %%
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

query_text1 = text(
    """
    SELECT
        run_id,
        locationdesc,
        deviation,
        headway,
        event_time,
        CASE scada
            WHEN 'nwc720t' THEN 'O-Hare Arrival'
            WHEN 'nwd720t' THEN 'O-Hare Departure'
            WHEN 'wd452t' THEN 'Forest Park Arrival'
            WHEN 'wc452t' THEN 'Forest Park Departure'
            WHEN 'wd005t' THEN 'UIC-Halsted SB Arrival'
            WHEN 'wd013t' THEN 'UIC-Halsted SB Departure'
            WHEN 'wd008t' THEN 'UIC-Halsted NB Arrival'
            WHEN 'wc005t' THEN 'UIC-Halsted NB Departure'
        END AS station_event
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        event_time::date = '2024-02-23' AND
        action = 'MOVE' AND
        scada IN ('nwc720t', 'nwd720t', 'wd452t', 'wc452t', 'wd005t', 'wd013t', 'wd008t', 'wc005t')
    ORDER BY
        event_time;
   """
)

pd.read_sql(
    query_text1, engine, params={"start_date": start_date, "end_date": end_date}
).to_csv(
    "./02-23-2024.csv",
    index=False,
)

# %%
