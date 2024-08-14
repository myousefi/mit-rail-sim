import json
import unittest

import pandas as pd
import plotly.graph_objects as go
import scipy.stats as st
from fitter import Fitter
from matplotlib import pyplot as plt
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay


class TestDispatchingHeadway(unittest.TestCase):
    def setUp(self):
        self.filename = "data/dispatching_headway_forest_park.csv"
        self.us_bd = CustomBusinessDay(calendar=USFederalHolidayCalendar())

    def preprocess_data(self, filename):
        df = pd.read_csv(filename)
        df["event_time"] = pd.to_datetime(df["event_time"])
        df = df[df["event_time"].dt.dayofweek < 5]
        # filter out weekends and US federal holidays

        # df = df[
        #     df["event_time"].dt.date.isin(
        #         pd.date_range(start="2023-01-01", end="2023-06-30", freq=self.us_bd)
        #     )
        # ]

        # set the date part to '1970-01-01' but keep the original time
        df["event_time"] = df["event_time"].apply(
            lambda dt: dt.replace(year=1970, month=1, day=1)
        )

        df = df[
            (df["headway"] > df["headway"].quantile(0.01))
            & (df["headway"] < df["headway"].quantile(0.99))
        ]

        # convert headway from minutes to seconds
        # df["headway"] = df["headway"] * 60
        return df

    def test_weekday_entries(self):
        df = self.preprocess_data(self.filename)
        df.set_index("event_time", inplace=True)
        df = df.resample("15T")["headway"].agg(["mean", "std"]).dropna()
        df = df.reset_index()
        df["event_time"] = df["event_time"].dt.time.astype(str)
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Mean Headway",
                    x=df["event_time"],
                    y=df["mean"],
                    error_y=dict(type="data", array=df["std"], visible=True),
                )
            ]
        )
        fig.update_layout(
            barmode="group",
            title="Headway Statistics Over Time",
            xaxis_title="Time",
            yaxis_title="Headway",
        )
        fig.show()

    def test_fit_distributions(self):
        df = self.preprocess_data(self.filename)
        df_time_range = df[
            (df["event_time"] >= pd.Timestamp("1970-01-01 06:15:00"))
            & (df["event_time"] < pd.Timestamp("1970-01-01 08:00:00"))
        ]
        f = Fitter(df_time_range["headway"], timeout=10)
        f.fit()
        summary = f.summary(Nbest=10)
        summary.to_csv("summary.csv")
        f.plot_pdf()
        plt.savefig("distributions.pdf")

    def test_fit_weibull(self):
        df = self.preprocess_data(self.filename)
        df_time_range = df[
            (df["event_time"] >= pd.Timestamp("1970-01-01 06:15:00"))
            & (df["event_time"] < pd.Timestamp("1970-01-01 08:00:00"))
        ]
        params = st.weibull_min.fit(df_time_range["headway"])
        with open("weibull_params.json", "w") as f:
            json.dump(params, f)

    def test_read_csv_file(self):
        df = pd.read_csv(self.filename)
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)


if __name__ == "__main__":
    unittest.main()
