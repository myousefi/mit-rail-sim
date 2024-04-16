import pandas as pd
import numpy as np
import plotly.graph_objects as go


class TravelTimeAnalysis:
    def __init__(self, real_data: pd.DataFrame, sim_data: pd.DataFrame):
        self.real_data = real_data
        self.sim_data = sim_data
        self.clean_and_prepare_data()

    def clean_and_prepare_data(self):
        self.real_data["event_time"] = pd.to_datetime(self.real_data["event_time"])
        self.real_data["date"] = self.real_data["event_time"].dt.date

    def calculate_travel_times(self, group, origin_station, destination_station):
        travel_times = []
        for _, row in group.iterrows():
            if row["station"] == origin_station:
                future_destination_entries = group[
                    (group["station"] == destination_station)
                    & (group["event_time"] > row["event_time"])
                    & (group["event_time"] < (row["event_time"] + pd.Timedelta(minutes=180)))
                ]
                if not future_destination_entries.empty:
                    travel_times.append(
                        (
                            future_destination_entries["event_time"].min() - row["event_time"]
                        ).total_seconds()
                        / 60
                    )
        return travel_times

    def filter_data(self, origin_station, destination_station):
        # Filter data based on station and time range
        mask = (
            (self.real_data["station"].isin([origin_station, destination_station]))
            & (self.real_data["event_time"].dt.time >= pd.Timestamp("07:00:00").time())
            & (self.real_data["event_time"].dt.time <= pd.Timestamp("11:00:00").time())
        )
        return self.real_data.loc[mask]

    def prepare_travel_times(self, origin_station, destination_station):
        # Calculate travel times for real data
        real_data_filtered = self.filter_data(origin_station, destination_station)
        real_travel_times_lists = (
            real_data_filtered.groupby(["date", "run_id"])
            .apply(lambda x: self.calculate_travel_times(x, origin_station, destination_station))
            .dropna()
        )

        # Flatten the resulting series of lists into a single series
        real_travel_times = pd.Series([tt for sublist in real_travel_times_lists for tt in sublist])

        # Filter travel times between the 5th and 95th percentiles
        lower_bound = real_travel_times.quantile(0.05)
        upper_bound = real_travel_times.quantile(0.95)
        real_travel_times = real_travel_times[
            (real_travel_times >= lower_bound) & (real_travel_times <= upper_bound)
        ]

        return real_travel_times

    def calculate_sim_travel_times(self, origin_station, destination_station):
        # Filter simulation data for origin and destination
        sim_data_filtered = self.sim_data[
            self.sim_data["station_name"].isin([origin_station, destination_station])
        ]

        # Calculate travel times for simulation data
        sim_travel_times = (
            sim_data_filtered.groupby(["replication_id", "train_id"])
            .apply(
                lambda x: (
                    x[x["station_name"] == destination_station]["time_in_seconds"].min()
                    - x[x["station_name"] == origin_station]["time_in_seconds"].max()
                )
                / 60
            )
            .dropna()
        )

        return sim_travel_times

    def plot_histogram(self, origin_station, destination_station):
        real_travel_times = self.prepare_travel_times(origin_station, destination_station)
        sim_travel_times = self.calculate_sim_travel_times(origin_station, destination_station)

        # Mean and Standard Deviation
        mean_real = np.mean(real_travel_times)
        std_real = np.std(real_travel_times)
        mean_sim = np.mean(sim_travel_times)
        std_sim = np.std(sim_travel_times)

        fig = go.Figure()

        # Adding histogram for real data
        # Adding histogram for real data
        fig.add_trace(
            go.Histogram(
                x=real_travel_times,
                nbinsx=50,
                name=f"Real-life ({origin_station}-{destination_station})",
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
                name=f"Simulation ({origin_station}-{destination_station})",
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
            text=f"Real: Mean={mean_real}, Std Dev={std_real}",
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
            text=f"Simulation: Mean={mean_sim}, Std Dev={std_sim}",
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
            legend=dict(
                x=1,
                y=1,
                xanchor="auto",
                yanchor="auto",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor="Black",
                borderwidth=2,
            ),
        )

        return fig
