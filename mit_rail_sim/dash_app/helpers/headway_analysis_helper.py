import pandas as pd
import plotly.graph_objects as go


class HeadwayAnalysis:
    def __init__(self, cleaned_events_path, train_test_path, station_test_path):
        self.cleaned_events_path = cleaned_events_path
        self.train_test_path = train_test_path
        self.station_test_path = station_test_path

        self.load_and_clean_data()
        self.filter_and_prepare_data()
        self.calculate_statistics()

    def mean(self, real_or_sim: str, station: str):
        if real_or_sim == "REAL":
            if station == "Forest Park":
                return self.real_headway_fp.mean()
            elif station == "UIC-Halsted":
                return self.real_headway_uic_halsted.mean()

        elif real_or_sim == "SIM":
            if station == "Forest Park":
                return self.sim_headway_forest_park.mean()
            elif station == "UIC-Halsted":
                return self.sim_headway_uic_halsted.mean()

        raise ValueError("Invalid input")

    def std(self, real_or_sim: str, station: str):
        if real_or_sim == "REAL":
            if station == "Forest Park":
                return self.real_headway_fp.std()
            elif station == "UIC-Halsted":
                return self.real_headway_uic_halsted.std()

        elif real_or_sim == "SIM":
            if station == "Forest Park":
                return self.sim_headway_forest_park.std()
            elif station == "UIC-Halsted":
                return self.sim_headway_uic_halsted.std()

        raise ValueError("Invalid input")

    def coef_var(self, real_or_sim: str, station: str):
        return self.std(real_or_sim, station) / self.mean(real_or_sim, station)

    def load_and_clean_data(self):
        # Load datasets
        self.train_test = pd.read_csv(self.train_test_path)
        self.station_test = pd.read_csv(self.station_test_path)
        self.cleaned_events = pd.read_csv(self.cleaned_events_path)

        # Clean cleaned_events data
        self.cleaned_events["event_time"] = pd.to_datetime(
            self.cleaned_events["event_time"]
        )
        self.cleaned_events["station"] = self.cleaned_events["station"].replace(
            "LV Forest Park", "Forest Park"
        )

        # Convert headway from seconds to minutes
        self.station_test["headway"] = self.station_test["headway"] / 60

    def filter_and_prepare_data(self):
        # Apply filtering
        mask = (
            (self.cleaned_events["station"].isin(["Forest Park", "UIC-Halsted"]))
            & (
                (
                    self.cleaned_events["event_time"].dt.time
                    >= pd.to_datetime("07:00:00").time()
                )
                & (
                    self.cleaned_events["event_time"].dt.time
                    <= pd.to_datetime("11:00:00").time()
                )
            )
            & (
                (self.cleaned_events["station"] != "UIC-Halsted")
                | (self.cleaned_events["is_short_turning"] == 1.0)
            )
        )
        self.cleaned_events_filtered = self.cleaned_events.loc[mask]

        # Determine short-turning trips
        short_turning_trips = self.train_test.loc[
            self.train_test["starting_block_index"] == 79,
            ["replication_id", "train_id"],
        ].drop_duplicates()

        # Merge station_test with short_turning_trips
        self.station_test = pd.merge(
            self.station_test,
            short_turning_trips,
            how="left",
            on=["replication_id", "train_id"],
        )
        self.station_test["is_short_turning"] = self.station_test["train_id"].notna()

        # Filter station_test for selected stations and short-turning
        self.station_test_filtered = self.station_test.loc[
            (self.station_test["station_name"].isin(["Forest Park", "UIC-Halsted"]))
            & (
                (self.station_test["station_name"] != "UIC-Halsted")
                | (self.station_test["is_short_turning"])
            )
        ]

    def calculate_statistics(self):
        # Forest Park
        self.real_headway_fp = self.cleaned_events_filtered.loc[
            self.cleaned_events_filtered["station"] == "Forest Park", "headway"
        ]
        self.sim_headway_forest_park = self.station_test_filtered.loc[
            self.station_test_filtered["station_name"] == "Forest Park",
            "headway",
        ]

        # UIC-Halsted
        self.real_headway_uic_halsted = self.cleaned_events_filtered.loc[
            self.cleaned_events_filtered["station"] == "UIC-Halsted", "headway"
        ]
        self.sim_headway_uic_halsted = self.station_test_filtered.loc[
            (self.station_test_filtered["station_name"] == "UIC-Halsted")
            & (self.station_test_filtered["is_short_turning"]),
            "headway",
        ]

        # Filter outliers
        self.real_headway_fp = self.filter_outliers(self.real_headway_fp)
        self.real_headway_uic_halsted = self.filter_outliers(
            self.real_headway_uic_halsted
        )

    def filter_outliers(self, series, lower_quantile=0.05, upper_quantile=0.95):
        return series[
            (series >= series.quantile(lower_quantile))
            & (series <= series.quantile(upper_quantile))
        ]

    def plot_histogram(self, real_headway, sim_headway, station_name):
        # Create histograms
        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=real_headway,
                histnorm="percent",
                nbinsx=50,
                name=f"Real-life ({station_name})",
                marker=dict(color="blue"),
            )
        )
        fig.add_trace(
            go.Histogram(
                x=sim_headway,
                histnorm="percent",
                nbinsx=50,
                name=f"Simulation ({station_name})",
                marker=dict(color="red"),
            )
        )

        fig.update_layout(
            title_text=f"Histograms of Headways at {station_name}",
            xaxis_title="Headway (min)",
            yaxis_title="Percent",
            bargap=0.1,
            bargroupgap=0.2,
            legend=dict(
                x=1,  # x and y are in normalized coordinates (between 0 and 1)
                y=1,
                xanchor="auto",  # the anchor for x is automatically computed
                yanchor="auto",  # the anchor for y is automatically computed
                orientation="h",  # horizontal
                bgcolor="rgba(0,0,0,0)",  # transparent background
                bordercolor="Black",
                borderwidth=2,
            ),
        )

        return fig
