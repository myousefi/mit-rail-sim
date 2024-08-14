from typing import Dict, List

import pandas as pd
import plotly.graph_objs as go
from plotly import express as px

from mit_rail_sim.dash_app.helpers import get_color


class PlotCreator:
    def __init__(
        self,
        train_data: pd.DataFrame,
        station_data: pd.DataFrame,
        travel_times_data: pd.DataFrame,
        passenger_data: pd.DataFrame,
        stations_dict: Dict,
    ):
        self.replication_train_data = train_data
        self.replication_station_data = station_data
        self.travel_times_data = travel_times_data
        self.replications_passenger_data = passenger_data
        self.replications_hover_texts_dict: Dict[int, Dict[str, pd.DataFrame]] = {}
        self.stations_dict = stations_dict

        self.replication_id: int

        self.replication_ids: List[int] = (
            self.replication_station_data["replication_id"].unique().tolist()
        )

        self.station_names: List[str] = list(self.stations_dict.keys())

    def _generate_hover_texts(self, replication_id: int):
        if replication_id in self.replications_hover_texts_dict:
            return self.replications_hover_texts_dict[replication_id]

        replication_train_data = self.replication_train_data.loc[
            self.replication_train_data["replication_id"] == replication_id
        ]

        unique_train_ids = replication_train_data["train_id"].unique()

        hover_texts_dict = {}
        for train_id in unique_train_ids:
            train_df = replication_train_data[
                replication_train_data["train_id"] == train_id
            ]

            # Making column title bold and adding horizontal lines
            hover_texts_dict[train_id] = train_df.apply(
                lambda row: "<br>".join(
                    [
                        f"<b>{col}:</b>{row[col]}<br>"
                        " ---------------------------------------------------------------------------------------"
                        for col in train_df.columns
                    ]
                ),
                axis=1,
            )
        self.replications_hover_texts_dict[replication_id] = hover_texts_dict

        return hover_texts_dict

    def create_scatter_trace(
        self,
        x_data: pd.Series,
        y_data: pd.Series,
        mode: str,
        name: str,
        color=None,
        text=None,
        hoverinfo=None,
        yaxis=None,
        visible=True,
        dash="solid",  # Default line style is solid
    ) -> go.Scatter:
        """
        Create a scatter trace for a Plotly plot.

        :param x_data: Data for the x-axis.
        :param y_data: Data for the y-axis.
        :param mode: Mode of the scatter plot (lines, markers, etc.).
        :param name: Name of the trace.
        :param color: Color of the trace (with optional opacity in rgba() format).
        :param text: Text to show when hovering over the trace.
        :param hoverinfo: Info to show when hovering over the trace.
        :param visible: Boolean indicating if the trace is initially visible (default is True).
        :param dash: Line style, could be 'solid', 'dash', 'dot', etc. (default is 'solid').
        :return: The scatter trace.
        """
        return go.Scatter(
            x=x_data,
            y=y_data,
            mode=mode,
            name=name,
            line=dict(
                color=color,
                dash=dash,
            )
            if color
            else None,
            text=text,
            hoverinfo=hoverinfo,
            yaxis=yaxis,
            visible=visible,
        )

    def create_layout(self, title: str, xaxis_title: str, yaxis_title: str) -> dict:
        """
        Create a layout for a Plotly plot.

        :param title: Title of the plot.
        :param xaxis_title: Title of the x-axis.
        :param yaxis_title: Title of the y-axis.
        :return: The layout.
        """
        return dict(title=title, xaxis_title=xaxis_title, yaxis_title=yaxis_title)

    def visualize_trajectories_for_all_trains(self, replication_id: int):
        replication_subset_train_data = self.replication_train_data[
            self.replication_train_data["replication_id"] == replication_id
        ]
        fig = go.Figure()

        hover_texts_dict = self._generate_hover_texts(replication_id)

        for train_id in replication_subset_train_data["train_id"].unique():
            train_data = replication_subset_train_data[
                replication_subset_train_data["train_id"] == train_id
            ]
            times = train_data["time_in_seconds"]
            positions = train_data["location_from_terminal"]

            # fig.add_trace(
            # self.create_scatter_trace(
            #     times,
            #     positions,
            #     "lines",
            #     f"{train_id}",
            #     text=hover_texts_dict[train_id],
            #     hoverinfo="text",
            # )
            # )

            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=positions,
                    mode="lines",
                    name=f"{train_id}",
                    text=hover_texts_dict[train_id],
                    hoverinfo="text",
                )
            )

        for station_name, station_distance in self.stations_dict.items():
            fig.add_shape(
                type="line",
                x0=0,
                y0=station_distance,
                x1=1,
                y1=station_distance,
                xref="paper",
                line=dict(
                    color="DarkGrey",
                    width=1,
                    dash="dot",
                ),
            )
            fig.add_annotation(
                x=0,
                y=station_distance,
                xref="paper",
                text=station_name,
                # text="Station",
                showarrow=False,
                font=dict(
                    size=10,
                    color="Black",
                ),
                align="left",
                xanchor="left",
                yanchor="middle",
                textangle=0,
            )

        fig.update_layout(
            self.create_layout("Trajectories", "Time (sec)", "Position (ft)"),
        )
        return fig

    def visualize_time_profile_from_logs(
        self,
        replication_id: int,
        train_ids: List[str],
        profile_column: str,
        title: str = "",
    ):
        replication_subset_train_data = self.replication_train_data[
            self.replication_train_data["replication_id"] == replication_id
        ]

        replication_subset_station_data = self.replication_station_data[
            self.replication_station_data["replication_id"] == replication_id
        ]

        hover_texts_dict = self._generate_hover_texts(replication_id)

        fig = go.Figure()

        for train_id in train_ids:
            train_data = replication_subset_train_data[
                replication_subset_train_data["train_id"] == train_id
            ]
            times = train_data["time_in_seconds"]
            profile = train_data[profile_column]
            hover_text = hover_texts_dict[train_id]

            fig.add_trace(
                self.create_scatter_trace(
                    times,
                    profile,
                    "lines",
                    f"{train_id}: {title}",
                    text=hover_text,
                    hoverinfo="text",
                )
            )

            received_speed_code = train_data["train_received_speed_code"]
            fig.add_trace(
                self.create_scatter_trace(
                    times,
                    received_speed_code,
                    "lines",
                    f"{train_id}: Received Speed Code",
                    color="rgba(0, 255, 0, 0.8)",  # Pastel mint color with 80% opacity
                    hoverinfo="y",
                    visible="legendonly",
                    dash="dash",
                )
            )

            block_speed_limit = train_data["current_block_speed_limit"]
            fig.add_trace(
                self.create_scatter_trace(
                    times,
                    block_speed_limit,
                    "lines",
                    f"{train_id}: Block Speed Limit",
                    color="rgba(0,0,255, 0.8)",  # Pastel blue color with 80% opacity
                    hoverinfo="y",
                    visible="legendonly",
                    dash="dash",
                )
            )

            reduced_speed_due_to_slow_zone = train_data[
                "current_block_reduced_speed_due_to_slow_zone"
            ]
            fig.add_trace(
                self.create_scatter_trace(
                    times,
                    reduced_speed_due_to_slow_zone,
                    "lines",
                    f"{train_id}: Reduced Speed (Slow Zone)",
                    color="rgba(255,0,0,0.8)",  # Pastel red color with 80% opacity
                    hoverinfo="y",
                    visible="legendonly",
                    dash="dash",
                )
            )

            if replication_subset_station_data is not None:
                station_times = replication_subset_station_data[
                    replication_subset_station_data["train_id"] == train_id
                ]["time_in_seconds"]
                station_names = replication_subset_station_data[
                    replication_subset_station_data["train_id"] == train_id
                ]["station_name"]

                for station_time, station_name in zip(station_times, station_names):
                    fig.add_shape(
                        type="line",
                        x0=station_time,
                        y0=0,
                        x1=station_time,
                        y1=1,
                        yref="paper",
                        line=dict(
                            color="DarkGrey",
                            width=1,
                            dash="dot",
                        ),
                    )
                    fig.add_annotation(
                        x=station_time,
                        y=1,
                        yref="paper",
                        text=station_name,
                        showarrow=False,
                        font=dict(
                            size=10,
                            color="Black",
                        ),
                        align="center",
                        xanchor="center",
                        yanchor="top",
                        textangle=-90,
                    )

        # yaxis_title =
        unit_dict = {"Acceleration": "mph/s", "Speed": "mph", "Distance": "ft"}
        fig.update_layout(
            **self.create_layout(
                f"{title} vs Time", "Time (sec)", f"{title} ({unit_dict.get(title)})"
            )
        )
        return fig

    def create_headway_scatter(
        self, replication_id: int, station_name: str
    ) -> go.Figure:
        replication_subset_station_data = self.replication_station_data[
            self.replication_station_data["replication_id"] == replication_id
        ]

        station_data = replication_subset_station_data[
            replication_subset_station_data["station_name"] == station_name
        ]
        fig = go.Figure()

        fig.add_trace(
            self.create_scatter_trace(
                station_data["time_in_seconds"],
                station_data["headway"],
                "markers",
                "Headway",
                get_color(0),
            )
        )

        fig.add_trace(
            self.create_scatter_trace(
                station_data["time_in_seconds"],
                station_data["dwell_time"],
                "markers",
                "Dwell Time",
                get_color(1),
                yaxis="y2",
            )
        )

        fig.update_layout(
            title=f"Headways and Dwell Times at {station_name}",
            xaxis_title="Time",
            yaxis_title="Headway",
            yaxis2=dict(
                title="Dwell Time",
                overlaying="y",
                side="right",
            ),
        )

        return fig

    def create_headway_histogram(self, station_name: str, direction: str) -> go.Figure:
        station_data = (
            self.replication_station_data[
                (self.replication_station_data["station_name"] == station_name)
                & (self.replication_station_data["direction"] == direction)
            ]["headway"]
            / 60
        )  # Convert to minutes

        mean_headway = station_data.mean()
        std_dev_headway = station_data.std()
        coeff_var_headway = std_dev_headway / mean_headway

        fig = px.histogram(
            station_data,
            histnorm="percent",
            x="headway",
            nbins=50,
            title=f"Histogram of Headways at {station_name} ({direction})",
            # hover_data=station_data.columns,
        )

        fig.add_annotation(
            x=0.95,
            y=0.95,
            text=(
                f"<b>Mean:</b> {mean_headway:.2f} min<br>"
                f"<b>Std Dev:</b> {std_dev_headway:.2f} min<br>"
                f"<b>CV:</b> {coeff_var_headway:.2f}"
            ),
            showarrow=False,
            font=dict(size=12, color="black"),
            align="left",
            ax=20,
            ay=-30,
            bordercolor="#c7c7c7",
            borderwidth=2,
            borderpad=4,
            bgcolor="white",
            opacity=0.8,
            xref="paper",
            yref="paper",
        )

        fig.update_layout(
            xaxis_title="Headway (min)",
            yaxis_title="Percent",
        )

        return fig

    def visualize_distance_profile_from_logs(
        self,
        replication_id: int,
        train_ids: List[str],
        profile_column: str,
        title: str = "",
    ):
        replication_subset_train_data = self.replication_train_data[
            self.replication_train_data["replication_id"] == replication_id
        ]

        fig = go.Figure()

        hover_texts_dict = self._generate_hover_texts(replication_id)

        for train_id in train_ids:
            train_data = replication_subset_train_data[
                replication_subset_train_data["train_id"] == train_id
            ]
            distances = train_data["location_from_terminal"]
            profile = train_data[profile_column]
            hover_text = hover_texts_dict[train_id]

            fig.add_trace(
                self.create_scatter_trace(
                    distances,
                    profile,
                    "lines",
                    f"{train_id}: {title}",
                    text=hover_text,
                    hoverinfo="text",
                )
            )

            received_speed_code = train_data["train_received_speed_code"]
            fig.add_trace(
                self.create_scatter_trace(
                    distances,
                    received_speed_code,
                    "lines",
                    f"{train_id}: Received Speed Code",
                    color="rgba(0, 255, 0, 0.8)",  # Pastel mint color with 80% opacity
                    hoverinfo="y",
                    visible="legendonly",
                    dash="dash",
                )
            )

            block_speed_limit = train_data["current_block_speed_limit"]
            fig.add_trace(
                self.create_scatter_trace(
                    distances,
                    block_speed_limit,
                    "lines",
                    f"{train_id}: Block Speed Limit",
                    color="rgba(0,0,255, 0.8)",  # Pastel blue color with 80% opacity
                    hoverinfo="y",
                    visible="legendonly",
                    dash="dash",
                )
            )

            reduced_speed_due_to_slow_zone = train_data[
                "current_block_reduced_speed_due_to_slow_zone"
            ]
            fig.add_trace(
                self.create_scatter_trace(
                    distances,
                    reduced_speed_due_to_slow_zone,
                    "lines",
                    f"{train_id}: Reduced Speed (Slow Zone)",
                    color="rgba(255,0,0,0.8)",  # Pastel red color with 80% opacity
                    hoverinfo="y",
                    visible="legendonly",
                    dash="dash",
                )
            )

        for station_name, station_distance in self.stations_dict.items():
            fig.add_shape(
                type="line",
                x0=station_distance,
                y0=0,
                x1=station_distance,
                y1=1,
                yref="paper",
                line=dict(
                    color="DarkGrey",
                    width=1,
                    dash="dot",
                ),
            )
            fig.add_annotation(
                x=station_distance,
                y=1,
                yref="paper",
                text=station_name,
                # text="Station",
                showarrow=False,
                font=dict(
                    size=10,
                    color="Black",
                ),
                align="center",
                xanchor="center",
                yanchor="top",
                textangle=-90,
            )
        unit_dict = {"Acceleration": "mph/s", "Speed": "mph", "Distance": "ft"}

        fig.update_layout(
            **self.create_layout(
                f"{title} vs Distance",
                "Distance (ft)",
                f"{title} ({unit_dict.get(title)})",
            )
        )

        return fig

    def create_travel_time_histogram(self, origin: str, destination: str) -> go.Figure:
        travel_times = (
            self.travel_times_data[
                (self.travel_times_data["origin"] == origin)
                & (self.travel_times_data["destination"] == destination)
            ]["travel_time"]
            / 60
        )  # Convert to minutes

        mean_travel_time = travel_times.mean()
        std_dev_travel_time = travel_times.std()
        coeff_var_travel_time = std_dev_travel_time / mean_travel_time

        fig = px.histogram(
            travel_times,
            histnorm="percent",
            x="travel_time",
            nbins=50,
            title=f"Histogram of Travel Times from {origin} to {destination}",
        )

        fig.add_annotation(
            x=0.95,
            y=0.95,
            text=(
                f"<b>Mean:</b> {mean_travel_time:.2f} min<br>"
                f"<b>Std Dev:</b> {std_dev_travel_time:.2f} min<br>"
                f"<b>CV:</b> {coeff_var_travel_time:.2f}"
            ),
            showarrow=False,
            font=dict(size=12, color="black"),
            align="left",  # Align the text to the left
            ax=20,
            ay=-30,
            bordercolor="#c7c7c7",
            borderwidth=2,
            borderpad=4,
            bgcolor="white",
            opacity=0.8,
            xref="paper",
            yref="paper",
        )

        fig.update_layout(
            xaxis_title="Travel Time (min)",
            yaxis_title="Percent",
        )

        return fig

    def create_average_waiting_time_figure(self) -> go.Figure:
        station_names = list(self.stations_dict.keys())
        df = self.replications_passenger_data[
            self.replications_passenger_data["origin"].isin(station_names)
        ]

        df["waiting_time"] = df["waiting_time"] / 60
        # Sort the dataframe by station names according to the given list
        df["origin"] = pd.Categorical(
            df["origin"], categories=station_names, ordered=True
        )
        df.sort_values("origin", inplace=True)

        data = []
        for direction in ["Northbound", "Southbound"]:
            # _df = df[df["direction"] == direction]
            group = df[df["direction"] == direction].groupby("origin", sort=False)[
                "waiting_time"
            ]
            # Calculate means, 25% and 75% percentiles
            means = group.mean()
            lower_bounds = group.quantile(0.25)
            upper_bounds = group.quantile(0.75)

            data.append(
                go.Scatter(
                    x=means.index,
                    y=means,
                    mode="lines+markers",
                    name=f"Average Waiting Time ({direction})",
                    error_y=dict(
                        type="data",  # value of error bar given in data coordinates
                        array=upper_bounds - means,
                        arrayminus=means - lower_bounds,
                        visible=True,
                    ),
                )
            )

        fig = go.Figure(data=data)

        fig.update_layout(
            title="Average Waiting Time with Quartiles",
            xaxis_title="Station",
            yaxis_title="Average Waiting Time (min)",
        )
        return fig

    # def create_reliability_buffer_time_figure(self) -> go.Figure:
    #     # Read the data from your file
    #     df = self.replications_passenger_data

    #     # Add a new column "journey_time" which is the sum of "waiting_time" and "travel_time"
    #     df["journey_time"] = df["waiting_time"] + df["travel_time"]

    #     # Group by "origin" and "destination", and calculate the 90th and 50th percentiles of "journey_time"
    #     percentiles = (
    #         df.groupby(["origin", "destination"]).journey_time.quantile([0.90, 0.50]).unstack()
    #     )

    #     # Calculate the reliability buffer time (the difference between the 90th percentile and 50th percentile)
    #     percentiles["reliability_buffer_time"] = percentiles[0.90] - percentiles[0.50]

    #     # Generate the reliability buffer time heatmap
    #     reliability_buffer_times = percentiles["reliability_buffer_time"].unstack()
    #     figure = px.imshow(
    #         reliability_buffer_times,
    #         labels=dict(x="Destination", y="Origin", color="Reliability Buffer Time"),
    #         title="Reliability Buffer Time Heatmap",
    #         color_continuous_scale="viridis",
    #     )
    #     return figure
    def create_reliability_buffer_time_figure(self) -> go.Figure:
        # Read the data from your file
        df = self.replications_passenger_data

        # Add a new column "journey_time" which is the sum of "waiting_time" and "travel_time"
        df["journey_time"] = df["waiting_time"] + df["travel_time"]

        # Group by "origin" and "destination", and calculate the 90th and 50th percentiles of "journey_time"
        percentiles = (
            df.groupby(["origin", "destination"])
            .journey_time.quantile([0.90, 0.50])
            .unstack()
        )

        # Calculate the reliability buffer time (the difference between the 90th percentile and 50th percentile)
        percentiles["reliability_buffer_time"] = percentiles[0.90] - percentiles[0.50]

        # Generate the reliability buffer time heatmap
        reliability_buffer_times = percentiles["reliability_buffer_time"].unstack()

        # Ensure all stations are in the DataFrame
        # stations = list(df["origin"].unique()) + list(df["destination"].unique())
        # stations = list(set(stations))
        reliability_buffer_times = reliability_buffer_times.reindex(
            index=self.station_names, columns=self.station_names
        )

        heatmap = go.Heatmap(
            z=reliability_buffer_times.values,
            x=reliability_buffer_times.columns,
            y=reliability_buffer_times.index,
            colorscale="Blues",
            hovertemplate=(
                "<b>Origin</b>: %{y}<br>"
                + "<b>Destination</b>: %{x}<br>"
                + "<b>Reliability Buffer Time</b>: %{z}<extra></extra>"
            ),
        )

        fig = go.Figure(data=heatmap)

        fig.update_layout(
            title="Reliability Buffer Time Heatmap",
            xaxis_title="Destination",
            yaxis_title="Origin",
            xaxis_nticks=36,
        )

        return fig
