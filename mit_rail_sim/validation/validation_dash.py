from datetime import datetime, time

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import Dash, Input, Output, State, dcc, html
from pandas.tseries.holiday import USFederalHolidayCalendar

from mit_rail_sim.utils import find_free_port

# pio.templates.default = "plotly_dark"


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

STATION_BLOCK_SB = {
    "O-Hare": "nwd739t",
    "Rosemont": "nwd612t",
    "Cumberland": "nwd555t",
    "Harlem (O-Hare Branch)": "nwd475t",
    "Jefferson Park": "nwd327t",
    "Montrose": "nwd270t",
    "Irving Park": "nwd217t",
    "Addison": "nwd184t",
    "Belmont": "nwd146t",
    "Logan Square": "nwd111t",
    "California": "ln2306t",
    "Western (O-Hare Branch)": "ln2269t",
    "Damen": "ln2236t",
    "Division": "dd210t",
    "Chicago": "dd169t",
    "Grand": "dd143t",
    "Clark/Lake": "dd092t",
    "Washington": "dd075t",
    "Monroe": "dd066t",
    "Jackson": "dd058t",
    "LaSalle": "dd038t",
    "Clinton": "dd014t",
    "UIC-Halsted": "wd008t",
    "Racine": "wd035t",
    "Illinois Medical District": "wd069t",
    "Western (Forest Park Branch)": "wd111t",
    "Kedzie-Homan": "wd166t",
    "Pulaski": "wd219t",
    "Cicero": "wd273t",
    "Austin": "wd355t",
    "Oak Park": "wd395t",
    "Harlem (Forest Park Branch)": "wd439t",
    "Forest Park": "wd466t",
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
    "Chicago": ("dc173t", "dc210t"),
    "Division": ("dc215t", "ln1232t"),
    "Damen": ("ln1240t", "ln1269t"),
    "Western (O-Hare Branch)": ("ln1275", "ln1301t"),
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


DWELL_BLOCK = {
    "Forest Park": ("wc470t", "wc463"),
    "Harlem (Forest Park Branch)": ("wc444t", "wc434"),
    "Oak Park": ("wc401t", "wc387t"),
    "Austin": ("wc361t", "wc350t"),
    "Cicero": ("wc279t", "wc266t"),
    "Pulaski": ("wc225t", "wc216"),
    "Kedzie-Homan": ("wc172t", "wc162"),
    "Western (Forest Park Branch)": ("wc117t", "wc108"),
    "Illinois Medical District": ("wc075t", "wc063t"),
    "Racine": ("wc035t", "wc030"),
    "UIC-Halsted": ("wc008t", "wc003t"),
    "Clinton": ("dc014t", "dc023t"),
    "LaSalle": ("dc036t", "dc044t"),
    "Jackson": ("dc056t", "dc061t"),
    "Monroe": ("dc066t", "dc072t"),
    "Washington": ("dc075t", "dc082t"),
    "Clark/Lake": ("dc088t", "dc099t"),
    "Grand": ("dc138t", "dc145t"),
    "Chicago": ("dc164t", "dc173t"),
    "Division": ("dc210t", "dc215t"),
    "Damen": ("ln1232t", "ln1240t"),
    "Western (O-Hare Branch)": ("ln1269t", "ln1275"),
    "California": ("ln1301t", "ln1310t"),
    "Logan Square": ("nwc110t", "nwc118t"),
    "Belmont": ("nwc146t", "nwc154t"),
    "Addison": ("nwc185t", "nwc189"),
    "Irving Park": ("nwc218t", "nwc225t"),
    "Montrose": ("nwc270t", "nwc278t"),
    "Jefferson Park": ("nwc325t", "nwc332t"),
    "Harlem (O-Hare Branch)": ("nwc468t", "nwc486t"),
    "Cumberland": ("nwc547t", "nwc561t"),
    "Rosemont": ("nwc606t", "nwc615t"),
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
app.title = "Validation Dashboard"

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
                dbc.Col(
                    [
                        html.Label("Delay Threshold"),
                        dcc.Input(id="delay-threshold-input", type="number", value=10, min=0),
                    ]
                ),
            ]
        ),
        dcc.Graph(id="bar-plot"),
        dcc.Store(id="delay-days-store"),  # Store for delay_days
        dcc.Dropdown(
            id="station-dropdown",
            options=[{"label": station, "value": station} for station in STATION_ORDER],
            value=STATION_ORDER[0],
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="headway-histogram")),
                dbc.Col(dcc.Graph(id="dwell-histogram")),
            ]
        ),
        dbc.Row((dcc.Graph(id="run-time-histogram"))),
        dbc.Row((dcc.Graph(id="dwell-time-histogram"))),
        dbc.Row(  # This was moved inside the main list to properly nest it.
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
                dbc.Col(dcc.Graph(id="travel-time-histogram")),
            ]
        ),
        dbc.Col(
            [
                dbc.Row(dcc.Graph(id="boarded-passengers-boxplot")),
                dbc.Row(dcc.Graph(id="alighted-passengers-boxplot")),
                dbc.Row(dcc.Graph(id="on-train-passengers-boxplot")),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Percentile of Interest"),
                        dcc.Input(
                            id="percentile-input",
                            type="number",
                            value=50,
                            min=1,
                            max=99,
                        ),
                    ]
                )
            ]
        ),
        dbc.Row([dbc.Col(dcc.Graph(id="heatmap-plot"))]),
    ],
    fluid=True,
)


# Callback for bar plot and updating delay-days-store
@app.callback(
    [Output("bar-plot", "figure"), Output("delay-days-store", "data")],
    [
        Input("time-range-slider", "value"),
        Input("delay-threshold-input", "value"),
    ],
)
def update_bar_plot(time_range, delay_threshold):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    filtered_event_delay = event_delay[
        (event_delay["event_datetime"].dt.time >= start_time)
        & (event_delay["event_datetime"].dt.time <= end_time)
    ]

    grouped_delays = (
        filtered_event_delay.groupby(filtered_event_delay["event_datetime"].dt.date)
        .agg({"delay": "sum"})
        .reset_index()
    )

    # Find the minimum and maximum dates from the grouped data
    min_date = filtered_event_delay["event_datetime"].min().date()
    max_date = filtered_event_delay["event_datetime"].max().date()

    # Generate a full date range between min and max dates
    full_date_range = pd.date_range(min_date, max_date)

    # Reindex the DataFrame
    grouped_delays.set_index("event_datetime", inplace=True)
    grouped_delays = grouped_delays.reindex(full_date_range).fillna(0).reset_index()
    grouped_delays.rename(columns={"index": "event_datetime"}, inplace=True)

    grouped_delays["event_datetime"] = pd.to_datetime(grouped_delays["event_datetime"])

    # Filter dates where the total delay is below the threshold
    non_delayed_days = grouped_delays[grouped_delays["delay"] <= delay_threshold][
        "event_datetime"
    ].dt.date.tolist()

    delay_grouped = (
        filtered_event_delay.groupby([filtered_event_delay["event_datetime"].dt.date, "drqbe"])[
            "delay"
        ]
        .sum()
        .reset_index()
    )

    fig_bar = px.bar(
        delay_grouped,
        x="event_datetime",
        y="delay",
        color="drqbe",
        labels={"event_datetime": "Date", "delay": "Total Delay"},
        title="Total Delay by DRQE Category",
    )

    # Add a horizontal line to indicate the delay threshold
    fig_bar.add_shape(
        go.layout.Shape(
            type="line",
            x0=delay_grouped["event_datetime"].min(),
            x1=delay_grouped["event_datetime"].max(),
            y0=delay_threshold,
            y1=delay_threshold,
            line=dict(color="Red", width=2),
        )
    )

    # Prepare the ticks for the x-axis
    tickvals = []
    ticktext = []

    for date in pd.date_range(
        delay_grouped["event_datetime"].min(), delay_grouped["event_datetime"].max()
    ):
        date_str = date.strftime("%Y-%m-%d")
        weekday_str = date.strftime("%A")
        month_str = date.strftime("%b")  # Month as a short string

        tickvals.append(date_str)

        # If the date is in non_delayed_days, color it red
        if date.date() in non_delayed_days:
            ticktext.append(f"{month_str} {date.day} - ({weekday_str})")
        else:
            ticktext.append(
                f"<span style='color:red;'>{month_str} {date.day} - ({weekday_str})</span>"
            )

    # Update the x-axis of the figure to include our custom tick labels
    fig_bar.update_xaxes(
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=-45,  # rotate the tick labels
    )

    return fig_bar, {"non_delayed_days": non_delayed_days}


@app.callback(
    [Output("run-time-histogram", "figure")],
    [
        Input("station-dropdown", "value"),
        Input("time-range-slider", "value"),
        Input("delay-days-store", "data"),
    ],
)
def update_run_time_histogram(selected_station, time_range, stored_data):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    filtered_df = track_df[track_df["scada"].isin(RUN_TIME_BLOCKS[selected_station])].copy()
    filtered_df = filter_by_time_and_weekday(filtered_df, start_time, end_time)
    filtered_df = remove_holidays(filtered_df)

    # Filter simulation data by time and selected station
    filtered_sim = block_test[block_test["block_id"].isin(RUN_TIME_BLOCKS[selected_station])].copy()
    filtered_sim = filtered_sim[
        (filtered_sim["time_in_seconds"] >= time_range[0] * 3600)
        & (filtered_sim["time_in_seconds"] <= time_range[1] * 3600)
    ]

    filtered_sim.sort_values(by=["time_in_seconds"], inplace=True)
    filtered_sim["time"] = filtered_sim["time_in_seconds"]

    if stored_data:
        non_delayed_days = stored_data["non_delayed_days"]
        # Convert back to datetime.date from str
        non_delayed_days = [
            datetime.strptime(date_str, "%Y-%m-%d").date() for date_str in non_delayed_days
        ]
        filtered_df = filtered_df[filtered_df["event_datetime"].dt.date.isin(non_delayed_days)]

    avl = pd.merge_asof(
        left=filtered_df[filtered_df["scada"] == RUN_TIME_BLOCKS[selected_station][0]],
        right=filtered_df[filtered_df["scada"] == RUN_TIME_BLOCKS[selected_station][1]],
        by=["date", "run_id"],
        left_on="event_datetime",
        right_on="event_datetime",
        direction="forward",
        suffixes=("_origin", "_destination"),
        tolerance=pd.Timedelta(minutes=20),
    )

    sim = pd.merge_asof(
        left=filtered_sim[filtered_sim["block_id"] == RUN_TIME_BLOCKS[selected_station][0]],
        right=filtered_sim[filtered_sim["block_id"] == RUN_TIME_BLOCKS[selected_station][1]],
        by=["replication_id", "train_id"],
        left_on="time",
        right_on="time",
        direction="forward",
        suffixes=("_origin", "_destination"),
    )

    real_run_times = (
        avl["event_time_destination"] - avl["event_time_origin"]
    ).dt.total_seconds() / 60

    sim_run_times = (sim["time_in_seconds_destination"] - sim["time_in_seconds_origin"]) / 60

    real_run_times = real_run_times.dropna(inplace=False)

    # # filter real_run_times with IQR in one line
    q1 = real_run_times.quantile(0.25)
    q3 = real_run_times.quantile(0.75)
    iqr = q3 - q1
    real_run_times = real_run_times[
        (real_run_times >= q1 - 3 * iqr) & (real_run_times <= q3 + 3 * iqr)
    ]

    sim_run_times = sim_run_times.dropna(inplace=False)

    fig = go.Figure()

    # Add real-world data
    fig.add_trace(go.Histogram(x=real_run_times.values, name="Real-World Data", histnorm="percent"))

    # Add simulation data
    fig.add_trace(go.Histogram(x=sim_run_times.values, name="Simulation Data", histnorm="percent"))

    fig.update_layout(
        title=f"Run-Time Histogram for {selected_station} to Next Station",
        xaxis_title="Run-Time (min)",
        yaxis_title="Frequency",
    )

    # Add real-world annotation
    fig.add_annotation(
        x=0.05,
        y=0.95,
        text=(
            f"<b>Real-world</b><br>Mean: {real_run_times.mean():.2f} min<br>Std Dev:"
            f" {real_run_times.std():.2f} min"
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

    # Add simulation annotation
    fig.add_annotation(
        x=0.95,
        y=0.95,
        text=(
            f"<b>Simulation</b><br>Mean: {sim_run_times.mean():.2f} min<br>Std Dev:"
            f" {sim_run_times.std():.2f} min"
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

    return [fig]


@app.callback(
    [Output("dwell-time-histogram", "figure")],
    [
        Input("station-dropdown", "value"),
        Input("time-range-slider", "value"),
        Input("delay-days-store", "data"),
    ],
)
def update_dwell_time_histogram(selected_station, time_range, stored_data):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    filtered_df = track_df[track_df["scada"].isin(DWELL_BLOCK[selected_station])].copy()
    filtered_df = filter_by_time_and_weekday(filtered_df, start_time, end_time)
    # filtered_df = remove_holidays(filtered_df)

    # Filter simulation data by time and selected station
    filtered_sim = block_test[block_test["block_id"].isin(DWELL_BLOCK[selected_station])].copy()
    filtered_sim = filtered_sim[
        (filtered_sim["time_in_seconds"] >= time_range[0] * 3600)
        & (filtered_sim["time_in_seconds"] <= time_range[1] * 3600)
    ]

    filtered_sim.sort_values(by=["time_in_seconds"], inplace=True)
    filtered_sim["time"] = filtered_sim["time_in_seconds"]

    if stored_data:
        non_delayed_days = stored_data["non_delayed_days"]
        # Convert back to datetime.date from str
        non_delayed_days = [
            datetime.strptime(date_str, "%Y-%m-%d").date() for date_str in non_delayed_days
        ]
        filtered_df = filtered_df[filtered_df["event_datetime"].dt.date.isin(non_delayed_days)]

    avl = pd.merge_asof(
        left=filtered_df[filtered_df["scada"] == DWELL_BLOCK[selected_station][0]],
        right=filtered_df[filtered_df["scada"] == DWELL_BLOCK[selected_station][1]],
        by=["date", "run_id"],
        left_on="event_datetime",
        right_on="event_datetime",
        direction="forward",
        suffixes=("_origin", "_destination"),
        tolerance=pd.Timedelta(minutes=20),
    )

    sim = pd.merge_asof(
        left=filtered_sim[filtered_sim["block_id"] == DWELL_BLOCK[selected_station][0]],
        right=filtered_sim[filtered_sim["block_id"] == DWELL_BLOCK[selected_station][1]],
        by=["replication_id", "train_id"],
        left_on="time",
        right_on="time",
        direction="forward",
        suffixes=("_origin", "_destination"),
    )

    real_run_times = (
        avl["event_time_destination"] - avl["event_time_origin"]
    ).dt.total_seconds() / 60

    sim_run_times = (sim["time_in_seconds_destination"] - sim["time_in_seconds_origin"]) / 60

    real_run_times = real_run_times.dropna(inplace=False)

    # # filter real_run_times with IQR in one line
    # q1 = real_run_times.quantile(0.25)
    # q3 = real_run_times.quantile(0.75)
    # iqr = q3 - q1
    # real_run_times = real_run_times[
    #     (real_run_times >= q1 - 3 * iqr) & (real_run_times <= q3 + 3 * iqr)
    # ]

    sim_run_times = sim_run_times.dropna(inplace=False)

    fig = go.Figure()

    # Add real-world data
    fig.add_trace(go.Histogram(x=real_run_times.values, name="Real-World Data", histnorm="percent"))

    # Add simulation data
    fig.add_trace(go.Histogram(x=sim_run_times.values, name="Simulation Data", histnorm="percent"))

    fig.update_layout(
        title=f"Dwell-Time Histogram for {selected_station}",
        xaxis_title="Dwell Time (min)",
        yaxis_title="Frequency",
    )

    # Add real-world annotation
    fig.add_annotation(
        x=0.05,
        y=0.95,
        text=(
            f"<b>Real-world</b><br>Mean: {real_run_times.mean():.2f} min<br>Std Dev:"
            f" {real_run_times.std():.2f} min"
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

    # Add simulation annotation
    fig.add_annotation(
        x=0.95,
        y=0.95,
        text=(
            f"<b>Simulation</b><br>Mean: {sim_run_times.mean():.2f} min<br>Std Dev:"
            f" {sim_run_times.std():.2f} min"
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

    return [fig]


@app.callback(
    [
        Output("headway-histogram", "figure"),
        Output("dwell-histogram", "figure"),
    ],
    [
        Input("station-dropdown", "value"),
        Input("time-range-slider", "value"),
        Input("delay-days-store", "data"),
    ],
)
def update_histograms(selected_station, time_range, stored_data):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    filtered_df = filter_by_time_and_weekday(merged_data, start_time, end_time)
    filtered_df = remove_holidays(filtered_df)

    # Filter simulation data by time and selected station
    filtered_sim = simulation_results[(simulation_results["station_name"] == selected_station)]
    filtered_sim = filtered_sim[
        (filtered_sim["time_in_seconds"] >= time_range[0] * 3600)
        & (filtered_sim["time_in_seconds"] <= time_range[1] * 3600)
    ]

    if stored_data:
        non_delayed_days = stored_data["non_delayed_days"]
        # Convert back to datetime.date from str
        non_delayed_days = [
            datetime.strptime(date_str, "%Y-%m-%d").date() for date_str in non_delayed_days
        ]
        filtered_df = filtered_df[filtered_df["event_datetime"].dt.date.isin(non_delayed_days)]

    station_df = filtered_df[filtered_df["station"] == selected_station].copy()

    # filter station_df with IQR on headway and dwell_time
    q1 = station_df["headway"].quantile(0.25)
    q3 = station_df["headway"].quantile(0.75)
    iqr = q3 - q1
    station_df = station_df[
        (station_df["headway"] >= q1 - 3 * iqr) & (station_df["headway"] <= q3 + 3 * iqr)
    ]

    q1 = station_df["dwell_arrtodep"].quantile(0.25)
    q3 = station_df["dwell_arrtodep"].quantile(0.75)
    iqr = q3 - q1
    station_df = station_df[
        (station_df["dwell_arrtodep"] >= q1 - 3 * iqr)
        & (station_df["dwell_arrtodep"] <= q3 + 3 * iqr)
    ]

    figs = []
    for column, sim_column, title in zip(
        ["headway", "dwell_arrtodep"],
        ["headway", "difference_in_activation"],
        ["Headway", "Dwell Time"],
    ):
        data = station_df[column].dropna()
        sim_data = filtered_sim[sim_column].dropna()

        # Calculate mean and std_dev for real-world data
        mean_real = np.mean(data)
        std_dev_real = np.std(data)

        # Calculate mean and std_dev for simulation data
        mean_sim = np.mean(sim_data)
        std_dev_sim = np.std(sim_data)

        fig = go.Figure()

        # Add real-world data
        fig.add_trace(go.Histogram(x=data, name="Real-World Data", histnorm="percent"))

        # Add simulation data
        fig.add_trace(go.Histogram(x=sim_data, name="Simulation Data", histnorm="percent"))

        fig.update_layout(
            title=f"{title} Histogram for {selected_station}",
            xaxis_title=f"{title} (min)",
            yaxis_title="Frequency",
        )

        # Add real-world annotation
        fig.add_annotation(
            x=0.05,
            y=0.95,
            text=(
                f"<b>Real-world</b><br>Mean: {mean_real:.2f} min<br>Std Dev: {std_dev_real:.2f} min"
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

        # Add simulation annotation
        fig.add_annotation(
            x=0.95,
            y=0.95,
            text=f"<b>Simulation</b><br>Mean: {mean_sim:.2f} min<br>Std Dev: {std_dev_sim:.2f} min",
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

        figs.append(fig)

    return figs


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
    travel_times = (
        (merged_df["event_time_destination"] - merged_df["event_time_origin"]).dt.total_seconds()
        / 60
    ).dropna()

    # # Filter travel times between the 5th and 95th percentiles
    # lower_bound = travel_times.quantile(0.05)
    # upper_bound = travel_times.quantile(0.95)
    # travel_times = travel_times[(travel_times >= lower_bound) & (travel_times <= upper_bound)]

    # Filter by fence method
    q1 = travel_times.quantile(0.25)
    q3 = travel_times.quantile(0.75)
    iqr = q3 - q1
    travel_times = travel_times[(travel_times >= q1 - 3 * iqr) & (travel_times <= q3 + 3 * iqr)]

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

    # print(merged_df.head(5))
    # Calculate the travel times
    sim_travel_times = (
        (merged_df["time_in_seconds_destination"] - merged_df["time_in_seconds_origin"]) / 60
    ).dropna()

    return sim_travel_times


# New callback for station-pair histograms
@app.callback(
    Output("travel-time-histogram", "figure"),
    [
        Input("start-station-dropdown", "value"),
        Input("end-station-dropdown", "value"),
        Input("time-range-slider", "value"),
        Input("delay-days-store", "data"),
    ],
)
def update_travel_time_histogram(start_station, end_station, time_range, stored_data):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    filtered_df = filter_by_time_and_weekday(merged_data, start_time, end_time)
    filtered_df = remove_holidays(filtered_df)

    if stored_data:
        non_delayed_days = stored_data["non_delayed_days"]
        non_delayed_days = [
            datetime.strptime(date_str, "%Y-%m-%d").date() for date_str in non_delayed_days
        ]
        filtered_df = filtered_df[filtered_df["event_datetime"].dt.date.isin(non_delayed_days)]

    real_travel_times = calculate_real_travel_times(
        filtered_df, merged_data, start_station, end_station
    )
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=real_travel_times, name="Travel Time", histnorm="percent"))

    filtered_sim = simulation_results[
        (simulation_results["time_in_seconds"] >= time_range[0] * 3600)
        & (simulation_results["time_in_seconds"] <= time_range[1] * 3600)
    ]
    sim_travel_times = calculate_sim_travel_times(
        filtered_sim, simulation_results, start_station, end_station
    )

    fig.add_trace(go.Histogram(x=sim_travel_times, name="Simulation", histnorm="percent"))

    fig.update_layout(
        title=f"Travel Time Histogram from {start_station} to {end_station}",
        xaxis_title="Travel Time (min)",
        yaxis_title="Frequency",
    )

    fig.add_annotation(
        x=0.05,
        y=0.95,
        text=(
            f"<b>Real-world</b><br>Mean: {real_travel_times.mean():.2f} min<br>Std Dev:"
            f" {real_travel_times.std():.2f} min"
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

    fig.add_annotation(
        x=0.95,
        y=0.95,
        text=(
            f"<b>Simulation</b><br>Mean: {sim_travel_times.mean():.2f} min<br>Std Dev:"
            f" {sim_travel_times.std():.2f} min"
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

    return fig


@app.callback(
    [
        Output("boarded-passengers-boxplot", "figure"),
        Output("alighted-passengers-boxplot", "figure"),
        Output("on-train-passengers-boxplot", "figure"),
    ],
    [Input("time-range-slider", "value"), Input("delay-threshold-input", "value")],
)
def update_passenger_boxplots(time_range, delay_threshold):
    # Here, filter simulation_results based on time and delay if needed
    # ...

    # Sort the DataFrame according to the station order
    sorted_simulation_results = simulation_results.copy()

    sorted_simulation_results = sorted_simulation_results[
        (sorted_simulation_results["time_in_seconds"] >= time_range[0] * 3600)
        & (sorted_simulation_results["time_in_seconds"] <= time_range[1] * 3600)
    ]

    sorted_simulation_results["station_name"] = sorted_simulation_results["station_name"].astype(
        "category"
    )
    sorted_simulation_results["station_name"] = sorted_simulation_results[
        "station_name"
    ].cat.set_categories(STATION_ORDER, ordered=True)
    sorted_simulation_results = sorted_simulation_results.sort_values(["station_name"])
    fig_boarded = px.box(
        sorted_simulation_results,
        x="station_name",
        y="number_of_passengers_boarded",
        color="direction",
    )
    fig_boarded.update_layout(
        title="Boarding",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
    )

    fig_alighted = px.box(
        sorted_simulation_results,
        x="station_name",
        y="number_of_passengers_alighted",
        color="direction",
    )
    fig_alighted.update_layout(
        title="Alighting",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
    )

    fig_on_train = px.box(
        sorted_simulation_results,
        x="station_name",
        y="number_of_passengers_on_train_after_stop",
        color="direction",
    )
    fig_on_train.update_layout(
        title="Train Load",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
    )

    return fig_boarded, fig_alighted, fig_on_train


# def calculate_sim_travel_times_all_pairs(df):
#     # Sort DataFrame by necessary keys
#     df = df[["replication_id", "train_id", "time_in_seconds", "station_name"]].copy()
#     df = df.sort_values(by="time_in_seconds")
#     df["time"] = df["time_in_seconds"]

#     # Merge DataFrames on replication_id, train_id, and find the closest time_in_seconds
#     merged_df = pd.merge_asof(
#         df,
#         df,
#         by=["replication_id", "train_id"],
#         on="time",
#         direction="forward",
#         allow_exact_matches=False,
#         suffixes=("_origin", "_destination"),
#     )

#     merged_df["travel_time"] = (
#         merged_df["time_in_seconds_destination"] - merged_df["time_in_seconds_origin"]
#     ) / 60

#     # print(merged_df.head(50))
#     return merged_df[["station_name_origin", "station_name_destination", "travel_time"]]


# def calculate_real_travel_times_all_pairs(df):
#     # Sort df by 'event_time' for merge_asof to work
#     df = df[["date", "run_id", "event_time", "event_datetime", "station"]].copy()
#     df = df.sort_values("event_time")

#     # Merge the DataFrame with itself to get OD pairs
#     merged_df = pd.merge_asof(
#         df,
#         df,
#         by=["date", "run_id"],
#         left_on="event_time",
#         right_on="event_time",
#         direction="forward",
#         suffixes=("_origin", "_destination"),
#     )

#     # print(merged_df.head(5))

#     # Add a max_time column for asof merge
#     # df["max_time"] = df["event_datetime_origin"] + pd.Timedelta(minutes=180)

#     # Filter rows where the destination station is different from the origin station
#     # and within the 180-minute window
#     merged_df = merged_df[(merged_df["station_origin"] != merged_df["station_destination"])]

#     # Calculate travel time
#     merged_df["travel_time"] = (
#         merged_df["event_datetime_destination"] - merged_df["event_datetime_origin"]
#     ).dt.total_seconds() / 60

#     # merged_df = merged_df[merged_df["travel_time"] < 180]

#     return merged_df[["station_origin", "station_destination", "travel_time"]]


@app.callback(
    Output("heatmap-plot", "figure"),
    [
        Input("percentile-input", "value"),
        Input("time-range-slider", "value"),
        Input("delay-days-store", "data"),
    ],
)
def update_heatmap_plot(percentile, time_range, stored_data):
    start_time = time(time_range[0])
    end_time = time(time_range[1])

    filtered_df = filter_by_time_and_weekday(merged_data, start_time, end_time)
    filtered_df = remove_holidays(filtered_df)

    if stored_data:
        non_delayed_days = stored_data["non_delayed_days"]
        non_delayed_days = [
            datetime.strptime(date_str, "%Y-%m-%d").date() for date_str in non_delayed_days
        ]
        filtered_df = filtered_df[filtered_df["event_datetime"].dt.date.isin(non_delayed_days)]

    filtered_sim = simulation_results[
        (simulation_results["time_in_seconds"] >= time_range[0] * 3600)
        & (simulation_results["time_in_seconds"] <= time_range[1] * 3600)
    ]
    # Use the new function to get travel times for all OD pairs
    # all_pair_real_travel_times = calculate_real_travel_times_all_pairs(filtered_df)
    # all_pair_sim_travel_times = calculate_sim_travel_times_all_pairs(simulation_results)

    # Initialize a 2D array to store the differences between real and simulation travel times
    diff_matrix = np.zeros((len(STATION_ORDER), len(STATION_ORDER)))

    for i, origin_station in enumerate(STATION_ORDER):
        for j, destination_station in enumerate(STATION_ORDER):
            if j <= i:  # Only consider stations that come after the origin in STATION_ORDER
                continue

            # Filter the all_pair_real_travel_times for the current OD pair
            real_travel_times = calculate_real_travel_times(
                filtered_df, merged_data, origin_station, destination_station
            )
            # all_pair_real_travel_times[
            #     (all_pair_real_travel_times["station_origin"] == origin_station)
            #     & (all_pair_real_travel_times["station_destination"] == destination_station)
            # ]["travel_time"]

            # Calculate simulated travel times using your existing function
            sim_travel_times = calculate_sim_travel_times(
                filtered_sim, simulation_results, origin_station, destination_station
            )
            # all_pair_sim_travel_times[
            #     (all_pair_sim_travel_times["station_name_origin"] == origin_station)
            #     & (all_pair_sim_travel_times["station_name_destination"] == destination_station)
            # ]["travel_time"]

            if real_travel_times.empty or sim_travel_times.empty:
                diff_matrix[i, j] = np.nan
                print(f"Missing data for {origin_station} to {destination_station}")
                print(f"Real travel times: {real_travel_times}")
                print(f"Sim travel times: {sim_travel_times}")
                continue

            percentile_real = np.percentile(real_travel_times, percentile)
            percentile_sim = np.percentile(sim_travel_times, percentile)

            # Calculate the difference
            diff_matrix[i, j] = percentile_real - percentile_sim

    # Create the heatmap plot
    fig = px.imshow(
        diff_matrix,
        labels=dict(x="Destination Stations", y="Origin Stations", color="Difference"),
        x=STATION_ORDER,
        y=STATION_ORDER,
        color_continuous_scale="RdBu_r",  # Choose an appropriate color scale
        color_continuous_midpoint=0,
    )
    fig.update_layout(title="Heatmap of Real - Simulated Travel Times")

    # Update layout to make the plot bigger
    fig.update_layout(
        title="Heatmap of Difference Between Real and Simulated Travel Times",
        autosize=False,
        width=1000,  # Set figure width
        height=1000,  # Set figure height
    )

    # Show all x-axis and y-axis labels
    fig.update_xaxes(tickvals=list(range(len(STATION_ORDER))), ticktext=STATION_ORDER, tickangle=45)
    fig.update_yaxes(tickvals=list(range(len(STATION_ORDER))), ticktext=STATION_ORDER)

    return fig


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
    # simulation_results = simulation_results[simulation_results["direction"] == "Northbound"]
    block_test = pd.read_csv("./simulation_results/block_test.csv")

    # Step 1: Add difference_in_activation column to block_test
    block_test.sort_values(by=["replication_id", "train_id", "time_in_seconds"], inplace=True)
    block_test["difference_in_activation"] = -block_test.groupby(["replication_id", "train_id"])[
        "time_in_seconds"
    ].diff(-2)

    # Create a new column in station_test dataframe to hold the corresponding block_id values for the Northbound direction only
    simulation_results["block_id"] = simulation_results.apply(
        lambda row: STATION_BLOCK[row["station_name"]]
        if row["direction"] == "Northbound"
        else STATION_BLOCK_SB[row["station_name"]],
        axis=1,
    )
    # simulation_results[simulation_results["direction"] == "Southbound"][
    #     "block_id"
    # ] = simulation_results[simulation_results["direction"] == "Southbound"]["station_name"].map(
    #     STATION_BLOCK_SB
    # )

    # Merge the dataframes on replication_id, train_id and block_id
    simulation_results = pd.merge(
        simulation_results,
        block_test,
        on=["replication_id", "train_id", "block_id"],
        how="left",
        suffixes=("_station", ""),
    )

    # simulation_results.dropna(inplace=True)

    simulation_results.to_csv(
        "/Users/moji/Projects/mit_rail_sim/mit_rail_sim/validation/simulation_results/simulation_merged.csv",
        index=False,
    )
    print("saved")
    simulation_results["headway"] = simulation_results["headway"] / 60
    simulation_results["dwell_time"] = simulation_results["dwell_time"] / 60
    simulation_results["difference_in_activation"] = (
        simulation_results["difference_in_activation"] / 60
    )

    app.run_server(debug=True, port=find_free_port())
