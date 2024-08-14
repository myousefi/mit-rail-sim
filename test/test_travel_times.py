import unittest

import numpy as np
import pandas as pd
import plotly.graph_objects as go


class TestTravelTimes(unittest.TestCase):
    def setUp(self):
        # Load the real data
        self.real_data = pd.read_csv("data/emprical_schedule/events.csv")
        self.real_data["event_time"] = pd.to_datetime(self.real_data["event_time"])
        self.real_data["date"] = self.real_data["event_time"].dt.date

        # Extract the first date from the real data
        self.first_date = self.real_data["date"].min() + pd.Timedelta(days=1)

        # Load the simulated data
        self.sim_data = pd.read_csv("test/output_files/station_test.csv")
        self.sim_data["departure_time"] = pd.to_datetime(
            str(self.first_date) + "T07:00:00"
        ) + pd.to_timedelta(self.sim_data["time_in_seconds"], unit="s")

    def calculate_travel_times(self, group):
        travel_times = []
        for _, row in group.iterrows():
            if row["station"] == "LV Forest Park":
                future_ohare_entries = group[
                    (group["station"] == "AR O-Hare")
                    & (group["event_time"] > row["event_time"])
                    & (
                        group["event_time"]
                        < (row["event_time"] + pd.Timedelta(minutes=180))
                    )
                ]
                if not future_ohare_entries.empty:
                    travel_time = (
                        future_ohare_entries["event_time"].min() - row["event_time"]
                    ).total_seconds() / 60
                    departure_time = row["event_time"]
                    travel_times.append((departure_time, travel_time))
        return travel_times

    def test_travel_times(self):
        # Filter data based on station and time range
        mask = (
            (self.real_data["station"].isin(["LV Forest Park", "AR O-Hare"]))
            & (self.real_data["event_time"].dt.time >= pd.Timestamp("07:00:00").time())
            & (self.real_data["event_time"].dt.time <= pd.Timestamp("11:00:00").time())
        )
        real_data_filtered = self.real_data.loc[mask]

        # Calculate travel times for real data
        real_travel_times_lists = (
            real_data_filtered.groupby(["date", "run_id"])
            .apply(self.calculate_travel_times)
            .dropna()
        )

        real_departure_times = pd.Series(
            [tt[0] for sublist in real_travel_times_lists for tt in sublist]
        )

        # Flatten the resulting series of lists into a single series
        real_travel_times = pd.Series(
            [tt[1] for sublist in real_travel_times_lists for tt in sublist]
        )

        # Filter travel times between the 5th and 95th percentiles
        lower_bound = real_travel_times.quantile(0.05)
        upper_bound = real_travel_times.quantile(0.95)
        real_travel_times = real_travel_times[
            (real_travel_times >= lower_bound) & (real_travel_times <= upper_bound)
        ]

        # Filter simulation data for Forest Park and O'Hare
        sim_data_filtered = self.sim_data[
            self.sim_data["station_name"].isin(["Forest Park", "O-Hare"])
        ]

        # Calculate travel times for simulation data
        sim_travel_times = (
            sim_data_filtered.groupby(["replication_id", "train_id"])
            .apply(
                lambda x: (
                    (
                        x[x["station_name"] == "Forest Park"]["departure_time"].min(),
                        (
                            x[x["station_name"] == "O-Hare"]["time_in_seconds"].min()
                            - x[x["station_name"] == "Forest Park"][
                                "time_in_seconds"
                            ].max()
                        )
                        / 60,
                        x["replication_id"].unique()[0],
                    )
                )
            )
            .dropna()
        )

        # Splitting tuples for plotting
        sim_departure_times = sim_travel_times.apply(lambda x: x[0])
        sim_replication_ids = sim_travel_times.apply(lambda x: x[2])
        sim_travel_times = sim_travel_times.apply(lambda x: x[1])

        first_replication_mask = sim_replication_ids == sim_replication_ids.min()

        # Mean and Standard Deviation
        mean_real = np.mean(real_travel_times)
        std_real = np.std(real_travel_times)
        mean_sim = np.mean(sim_travel_times)
        std_sim = np.std(sim_travel_times)

        fig = go.Figure()

        # Adding histogram for real data
        fig.add_trace(
            go.Histogram(
                x=real_travel_times,
                nbinsx=50,
                name="Real",
                histnorm="probability",
                marker_color="blue",
                opacity=0.75,
            ),
        )

        # Adding histogram for simulated data
        fig.add_trace(
            go.Histogram(
                x=sim_travel_times,
                nbinsx=50,
                name="Simulation",
                histnorm="probability",
                marker_color="red",
                opacity=0.75,
            ),
        )

        # Add mean and standard deviation annotations
        fig.add_annotation(
            x=mean_real,
            y=0.6,
            xref="x",
            yref="paper",
            text=f"Real: Mean={mean_real:.2f}, Std Dev={std_real:.2f}",
            showarrow=False,
            font=dict(size=24, color="#ffffff"),  # increased font size
            bgcolor="#0000ff",
            bordercolor="#000000",
            borderwidth=2,
            opacity=0.8,
        )

        fig.add_annotation(
            x=mean_sim,
            y=0.3,
            xref="x",
            yref="paper",
            text=f"Simulation: Mean={mean_sim:.2f}, Std Dev={std_sim:.2f}",
            showarrow=False,
            font=dict(size=24, color="#ffffff"),  # increased font size
            bgcolor="#ff0000",
            bordercolor="#000000",
            borderwidth=2,
            opacity=0.8,
        )

        fig.update_layout(
            title_text="Travel Time Distributions - Real vs Simulation",
            bargap=0.1,
            bargroupgap=0.2,
            xaxis_title="Travel Time",
            yaxis_title="Probability",
        )  # gap between bars of adjacent location coordinates

        fig.show()

        # Now, filter only the data from the first date for plotting
        mask_for_first_day = real_departure_times.dt.date == self.first_date
        first_day_departure_times = real_departure_times[mask_for_first_day]
        first_day_travel_times = real_travel_times[mask_for_first_day]
        # Scatter plot for departure times vs travel times for the first day
        # For real data
        real_departure_times_timeonly = real_departure_times.dt.time

        # For simulated data
        sim_departure_times_timeonly = sim_departure_times.dt.time
        # Scatter plot for departure times vs travel times
        fig2 = go.Figure()

        fig2.add_trace(
            go.Scatter(
                x=real_departure_times_timeonly,
                y=real_travel_times,
                mode="markers",
                name="Real Data",
                marker_color="blue",
                opacity=0.75,
            )
        )

        fig2.add_trace(
            go.Scatter(
                x=sim_departure_times_timeonly,
                y=sim_travel_times,
                mode="markers",
                name="Simulation Data",
                marker_color="red",
                opacity=0.75,
            )
        )

        fig2.update_layout(
            title_text="Travel Time vs Departure Time (Aggregated across dates)",
            xaxis_title="Departure Time",
            yaxis_title="Travel Time",
        )

        fig2.show()


if __name__ == "__main__":
    unittest.main()
