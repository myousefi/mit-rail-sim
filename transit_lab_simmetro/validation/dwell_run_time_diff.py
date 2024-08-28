from datetime import datetime, time

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from pandas.tseries.holiday import USFederalHolidayCalendar

from transit_lab_simmetro.utils import find_free_port
from transit_lab_simmetro.validation.validation_dash import (
    DWELL_BLOCK,
    RUN_TIME_BLOCKS,
    STATION_BLOCK,
)


# Utility Functions
def filter_by_time_and_weekday(df, start_time, end_time):
    return df[
        (df["event_datetime"].dt.time >= start_time)
        & (df["event_datetime"].dt.time <= end_time)
        & (df["weekday"] < 5)
    ].copy()


def remove_holidays(df):
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(
        start=df["event_datetime"].min(), end=df["event_datetime"].max()
    )
    return df[~df["event_datetime"].dt.date.isin(holidays)].copy()


# Dash App
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Diff"

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Select Time Range (Start and End Time)"),
                        dcc.RangeSlider(
                            id="time-range-slider",
                            min=0,
                            max=24,
                            step=1,
                            value=[7, 11],
                            marks={i: str(i) for i in range(25)},
                        ),
                    ]
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="dwell-diff")),
                dbc.Col(dcc.Graph(id="run-time-diff")),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="dwell-diff-hist")),
                dbc.Col(dcc.Graph(id="run-time-diff-hist")),
            ]
        ),
    ],
    fluid=True,
)


@app.callback(
    [Output("dwell-diff", "figure"), Output("dwell-diff-hist", "figure")],
    Input("time-range-slider", "value"),
)
def update_dwell_diff(time_range):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    avl_all = track_df.copy()
    avl_all = remove_holidays(avl_all)
    avl_all = avl_all[avl_all["weekday"] < 5]
    filtered_df = filter_by_time_and_weekday(avl_all, start_time, end_time)

    # Filter simulation data by time and selected station
    sim_all = block_test.copy()
    sim_all["time"] = sim_all["time_in_seconds"]
    sim_all.sort_values(by=["time_in_seconds"], inplace=True)

    filtered_sim = sim_all[
        (sim_all["time_in_seconds"] >= time_range[0] * 3600)
        & (sim_all["time_in_seconds"] <= time_range[1] * 3600)
    ]

    # filtered_sim["time"] = filtered_sim["time_in_seconds"]

    run_times_dict = {}
    for station in DWELL_BLOCK.keys():
        avl = pd.merge_asof(
            left=filtered_df[filtered_df["scada"] == DWELL_BLOCK[station][0]],
            right=avl_all[avl_all["scada"] == DWELL_BLOCK[station][1]],
            by=["date", "run_id"],
            left_on="event_datetime",
            right_on="event_datetime",
            direction="forward",
            suffixes=("_origin", "_destination"),
            tolerance=pd.Timedelta(minutes=20),
        )

        sim = pd.merge_asof(
            left=filtered_sim[filtered_sim["block_id"] == DWELL_BLOCK[station][0]],
            right=sim_all[sim_all["block_id"] == DWELL_BLOCK[station][1]],
            by=["replication_id", "train_id"],
            left_on="time",
            right_on="time",
            direction="forward",
            suffixes=("_origin", "_destination"),
        )

        real_run_times = (
            avl["event_time_destination"] - avl["event_time_origin"]
        ).dt.total_seconds() / 60

        sim_run_times = (
            sim["time_in_seconds_destination"] - sim["time_in_seconds_origin"]
        ) / 60

        real_run_times.dropna(inplace=True)

        sim_run_times.dropna(inplace=True)

        run_times_dict[station] = real_run_times.mean() - sim_run_times.mean()

        # filter out outliers by fence method for each series
        q1 = real_run_times.quantile(0.25)
        q3 = real_run_times.quantile(0.75)
        iqr = q3 - q1
        lower_fence = q1 - 3 * iqr
        upper_fence = q3 + 3 * iqr
        real_run_times = real_run_times[
            (real_run_times > lower_fence) & (real_run_times < upper_fence)
        ]

    df = pd.DataFrame.from_dict(
        run_times_dict, orient="index", columns=["Dwell Time Difference"]
    )

    fig = go.Figure(
        go.Bar(
            x=df.index,
            y=df["Dwell Time Difference"],
            text=df["Dwell Time Difference"].round(2),
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Dwell Time Difference: AVL - SIM (mins)",
        xaxis_title="Station",
        yaxis_title="Dwell Time Difference (mins)",
    )

    fig2 = px.histogram(
        df,
        x="Dwell Time Difference",
        nbins=20,
        title="Dwell Time Difference: AVL - SIM (mins) ",
    )

    fig2.add_annotation(
        x=0.5,
        y=1.05,
        xref="paper",
        yref="paper",
        align="left",
        text=(
            f"Mean: {df['Dwell Time Difference'].mean()} | Std: {df['Dwell Time Difference'].std()}"
        ),
        showarrow=False,
        # arrowhead=1,
    )

    return [fig, fig2]


@app.callback(
    [Output("run-time-diff", "figure"), Output("run-time-diff-hist", "figure")],
    Input("time-range-slider", "value"),
)
def update_run_time_diff(time_range):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    avl_all = track_df.copy()
    avl_all = remove_holidays(avl_all)
    avl_all = avl_all[avl_all["weekday"] < 5]
    filtered_df = filter_by_time_and_weekday(avl_all, start_time, end_time)

    # Filter simulation data by time and selected station
    sim_all = block_test.copy()
    sim_all["time"] = sim_all["time_in_seconds"]
    sim_all.sort_values(by=["time_in_seconds"], inplace=True)

    filtered_sim = sim_all[
        (sim_all["time_in_seconds"] >= time_range[0] * 3600)
        & (sim_all["time_in_seconds"] <= time_range[1] * 3600)
    ]

    # filtered_sim["time"] = filtered_sim["time_in_seconds"]

    run_times_dict = {}
    for station in RUN_TIME_BLOCKS.keys():
        avl = pd.merge_asof(
            left=filtered_df[filtered_df["scada"] == RUN_TIME_BLOCKS[station][0]],
            right=avl_all[avl_all["scada"] == RUN_TIME_BLOCKS[station][1]],
            by=["date", "run_id"],
            left_on="event_datetime",
            right_on="event_datetime",
            direction="forward",
            suffixes=("_origin", "_destination"),
            tolerance=pd.Timedelta(minutes=20),
        )

        sim = pd.merge_asof(
            left=filtered_sim[filtered_sim["block_id"] == RUN_TIME_BLOCKS[station][0]],
            right=sim_all[sim_all["block_id"] == RUN_TIME_BLOCKS[station][1]],
            by=["replication_id", "train_id"],
            left_on="time",
            right_on="time",
            direction="forward",
            suffixes=("_origin", "_destination"),
        )

        real_run_times = (
            avl["event_time_destination"] - avl["event_time_origin"]
        ).dt.total_seconds() / 60

        sim_run_times = (
            sim["time_in_seconds_destination"] - sim["time_in_seconds_origin"]
        ) / 60

        real_run_times.dropna(inplace=True)

        sim_run_times.dropna(inplace=True)

        # filter out outliers by fence method for each series
        q1 = real_run_times.quantile(0.25)
        q3 = real_run_times.quantile(0.75)
        iqr = q3 - q1
        lower_fence = q1 - 3 * iqr
        upper_fence = q3 + 3 * iqr
        real_run_times = real_run_times[
            (real_run_times > lower_fence) & (real_run_times < upper_fence)
        ]

        # q1 = sim_run_times.quantile(0.25)
        # q3 = sim_run_times.quantile(0.75)
        # iqr = q3 - q1
        # lower_fence = q1 - 3 * iqr
        # upper_fence = q3 + 3 * iqr
        # sim_run_times = sim_run_times[(sim_run_times > lower_fence) & (sim_run_times < upper_fence)]

        run_times_dict[station] = real_run_times.mean() - sim_run_times.mean()

    df = pd.DataFrame.from_dict(
        run_times_dict, orient="index", columns=["Run Time Difference"]
    )

    fig = go.Figure(
        go.Bar(
            x=df.index,
            y=df["Run Time Difference"],
            text=df["Run Time Difference"].round(2),
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Run Time Difference: AVL - SIM (mins)",
        xaxis_title="Station",
        yaxis_title="Run Time Difference (mins)",
    )

    fig2 = px.histogram(
        df,
        x="Run Time Difference",
        nbins=20,
        title="Run Time Difference: AVL - SIM (mins) ",
    )

    fig2.add_annotation(
        x=0.5,
        y=1.05,
        xref="paper",
        yref="paper",
        align="left",
        text=f"Mean: {df['Run Time Difference'].mean()} | Std: {df['Run Time Difference'].std()}",
        showarrow=False,
        # arrowhead=1,
    )

    return [fig, fig2]


if __name__ == "__main__":
    # Data Preparation
    merged_data = pd.read_csv("./data/track_events.csv", parse_dates=["event_time"])
    merged_data["event_datetime"] = pd.to_datetime(merged_data["event_time"])
    merged_data["weekday"] = merged_data["event_datetime"].dt.weekday
    merged_data["date"] = merged_data["event_datetime"].dt.date
    merged_data = merged_data[
        (merged_data["event_datetime"].dt.date >= datetime(2023, 5, 15).date())
        & (merged_data["event_datetime"].dt.date <= datetime(2023, 5, 25).date())
    ]

    # merged_data["event_time"] = merged_data["event_datetime"]
    merged_data.sort_values(by=["event_datetime"], inplace=True)
    track_df = merged_data.copy()
    merged_data["dwell_arrtodep"] = (
        abs(merged_data.groupby(["date", "run_id"])["event_time"].diff(-2)).dt.seconds
        / 60
    )

    merged_data = merged_data[merged_data["scada"].isin(STATION_BLOCK.values())]
    merged_data["station"] = merged_data["scada"].map(
        {v: k for k, v in STATION_BLOCK.items()}
    )

    event_delay = pd.read_csv("./data/blue_line_event_delay_drqe.csv")
    event_delay["event_datetime"] = pd.to_datetime(event_delay["event_datetime"])
    event_delay["drqbe"] = event_delay["drqbe"].str.split(" - ").str[-1]

    simulation_results = pd.read_csv("./simulation_results/station_test.csv")
    block_test = pd.read_csv("./simulation_results/block_test.csv")

    # Step 1: Add difference_in_activation column to block_test
    block_test.sort_values(
        by=["replication_id", "train_id", "time_in_seconds"], inplace=True
    )
    block_test["difference_in_activation"] = -block_test.groupby(
        ["replication_id", "train_id"]
    )["time_in_seconds"].diff(-2)

    # Create a new column in station_test dataframe to hold the corresponding block_id values
    simulation_results["block_id"] = simulation_results["station_name"].map(
        STATION_BLOCK
    )

    # Merge the dataframes on replication_id, train_id and block_id
    simulation_results = pd.merge(
        simulation_results,
        block_test,
        on=["replication_id", "train_id", "block_id"],
        how="left",
        suffixes=("_station", ""),
    )

    simulation_results.dropna(inplace=True)

    simulation_results["headway"] = simulation_results["headway"] / 60
    simulation_results["dwell_time"] = simulation_results["dwell_time"] / 60
    simulation_results["difference_in_activation"] = (
        simulation_results["difference_in_activation"] / 60
    )

    # update_run_time_diff((7, 11)).show()

    app.run_server(debug=True, port=find_free_port())
