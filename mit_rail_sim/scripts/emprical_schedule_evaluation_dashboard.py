import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash
from scipy.stats import entropy


class HeadwayAnalysis:
    def __init__(self, cleaned_events_path, train_test_path, station_test_path):
        self.cleaned_events_path = cleaned_events_path
        self.train_test_path = train_test_path
        self.station_test_path = station_test_path

    def load_and_clean_data(self):
        # Load datasets
        self.train_test = pd.read_csv(self.train_test_path)
        self.station_test = pd.read_csv(self.station_test_path)
        self.cleaned_events = pd.read_csv(self.cleaned_events_path)

        # Clean cleaned_events data
        self.cleaned_events["event_time"] = pd.to_datetime(self.cleaned_events["event_time"])
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
                (self.cleaned_events["event_time"].dt.time >= pd.to_datetime("07:00:00").time())
                & (self.cleaned_events["event_time"].dt.time <= pd.to_datetime("11:00:00").time())
            )
            & (
                (self.cleaned_events["station"] != "UIC-Halsted")
                | (self.cleaned_events["is_short_turning"] == 1.0)
            )
        )
        self.cleaned_events_filtered = self.cleaned_events.loc[mask]

        # Determine short-turning trips
        short_turning_trips = self.train_test.loc[
            self.train_test["starting_block_index"] == 79, ["replication_id", "train_id"]
        ].drop_duplicates()

        # Merge station_test with short_turning_trips
        self.station_test = pd.merge(
            self.station_test, short_turning_trips, how="left", on=["replication_id", "train_id"]
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
        self.real_headway_uic_halsted = self.filter_outliers(self.real_headway_uic_halsted)

    def filter_outliers(self, series, lower_quantile=0.1, upper_quantile=0.9):
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
                name=f"Real-life ({station_name})",
                marker=dict(color="blue"),
            )
        )
        fig.add_trace(
            go.Histogram(
                x=sim_headway,
                histnorm="percent",
                name=f"Simulation ({station_name})",
                marker=dict(color="red"),
            )
        )

        fig.update_layout(
            title_text=f"Histograms of Headways at {station_name}",
            bargap=0.1,
            bargroupgap=0.2,
        )

        return fig


# Initialize and prepare data
analysis = HeadwayAnalysis(
    "data/emprical_schedule/cleaned_events.csv",
    "test/output_files/train_test.csv",
    "test/output_files/station_test.csv",
)
analysis.load_and_clean_data()
analysis.filter_and_prepare_data()
analysis.calculate_statistics()

# Create dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
# Inside the layout:
# Inside the layout:

app.layout = dbc.Container(
    [
        dbc.Col(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="forest_park_graph",
                                figure=analysis.plot_histogram(
                                    analysis.real_headway_fp,
                                    analysis.sim_headway_forest_park,
                                    "Forest Park",
                                ),
                            )
                        ),
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader("Statistics"),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                "Mean (real):"
                                                f" {np.mean(analysis.real_headway_fp):.2f} minutes"
                                            ),
                                            html.P(
                                                "Mean (simulated):"
                                                f" {np.mean(analysis.sim_headway_forest_park):.2f} minutes"
                                            ),
                                            html.P(
                                                "Standard deviation (real):"
                                                f" {np.std(analysis.real_headway_fp):.2f} minutes"
                                            ),
                                            html.P(
                                                "Standard deviation (simulated):"
                                                f" {np.std(analysis.sim_headway_forest_park):.2f} minutes"
                                            ),
                                            html.P(
                                                "Coefficient of variation (real):"
                                                f" {np.std(analysis.real_headway_fp)/np.mean(analysis.real_headway_fp):.2f}"
                                            ),
                                            html.P(
                                                "Coefficient of variation (simulated):"
                                                f" {np.std(analysis.sim_headway_forest_park)/np.mean(analysis.sim_headway_forest_park):.2f}"
                                            ),
                                            # Add more statistics here
                                        ]
                                    ),
                                ]
                            ),
                            width=3,
                        ),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="uic_halsted_graph",
                                figure=analysis.plot_histogram(
                                    analysis.real_headway_uic_halsted,
                                    analysis.sim_headway_uic_halsted,
                                    "UIC-Halsted",
                                ),
                            )
                        ),
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader("Statistics"),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                "Mean (real):"
                                                f" {np.mean(analysis.real_headway_uic_halsted):.2f} minutes"
                                            ),
                                            html.P(
                                                "Mean (simulated):"
                                                f" {np.mean(analysis.sim_headway_uic_halsted):.2f} minutes"
                                            ),
                                            html.P(
                                                "Standard deviation (real):"
                                                f" {np.std(analysis.real_headway_uic_halsted):.2f} minutes"
                                            ),
                                            html.P(
                                                "Standard deviation (simulated):"
                                                f" {np.std(analysis.sim_headway_uic_halsted):.2f} minutes"
                                            ),
                                            html.P(
                                                "Coefficient of variation (real):"
                                                f" {np.std(analysis.real_headway_uic_halsted) / np.mean(analysis.real_headway_uic_halsted):.2f}"
                                            ),
                                            html.P(
                                                "Coefficient of variation (simulated):"
                                                f" {np.std(analysis.sim_headway_uic_halsted) / np.mean(analysis.sim_headway_uic_halsted):.2f}"
                                            ),
                                            # Add more statistics here
                                        ]
                                    ),
                                ]
                            ),
                            width=3,
                        ),
                    ]
                ),
            ]
        ),
    ],
    fluid=True,
)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
