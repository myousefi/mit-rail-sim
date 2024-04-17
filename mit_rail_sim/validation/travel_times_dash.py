from datetime import datetime, time

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
from pandas.tseries.holiday import USFederalHolidayCalendar

from mit_rail_sim.utils import find_free_port, project_root

# Constants
STATION_ORDER = [
    "Forest Park",
    "Harlem (Forest Park Branch)",
    "Oak Park",
    "Austin",
    "Cicero",
    "Pulaski",
    "Kedzie-Homan",
    "Western (Forest Park Branch)",
    "Illinois Medical District",
    "Racine",
    "UIC-Halsted",
    "Clinton",
    "LaSalle",
    "Jackson",
    "Monroe",
    "Washington",
    "Clark/Lake",
    "Grand",
    "Chicago",
    "Division",
    "Damen",
    "Western (O-Hare Branch)",
    "California",
    "Logan Square",
    "Belmont",
    "Addison",
    "Irving Park",
    "Montrose",
    "Jefferson Park",
    "Harlem (O-Hare Branch)",
    "Cumberland",
    "Rosemont",
    "O-Hare",
]

STATION_BLOCK = {
    "Forest Park": "wc461t",
    "Harlem (Forest Park Branch)": "wc444t",
    "Oak Park": "wc401t",
    "Austin": "wc361t",
    "Cicero": "wc279t",
    "Pulaski": "wc225t",
    "Kedzie-Homan": "wc172t",
    "Western (Forest Park Branch)": "wc117t",
    "Illinois Medical District": "wc075t",
    "Racine": "wc035t",
    "UIC-Halsted": "wc008t",
    "Clinton": "dc014t",
    "LaSalle": "dc036t",
    "Jackson": "dc056t",
    "Monroe": "dc066t",
    "Washington": "dc075t",
    "Clark/Lake": "dc088t",
    "Grand": "dc138t",
    "Chicago": "dc164t",
    "Division": "dc210t",
    "Damen": "ln1232t",
    "Western (O-Hare Branch)": "ln1269t",
    "California": "ln1301t",
    "Logan Square": "nwc110t",
    "Belmont": "nwc146t",
    "Addison": "nwc185t",
    "Irving Park": "nwc218t",
    "Montrose": "nwc270t",
    "Jefferson Park": "nwc325t",
    "Harlem (O-Hare Branch)": "nwc468t",
    "Cumberland": "nwc547t",
    "Rosemont": "nwc606t",
    "O-Hare": "nwc724t",
}

RUN_TIME_BLOCKS = {
    "Forest Park": ("wc461t", "wc444t"),
    "Harlem (Forest Park Branch)": ("wc434", "wc401t"),
    "Oak Park": ("wc387t", "wc361t"),
    "Austin": ("wc350t", "wc279t"),
    "Cicero": ("wc266t", "wc225t"),
    "Pulaski": ("wc216", "wc172t"),
    "Kedzie-Homan": ("wc162", "wc117t"),
    "Western (Forest Park Branch)": ("wc108", "wc075t"),
    "Illinois Medical District": ("wc063t", "wc035t"),
    "Racine": ("wc030", "wc008t"),
    "UIC-Halsted": ("wc003t", "dc014t"),
    "Clinton": ("dc023t", "dc036t"),
    "LaSalle": ("dc044t", "dc056t"),
    "Jackson": ("dc061t", "dc066t"),
    "Monroe": ("dc072t", "dc075t"),
    "Washington": ("dc082t", "dc088t"),
    "Clark/Lake": ("dc099t", "dc138t"),
    "Grand": ("dc145t", "dc164t"),
    "Chicago": ("dc171t", "dc210t"),
    "Division": ("dc215t", "ln1232t"),
    "Damen": ("ln1240t", "ln1269t"),
    "Western (O-Hare Branch)": ("ln1273", "ln1301t"),
    "California": ("ln1310t", "nwc110t"),
    "Logan Square": ("nwc118t", "nwc146t"),
    "Belmont": ("nwc154t", "nwc185t"),
    "Addison": ("nwc189", "nwc218t"),
    "Irving Park": ("nwc225t", "nwc270t"),
    "Montrose": ("nwc278t", "nwc325t"),
    "Jefferson Park": ("nwc332t", "nwc468t"),
    "Harlem (O-Hare Branch)": ("nwc486t", "nwc547t"),
    "Cumberland": ("nwc561t", "nwc606t"),
    "Rosemont": ("nwc615t", "nwc724t"),
    "O-Hare": (None, None),
}


# Utility Functions
def filter_by_time_and_weekday(df, start_time, end_time):
    return df[
        (df["event_datetime"].dt.time >= start_time)
        & (df["event_datetime"].dt.time <= end_time)
        & (df["weekday"] < 5)
    ].copy()


def remove_holidays(df):
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=df["event_datetime"].min(), end=df["event_datetime"].max())
    return df[~df["event_datetime"].dt.date.isin(holidays)].copy()


# Dash App
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Travel Times"
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Select Start Station"),
                        dcc.Dropdown(
                            id="start-station-dropdown",
                            options=[
                                {"label": station, "value": station} for station in STATION_ORDER
                            ],
                            value=STATION_ORDER[0],
                        ),
                    ]
                ),
                dbc.Col(
                    [
                        html.Label("Select End Station"),
                        dcc.Dropdown(
                            id="end-station-dropdown",
                            options=[
                                {"label": station, "value": station} for station in STATION_ORDER
                            ],
                            value=STATION_ORDER[-1],
                        ),
                    ]
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="travel-time-scatter")),
            ]
        ),
    ],
    fluid=True,
)


@app.callback(
    Output("travel-time-scatter", "figure"),
    [Input("start-station-dropdown", "value"), Input("end-station-dropdown", "value")],
)
def update_travel_time_scatter(start_station, end_station):
    df = (
        pd.concat(
            [
                calculate_real_travel_times(merged_data, merged_data, start_station, end_station),
                calculate_sim_travel_times(
                    simulation_results, simulation_results, start_station, end_station
                ),
            ],
            keys=["real", "sim"],
        )
        .reset_index(level=0)
        .rename(columns={"level_0": "source"})
    )

    fig = px.scatter(df, x="dispatch_time", y="duration", color="source")

    fig.update_layout(
        title="Travel Times from {} to {}".format(start_station, end_station),
        xaxis_title="Dispatch Time",
        yaxis_title="Travel Time (min)",
        legend_title="Data Source",
    )

    return fig


def calculate_real_travel_times(df, dest_df, origin_station, destination_station):
    # Sort df by 'event_time' for merge_asof to work
    df = df[["date", "run_id", "event_time", "event_datetime", "station"]].copy()
    df = df.sort_values("event_time")

    dest_df = dest_df[["date", "run_id", "event_time", "event_datetime", "station"]].copy()
    dest_df = dest_df.sort_values("event_time")

    # Separate origin and destination stations
    origin_df = df[df["station"] == origin_station].copy()
    destination_df = dest_df[dest_df["station"] == destination_station].copy()

    # Create a column to store the maximum possible time for a valid trip
    origin_df["max_time"] = origin_df["event_time"] + pd.Timedelta(minutes=180)
    # Merge_asof to find closest matching destination row for each origin row
    merged_df = pd.merge_asof(
        origin_df,
        destination_df,
        by=["date", "run_id"],
        left_on="event_datetime",
        right_on="event_datetime",
        direction="forward",
        suffixes=("_origin", "_destination"),
    )
    # Filter rows where destination event_time is within the valid trip time window
    merged_df = merged_df[
        (merged_df["event_time_destination"] >= merged_df["event_time_origin"])
        & (merged_df["event_time_destination"] <= merged_df["max_time"])
    ]

    # Calculate travel times
    travel_times = pd.DataFrame()

    travel_times["dispatch_time"] = (
        merged_df["event_time_origin"]
        - merged_df["event_time_origin"].dt.normalize()
        # + pd.datetime(2023, 4, 15)
        + pd.to_datetime("2023-04-15")
    )

    travel_times["duration"] = (
        (merged_df["event_time_destination"] - merged_df["event_time_origin"]).dt.total_seconds()
        / 60
    ).dropna()

    # Filter by fence method
    q1 = travel_times["duration"].quantile(0.25)
    q3 = travel_times["duration"].quantile(0.75)
    iqr = q3 - q1
    travel_times = travel_times[
        (travel_times["duration"] >= q1 - 3 * iqr) & (travel_times["duration"] <= q3 + 3 * iqr)
    ]

    return travel_times


def calculate_sim_travel_times(df, dest_df, origin_station, destination_station):
    # Sort DataFrame by necessary keys
    df = df[["replication_id", "time_in_seconds", "station_name", "train_id"]].copy()
    df = df.sort_values(by="time_in_seconds")
    df["time"] = df["time_in_seconds"]

    dest_df = dest_df[["replication_id", "time_in_seconds", "station_name", "train_id"]].copy()
    dest_df = dest_df.sort_values(by="time_in_seconds")
    dest_df["time"] = dest_df["time_in_seconds"]

    # Split DataFrame into origin and destination stations
    origin_df = df[df["station_name"] == origin_station]
    destination_df = dest_df[dest_df["station_name"] == destination_station]

    # Merge DataFrames on replication_id, train_id, and find the closest time_in_seconds
    merged_df = pd.merge_asof(
        origin_df,
        destination_df,
        by=["replication_id", "train_id"],
        on="time",
        direction="forward",
        suffixes=("_origin", "_destination"),
    )

    sim_travel_times = pd.DataFrame()

    sim_travel_times["dispatch_time"] = pd.to_datetime(
        merged_df["time_in_seconds_origin"], unit="s", origin="2023-04-15"
    )

    sim_travel_times["duration"] = (
        (merged_df["time_in_seconds_destination"] - merged_df["time_in_seconds_origin"]) / 60
    ).dropna()

    return sim_travel_times


if __name__ == "__main__":
    # Data Preparation
    merged_data = pd.read_csv("./data/track_events.csv", parse_dates=["event_time"])
    merged_data["event_datetime"] = pd.to_datetime(merged_data["event_time"])
    merged_data["weekday"] = merged_data["event_datetime"].dt.weekday
    merged_data["date"] = merged_data["event_datetime"].dt.date
    merged_data = merged_data[
        (merged_data["event_datetime"].dt.date >= datetime(2023, 4, 15).date())
        & (merged_data["event_datetime"].dt.date <= datetime(2023, 4, 25).date())
    ]

    # merged_data["event_time"] = merged_data["event_datetime"]
    merged_data.sort_values(by=["event_datetime"], inplace=True)
    track_df = merged_data.copy()
    merged_data["dwell_arrtodep"] = (
        abs(merged_data.groupby(["date", "run_id"])["event_time"].diff(-2)).dt.seconds / 60
    )

    merged_data = merged_data[merged_data["scada"].isin(STATION_BLOCK.values())]
    merged_data["station"] = merged_data["scada"].map({v: k for k, v in STATION_BLOCK.items()})

    event_delay = pd.read_csv("./data/blue_line_event_delay_drqe.csv")
    event_delay["event_datetime"] = pd.to_datetime(event_delay["event_datetime"])
    event_delay["drqbe"] = event_delay["drqbe"].str.split(" - ").str[-1]

    simulation_results = pd.read_csv("./simulation_results/station_test.csv")
    block_test = pd.read_csv("./simulation_results/block_test.csv")

    # Step 1: Add difference_in_activation column to block_test
    block_test.sort_values(by=["replication_id", "train_id", "time_in_seconds"], inplace=True)
    block_test["difference_in_activation"] = -block_test.groupby(["replication_id", "train_id"])[
        "time_in_seconds"
    ].diff(-2)

    # Create a new column in station_test dataframe to hold the corresponding block_id values
    simulation_results["block_id"] = simulation_results["station_name"].map(STATION_BLOCK)

    # Merge the dataframes on replication_id, train_id and block_id
    simulation_results = pd.merge(
        simulation_results,
        block_test,
        on=["replication_id", "train_id", "block_id"],
        how="left",
        suffixes=("_station", ""),
    )

    simulation_results.dropna(inplace=True)

    simulation_results.to_csv(
        project_root
        / "mit_rail_sim"
        / "validation"
        / "simulation_results"
        / "simulation_merged.csv",
        index=False,
    )
    print("saved")
    simulation_results["headway"] = simulation_results["headway"] / 60
    simulation_results["dwell_time"] = simulation_results["dwell_time"] / 60
    simulation_results["difference_in_activation"] = (
        simulation_results["difference_in_activation"] / 60
    )

    app.run_server(debug=True, port=find_free_port())
