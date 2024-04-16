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
engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}").connect()

query_text = """
SELECT DATE(transaction_dtm) as transaction_date, COUNT(*) as total_tap_ins
FROM planning_models_spectrum.odx_journeys
WHERE operator_nm = '2-CTA Bus'
AND transaction_dtm >= '2023-01-01'
AND transaction_dtm < '2023-10-09'
GROUP BY DATE(transaction_dtm);
"""


# Execute the query
result_df = pd.read_sql(
    query_text,
    engine,
)

result_df.sort_values(by="transaction_date").to_csv("bus_tap_in_series.csv", index=False)
