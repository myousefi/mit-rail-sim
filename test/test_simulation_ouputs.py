import unittest

import numpy as np
import pandas as pd
import plotly.express as px
from pandas.api.types import is_numeric_dtype


class TestRailwaySimulation(unittest.TestCase):
    def test_headway_variation(self):
        # Read CSV file
        df = pd.read_csv("test/output_files/station_test.csv")

        # Ensure headway is numeric
        assert is_numeric_dtype(df["headway"]), "Headway is not numeric"

        # Convert headway to minutes
        df["headway"] = df["headway"] / 60

        # Calculate coefficient of variation
        station_headway_cv = (
            df.groupby("station_name")["headway"]
            .apply(lambda x: np.std(x, ddof=1) / np.mean(x) if np.mean(x) != 0 else 0)
            .reset_index()
        )

        # Get the first replication ID
        first_replication_id = df["replication_id"].min()

        # Keep the stations sorted as per the first train in the first replication
        first_train_stations = (
            df[
                (df["train_id"] == "train_0")
                & (df["replication_id"] == first_replication_id)
            ]
            .sort_values(by="time_in_seconds")["station_name"]
            .tolist()
        )
        station_headway_cv["station_name"] = pd.Categorical(
            station_headway_cv["station_name"],
            categories=first_train_stations,
            ordered=True,
        )
        station_headway_cv = station_headway_cv.sort_values("station_name")

        # Plot coefficient of variation
        fig = px.bar(
            station_headway_cv,
            x="station_name",
            y="headway",
            labels={
                "headway": "Coefficient of Variation (%)",
                "station_name": "Station Name",
            },
            title="Coefficient of Variation of Headways",
        )
        fig.show()


if __name__ == "__main__":
    unittest.main()
