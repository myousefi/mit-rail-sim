from typing import List

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import plotly.io as pio
from dash.dependencies import Input, Output

pio.templates["sophisticated"] = go.layout.Template(
    layout=go.Layout(colorway=["#91393D", "#DEDC83", "#DE6D72", "#57ADDE", "#407491"])
)
pio.templates.default = "sophisticated"


def get_color(index: int) -> str:
    """Get a color from the color palette based on the index."""
    color_palette = pio.templates["sophisticated"].layout.colorway
    return color_palette[index % len(color_palette)]


def visualize_time_profile_from_logs(
    data: pd.DataFrame,
    train_ids: List[str],
    profile_column: str,
    title: str = "",
):
    fig = go.Figure()

    for train_id in train_ids:
        train_data = data[data["train_id"] == train_id]
        times = train_data["time_in_seconds"]
        profile = train_data[profile_column]
        train_speed_regulator_states = train_data[
            "train_speed_regulator_state"
        ].tolist()

        if True:
            state_data = train_speed_regulator_states

            # Create a list of unique states
            unique_states = list(pd.Series(state_data).unique())

            for state, group in train_data.groupby(train_speed_regulator_states):
                state_index = unique_states.index(state)

                fig.add_trace(
                    go.Scatter(
                        x=group["time_in_seconds"],
                        y=group[profile_column],
                        mode="markers",
                        name=f"{train_id}: {state}",
                        marker=dict(color=get_color(state_index)),
                        legendgroup=f"{train_id}: {state}",
                    ),
                )
        else:
            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=profile,
                    mode="markers",
                    name=f"{train_id}: {title}",
                ),
            )

    fig.update_layout(title=title, xaxis_title="Time", yaxis_title=title)
    return fig


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

train_log_file_path = "test/output_files/train_test.csv"
train_data = pd.read_csv(train_log_file_path)
train_ids = train_data["train_id"].unique().tolist()

station_log_file_path = "test/output_files/station_test.csv"
station_names = pd.read_csv(station_log_file_path)["station_name"].unique().tolist()


def calculate_travel_times(station_data: pd.DataFrame) -> pd.DataFrame:
    travel_times = []
    # create a list of unique station names
    station_names = station_data["station_name"].unique()
    for origin_name in station_names:
        for destination_name in station_names:
            # exclude cases where the origin and destination are the same
            if origin_name != destination_name:
                # filter station_data for the current origin/destination pair
                origin_data = station_data[station_data["station_name"] == origin_name]
                dest_data = station_data[
                    station_data["station_name"] == destination_name
                ]
                # calculate the travel time for each train that passes through both stations
                for train_id in set(origin_data["train_id"]).intersection(
                    set(dest_data["train_id"])
                ):
                    origin = origin_data[origin_data["train_id"] == train_id].iloc[0]
                    destination = dest_data[dest_data["train_id"] == train_id].iloc[0]
                    travel_time = (
                        destination["time_in_seconds"] - origin["time_in_seconds"]
                    )

                    if travel_time > 0:
                        travel_times.append(
                            {
                                "origin": origin_name,
                                "destination": destination_name,
                                "train_id": train_id,
                                "travel_time": travel_time,
                            }
                        )
    return pd.DataFrame(travel_times)


station_data = pd.read_csv(station_log_file_path)
travel_times_data = calculate_travel_times(station_data)

app.layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Train ID"),
                        dcc.Dropdown(
                            id="train_id_dropdown",
                            options=[
                                {"label": train_id, "value": train_id}
                                for train_id in train_ids
                            ],
                            value=train_ids[0],
                        ),
                    ]
                ),
                dbc.Col(
                    [
                        html.Label("Profile"),
                        dcc.Dropdown(
                            id="profile_dropdown",
                            options=[
                                {"label": "Speed", "value": "speed"},
                                {"label": "Acceleration", "value": "acceleration"},
                                {
                                    "label": "Distance",
                                    "value": "total_travelled_distance",
                                },
                            ],
                            value="speed",
                        ),
                    ]
                ),
            ]
        ),
        html.H2("Profile vs Time"),
        dcc.Graph(id="profile_graph"),
        html.H2("Profile vs Distance"),
        dcc.Graph(id="distance_profile_graph"),
        html.H2("Distances Traveled Since Start"),
        dcc.Graph(id="distances_graph"),
        dcc.Store(
            id="dummy_input", storage_type="memory"
        ),  # Add a dummy dcc.Store component
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Station"),
                        dcc.Dropdown(
                            id="station_dropdown",
                            options=[
                                {"label": station_name, "value": station_name}
                                for station_name in station_names
                            ],
                            value=station_names[0],
                        ),
                    ]
                ),
            ]
        ),
        dcc.Graph(id="headway_scatter_graph"),
        dcc.Graph(id="headway_histogram_graph"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Origin Station"),
                        dcc.Dropdown(
                            id="origin_dropdown",
                            options=[
                                {"label": station_name, "value": station_name}
                                for station_name in station_names
                            ],
                            value=station_names[0],
                        ),
                    ]
                ),
                dbc.Col(
                    [
                        html.Label("Destination Station"),
                        dcc.Dropdown(
                            id="destination_dropdown",
                            options=[
                                {"label": station_name, "value": station_name}
                                for station_name in station_names
                            ],
                            value=station_names[1],
                        ),
                    ]
                ),
            ]
        ),
        html.H2("Travel Time Histogram"),
        dcc.Graph(id="travel_time_histogram"),
    ]
)


@app.callback(
    Output("distances_graph", "figure"),
    [Input("dummy_input", "data")],  # Use the dummy_input as a trigger
)
def update_distances_graph(_):
    return visualize_time_profile_from_logs(
        train_data,
        train_ids,
        "total_travelled_distance",
        "Distances Traveled Since Start",
    )


@app.callback(
    Output("profile_graph", "figure"),
    [
        Input("train_id_dropdown", "value"),
        Input("profile_dropdown", "value"),
    ],
)
def update_graph(train_id, profile):
    if profile == "speed":
        return visualize_time_profile_from_logs(
            train_data, [train_id], profile, "Speed"
        )
    elif profile == "acceleration":
        return visualize_time_profile_from_logs(
            train_data, [train_id], profile, "Acceleration"
        )
    elif profile == "total_travelled_distance":
        return visualize_time_profile_from_logs(
            train_data, [train_id], profile, "Distance"
        )


def create_headway_scatter(data: pd.DataFrame, station_name: str) -> go.Figure:
    station_data = data[data["station_name"] == station_name]
    fig = go.Figure()

    # Headway trace
    fig.add_trace(
        go.Scatter(
            x=station_data["time_in_seconds"],
            y=station_data["headway"],
            mode="markers",
            name="Headway",
            marker=dict(color=get_color(0)),
        )
    )

    # Dwell time trace
    fig.add_trace(
        go.Scatter(
            x=station_data["time_in_seconds"],
            y=station_data["dwell_time"],
            mode="markers",
            name="Dwell Time",
            marker=dict(color=get_color(1)),
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


@app.callback(
    Output("headway_scatter_graph", "figure"),
    [Input("station_dropdown", "value")],
)
def update_headway_scatter(station_name):
    station_data = pd.read_csv(station_log_file_path)
    return create_headway_scatter(station_data, station_name)


def create_headway_histogram(data: pd.DataFrame, station_name: str) -> go.Figure:
    station_data = data[data["station_name"] == station_name]
    fig = px.histogram(
        station_data,
        x="headway",
        nbins=20,
        title=f"Histogram of Headways at {station_name}",
    )
    return fig


@app.callback(
    Output("headway_histogram_graph", "figure"),
    [Input("station_dropdown", "value")],
)
def update_headway_histogram(station_name):
    station_data = pd.read_csv(station_log_file_path)
    return create_headway_histogram(station_data, station_name)


@app.callback(
    Output("distance_profile_graph", "figure"),
    [
        Input("train_id_dropdown", "value"),
        Input("profile_dropdown", "value"),
    ],
)
def update_distance_profile_graph(train_id, profile):
    if profile == "speed":
        return visualize_distance_profile_from_logs(
            train_data, [train_id], profile, "Speed vs Distance"
        )
    elif profile == "acceleration":
        return visualize_distance_profile_from_logs(
            train_data, [train_id], profile, "Acceleration vs Distance"
        )
    elif profile == "total_travelled_distance":
        return visualize_distance_profile_from_logs(
            train_data, [train_id], profile, "Distance vs Distance"
        )


def visualize_distance_profile_from_logs(
    data: pd.DataFrame,
    train_ids: List[str],
    profile_column: str,
    title: str = "",
):
    fig = go.Figure()

    for train_id in train_ids:
        train_data = data[data["train_id"] == train_id]
        distances = train_data["total_travelled_distance"]
        profile = train_data[profile_column]
        train_speed_regulator_states = train_data[
            "train_speed_regulator_state"
        ].tolist()

        if True:
            state_data = train_speed_regulator_states

            # Create a list of unique states
            unique_states = list(pd.Series(state_data).unique())

            for state, group in train_data.groupby(train_speed_regulator_states):
                state_index = unique_states.index(state)

                fig.add_trace(
                    go.Scatter(
                        x=group["total_travelled_distance"],
                        y=group[profile_column],
                        mode="markers",
                        name=f"{train_id}: {state}",
                        marker=dict(color=get_color(state_index)),
                        legendgroup=f"{train_id}: {state}",
                    ),
                )
        else:
            fig.add_trace(
                go.Scatter(
                    x=distances,
                    y=profile,
                    mode="markers",
                    name=f"{train_id}: {title}",
                ),
            )

    fig.update_layout(title=title, xaxis_title="Distance", yaxis_title=title)
    return fig


def create_travel_time_histogram(
    travel_times_data: pd.DataFrame, origin: str, destination: str
) -> go.Figure:
    travel_times = travel_times_data[
        (travel_times_data["origin"] == origin)
        & (travel_times_data["destination"] == destination)
    ]
    fig = px.histogram(
        travel_times,
        x="travel_time",
        nbins=20,
        title=f"Histogram of Travel Times from {origin} to {destination}",
    )
    return fig


@app.callback(
    Output("travel_time_histogram", "figure"),
    [Input("origin_dropdown", "value"), Input("destination_dropdown", "value")],
)
def update_travel_time_histogram(origin, destination):
    return create_travel_time_histogram(travel_times_data, origin, destination)


if __name__ == "__main__":
    app.run_server(debug=True)
