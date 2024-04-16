import unittest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import entropy


class TestHistogram(unittest.TestCase):
    def test_headways(self):
        # Load datasets
        train_test = pd.read_csv("test/output_files/train_test.csv")
        station_test = pd.read_csv("test/output_files/station_test.csv")
        cleaned_events = pd.read_csv("data/emprical_schedule/cleaned_events.csv")

        # Filter cleaned_events for selected stations and short-turning
        cleaned_events["event_time"] = pd.to_datetime(cleaned_events["event_time"])
        mask = (
            (cleaned_events["station"].isin(["LV Forest Park", "UIC-Halsted"]))
            & (
                (cleaned_events["event_time"].dt.time >= pd.to_datetime("07:00:00").time())
                & (cleaned_events["event_time"].dt.time <= pd.to_datetime("11:00:00").time())
            )
            & (
                (cleaned_events["station"] != "UIC-Halsted")
                | (cleaned_events["is_short_turning"] == 1.0)
            )
        )
        cleaned_events_filtered = cleaned_events.loc[mask]

        # Determine short-turning trips
        short_turning_trips = train_test.loc[
            train_test["starting_block_index"] == 79, ["replication_id", "train_id"]
        ].drop_duplicates()

        # Merge station_test with short_turning_trips
        station_test = pd.merge(
            station_test, short_turning_trips, how="left", on=["replication_id", "train_id"]
        )
        station_test["is_short_turning"] = station_test["train_id"].notna()

        # Filter station_test for selected stations
        station_test_filtered = station_test.loc[
            station_test["station_name"].isin(["Forest Park", "UIC-Halsted"])
        ]

        # Convert headway from seconds to minutes
        station_test_filtered["headway"] = station_test_filtered["headway"] / 60

        # Create histograms
        fig = make_subplots(rows=2, cols=1)

        # Forest Park
        real_headway_fp = cleaned_events_filtered.loc[
            cleaned_events_filtered["station"] == "LV Forest Park", "headway"
        ]
        sim_headway_forest_park = station_test_filtered.loc[
            station_test_filtered["station_name"] == "Forest Park",
            "headway",
        ]

        fig.add_trace(
            go.Histogram(
                x=real_headway_fp,
                histnorm="percent",
                name="Real-life (Forest Park)",
                marker=dict(color="blue"),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Histogram(
                x=sim_headway_forest_park,
                histnorm="percent",
                name="Simulation (Forest Park)",
                marker=dict(color="red"),
            ),
            row=1,
            col=1,
        )

        # UIC-Halsted
        real_headway_uic_halsted = cleaned_events_filtered.loc[
            cleaned_events_filtered["station"] == "UIC-Halsted", "headway"
        ]
        sim_headway_uic_halsted = station_test_filtered.loc[
            (station_test_filtered["station_name"] == "UIC-Halsted")
            & (station_test_filtered["is_short_turning"]),
            "headway",
        ]

        fig.add_trace(
            go.Histogram(
                x=real_headway_uic_halsted,
                histnorm="percent",
                name="Real-life (UIC-Halsted)",
                marker=dict(color="blue"),
            ),
            row=2,
            col=1,
        )

        fig.add_trace(
            go.Histogram(
                x=sim_headway_uic_halsted,
                histnorm="percent",
                name="Simulation (UIC-Halsted)",
                marker=dict(color="red"),
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            height=600, width=800, title_text="Histograms of Headways", bargap=0.1, bargroupgap=0.2
        )

        # Calculate statistics and KL divergence
        for i, (real_headway, sim_headway, station) in enumerate(
            zip(
                [real_headway_fp, real_headway_uic_halsted],
                [sim_headway_forest_park, sim_headway_uic_halsted],
                ["Forest Park", "UIC-Halsted"],
            )
        ):
            # Filter outliers
            real_headway = real_headway[
                (real_headway >= real_headway.quantile(0.1))
                & (real_headway <= real_headway.quantile(0.9))
            ]

            real_mean = np.mean(real_headway)
            real_std = np.std(real_headway)
            real_cv = real_std / real_mean

            sim_mean = np.mean(sim_headway)
            sim_std = np.std(sim_headway)
            sim_cv = sim_std / sim_mean

            real_hist, _ = np.histogram(real_headway, bins=100, density=True)
            sim_hist, _ = np.histogram(sim_headway, bins=100, density=True)

            kl_divergence = entropy(real_hist, sim_hist)

            # Assert that headways are non-negative
            self.assertTrue(all(headway >= 0 for headway in real_headway))
            self.assertTrue(all(headway >= 0 for headway in sim_headway))

            # Assert that mean and std are non-negative
            self.assertTrue(real_mean >= 0 and real_std >= 0 and sim_mean >= 0 and sim_std >= 0)

            annotations = [
                f"Real mean: {real_mean:.2f}",
                f"Sim mean: {sim_mean:.2f}",
                f"Real std: {real_std:.2f}",
                f"Sim std: {sim_std:.2f}",
                f"Real CV: {real_cv:.2f}",
                f"Sim CV: {sim_cv:.2f}",
                f"KL Divergence: {kl_divergence:.2f}",
            ]

            annotation_x = [0.5] * len(annotations)  # position annotations in the middle
            annotation_y = np.linspace(
                0, 1, len(annotations)
            )  # distribute annotations evenly along y

            for annotation, x, y in zip(annotations, annotation_x, annotation_y):
                fig.add_annotation(
                    x=x,
                    y=y,
                    text=annotation,
                    showarrow=False,
                    xref=f"x{i+1}",
                    yref=f"paper",
                    font=dict(size=10),
                )

        fig.show()
