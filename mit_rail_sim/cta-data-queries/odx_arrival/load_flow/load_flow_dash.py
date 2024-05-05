import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import Input, Output, dcc, html

from mit_rail_sim.utils import find_free_port

# Set default Plotly template
pio.templates.default = "simple_white"

# Load and preprocess data
df = pd.read_csv("../data/cta_afc_data_for_load_flow_imputed.csv")

df["transaction_dtm"] = pd.to_datetime(df["transaction_dtm"])
df["time"] = df["transaction_dtm"].dt.hour
df["day_type"] = df["transaction_dtm"].dt.dayofweek.apply(
    lambda x: "weekday" if x < 5 else "sat" if x == 5 else "sun"
)

# Impute missing data within each group
fill_columns = [
    "route_sequence",
    "direction_sequence",
    "boarding_platform_sequence",
    "alighting_platform_sequence",
    "first_route",
    "first_direction",
    "first_boarding_platform",
    "first_alighting_platform",
]


def impute_within_group(group):
    non_nan_rows = group.dropna(subset=fill_columns)
    if non_nan_rows.empty:
        return group
    nan_rows = group[fill_columns].isna().any(axis=1)
    group.loc[nan_rows, fill_columns] = (
        non_nan_rows[fill_columns].sample(n=nan_rows.sum(), replace=True).values
    )
    return group


df = (
    df.groupby(["boarding_stop", "time", "day_type"])
    .apply(impute_within_group)
    .reset_index(drop=True)
)

# Merge station data
blue_line_stations = pd.read_csv("../data/blue_line_stations.csv")
blue_line_stations["dir_id"] = blue_line_stations["dir_id"].str.rstrip("bound")

df = df.merge(
    blue_line_stations,
    how="left",
    left_on=["first_direction", "first_boarding_platform"],
    right_on=["dir_id", "STOP_ID"],
    suffixes=("", "_boarding"),
)
df = df.merge(
    blue_line_stations,
    how="left",
    left_on=["first_direction", "first_alighting_platform"],
    right_on=["dir_id", "STOP_ID"],
    suffixes=("", "_alighting"),
)

df["origin"] = df["STATION_NAME_IN_SIM"]
df["destination"] = df["STATION_NAME_IN_SIM_alighting"]
df = df[df["first_route"] == "Blue"]

STATION_ORDER_NORTH = blue_line_stations[blue_line_stations["dir_id"] == "North"][
    "STATION_NAME_IN_SIM"
].tolist()

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# App layout
app.layout = html.Div(
    [
        dcc.DatePickerRange(
            id="date-picker-range",
            start_date=df["transaction_dtm"].min().date(),
            end_date=df["transaction_dtm"].min().date(),
            min_date_allowed=df["transaction_dtm"].min().date(),
            max_date_allowed=df["transaction_dtm"].max().date(),
            initial_visible_month=df["transaction_dtm"].min().date(),
        ),
        dcc.RangeSlider(
            id="time-slider",
            min=0,
            max=23,
            step=1,
            value=[7, 11],
            marks={i: str(i) for i in range(24)},
        ),
        dcc.Dropdown(
            id="day-type-dropdown",
            options=[
                {"label": "Weekday", "value": "weekday"},
                {"label": "Saturday", "value": "sat"},
                {"label": "Sunday", "value": "sun"},
            ],
            value="weekday",
            style={"width": "50%"},
        ),
        dcc.Dropdown(
            id="direction-dropdown",
            options=[
                {"label": "North", "value": "North"},
                {"label": "South", "value": "South"},
            ],
            value="North",
            style={"width": "50%"},
        ),
        dcc.Graph(id="graph-output"),
    ]
)


# Callback to update graph
@app.callback(
    Output("graph-output", "figure"),
    [
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("time-slider", "value"),
        Input("day-type-dropdown", "value"),
        Input("direction-dropdown", "value"),
    ],
)
def update_graph(
    start_date,
    end_date,
    time_range,
    selected_day_type,
    selected_direction,
):
    start_date, end_date = (
        pd.to_datetime(start_date).date(),
        pd.to_datetime(end_date).date(),
    )
    if start_date > end_date or time_range[0] >= time_range[1]:
        raise ValueError("Invalid date range or time range.")

    query = (
        "transaction_dtm.dt.date >= @start_date & "
        "transaction_dtm.dt.date <= @end_date & "
        "transaction_dtm.dt.hour >= @time_range[0] & "
        "transaction_dtm.dt.hour < @time_range[1] & "
        "day_type == @selected_day_type & "
        "first_direction == @selected_direction"
    )
    filtered_df = df.query(query)

    categories = (
        STATION_ORDER_NORTH
        if selected_direction == "North"
        else list(reversed(STATION_ORDER_NORTH))
    )
    filtered_df["origin"] = pd.Categorical(
        filtered_df["origin"], categories=categories, ordered=True
    )
    filtered_df["destination"] = pd.Categorical(
        filtered_df["destination"], categories=categories, ordered=True
    )

    daily_cumulative_load_flow = (
        filtered_df.groupby(filtered_df["transaction_dtm"].dt.date)
        .apply(
            lambda day: (day.groupby("origin").size() - day.groupby("destination").size()).cumsum()
        )
        .reindex(columns=STATION_ORDER_NORTH)
        .div(time_range[1] - time_range[0])
    )

    fig = generate_plot(start_date, end_date, daily_cumulative_load_flow)
    title = f"Load Flow Statistics for {time_range[0]}:00-{time_range[1]}:00, Direction: {selected_direction}bound"
    fig.update_layout(
        title=title,
        showlegend=False,
        yaxis_title="Cumulative Load Flow Per Hour",
        yaxis_range=[0, 4000],
    )
    return fig


def generate_plot(start_date, end_date, load_flow_data):
    if start_date != end_date:
        stats = load_flow_data.apply(
            lambda x: {
                "5_percentile": x.quantile(0.05),
                "median": x.median(),
                "95_percentile": x.quantile(0.95),
            }
        ).T
        fig = px.line(
            data_frame=stats,
            y=["median"],
            title="Daily Load Flow Statistics",
            labels={"value": "Cumulative Load Flow", "origin": "Station"},
            color_discrete_sequence=["blue"],
        )
        for percentile in ["95_percentile", "5_percentile"]:
            fig.add_trace(
                go.Scatter(
                    x=stats.index,
                    y=stats[percentile],
                    mode="lines",
                    line=dict(width=0),
                    fillcolor="rgba(135, 206, 250, 0.4)",
                    fill="tonexty",
                    showlegend=True,
                )
            )
    else:
        single_day_load_flow = load_flow_data.iloc[0]
        fig = px.bar(
            x=single_day_load_flow.index,
            y=single_day_load_flow.values,
            labels={"x": "Station", "y": "Cumulative Load Flow Per Hour"},
        )
    return fig


if __name__ == "__main__":
    app.run_server(debug=True, port=find_free_port())
