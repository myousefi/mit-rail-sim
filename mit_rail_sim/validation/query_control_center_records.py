import csv
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
    f"SELECT timec, timerc, line, lineall, station, datec, direction, nature, naturefinal, drqbe,"
    f" run, terminal, timert, delay, details FROM cta01.cpc.rrecord WHERE datec >= :start_date AND"
    f" datec < :end_date"
)

pd.read_sql(query_text1, engine, params={"start_date": start_date, "end_date": end_date}).to_csv(
    "./data/cpc_records.csv",
    index=False,
    sep="|",
    quotechar='"',
    quoting=csv.QUOTE_NONNUMERIC,
)
