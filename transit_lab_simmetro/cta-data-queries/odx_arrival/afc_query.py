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

# Load stations data
station_df = pd.read_csv("data/blue_line_stations.csv")

# Generate query text
query_text = text(
    """
    SELECT transaction_dtm,boarding_stop,route_sequence,direction_sequence,boarding_platform_sequence,alighting_platform_sequence
    FROM planning_models_spectrum.odx_journeys
    WHERE
        boarding_stop IN :boarding_stops_list AND
        transaction_dtm BETWEEN :start_date AND :end_date
    """,
)

# Execute the query
result_df = pd.read_sql(
    query_text,
    engine,
    params={
        "boarding_stops_list": tuple(station_df["MAP_ID"].unique().tolist()),
        "start_date": "2023-11-13",
        "end_date": "2023-12-13",
    },
)

result_df["Origin"] = (
    result_df["boarding_stop"]
    .astype(str)
    .map(dict(zip(station_df["MAP_ID"].astype(str), station_df["STATION_NAME_IN_SIM"])))
)

for col in [
    "route_sequence",
    "direction_sequence",
    "boarding_platform_sequence",
    "alighting_platform_sequence",
]:
    result_df["first_" + col.replace("_sequence", "")] = (
        result_df[col].str.split("|").str[1]
    )

result_df.sort_values(["transaction_dtm"], inplace=True)

result_df.to_csv("./data/ODX_Journeys_Nov.csv", index=False)
