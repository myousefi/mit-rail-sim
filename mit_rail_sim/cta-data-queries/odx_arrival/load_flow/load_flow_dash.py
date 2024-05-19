from pathlib import Path
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import Input, Output, dcc, html

from mit_rail_sim.utils import find_free_port
from mit_rail_sim.utils.root_path import project_root

# Set default Plotly template
pio.templates.default = "simple_white"

# Load and preprocess data
df = pd.read_csv(
    project_root / "inputs" / "demand" / f"odx_imputed_demand_all_periods.csv"
)

df["transaction_dtm"] = pd.to_datetime(df["transaction_dtm"])
df["time"] = df["transaction_dtm"].dt.hour
df["day_type"] = df["transaction_dtm"].dt.dayofweek.apply(
    lambda x: "weekday" if x < 5 else "sat" if x == 5 else "sun"
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
        Input("time-slider", "value"),
        Input("day-type-dropdown", "value"),
        Input("direction-dropdown", "value"),
    ],
)
def update_graph(
    time_range,
    selected_day_type,
    selected_direction,
):
    if time_range[0] >= time_range[1]:
        raise ValueError("Invalid time range.")

    periods = ["Winter 2023", "Spring 2024"]
    data = []

    for period in periods:
        query = (
            "period == @period & "
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

        median_load_flow = (
            (
                filtered_df.groupby("origin").size()
                - filtered_df.groupby("destination").size()
            )
            .cumsum()
            .reindex(categories)
            .div(time_range[1] - time_range[0])
            .div(filtered_df["transaction_dtm"].dt.date.nunique())
        )
        if selected_direction == "North":
            median_load_flow = median_load_flow
        else:
            median_load_flow = median_load_flow[::-1]

        data.append(go.Bar(x=STATION_ORDER_NORTH, y=median_load_flow, name=period))

    fig = go.Figure(data=data)
    title = f"Average Load Flow for {time_range[0]}:00-{time_range[1]}:00, Direction: {selected_direction}bound"
    fig.update_layout(
        title=dict(text=title, font=dict(size=24)),
        barmode="group",
        yaxis_title=dict(
            text="Number of Passengers Per Hour", font=dict(size=18)
        ),  # Increase y-axis title font size
        yaxis=dict(
            range=[0, 4500],
            tickfont=dict(size=14),  # Increase y-axis tick font size
        ),
        xaxis=dict(
            tickfont=dict(size=14),
            tickangle=45,
        ),
        legend=dict(
            font=dict(size=16)  # Increase legend font size
        ),
    )
    return fig


# Add this code block after the `update_graph` function
def save_sample_plots():
    sample_configs = [
        {
            "time_range": [7, 8],
            "selected_day_type": "weekday",
            "selected_direction": "North",
        },
        {
            "time_range": [7, 8],
            "selected_day_type": "weekday",
            "selected_direction": "South",
        },
        {
            "time_range": [16, 17],
            "selected_day_type": "weekday",
            "selected_direction": "North",
        },
        {
            "time_range": [16, 17],
            "selected_day_type": "weekday",
            "selected_direction": "South",
        },
    ]

    output_dir = Path(
        "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"
    )
    # output_dir.mkdir(exist_ok=True)

    for config in sample_configs:
        fig = update_graph(
            config["time_range"],
            config["selected_day_type"],
            config["selected_direction"],
        )

        filename = f"{config['selected_direction']}_{config['selected_day_type']}_{config['time_range'][0]}-{config['time_range'][1]}.svg"
        fig.write_image(
            str(output_dir / filename),
            width=1200,
            height=600,
            scale=2,
        )


if __name__ == "__main__":
    save_sample_plots()
    app.run_server(debug=True, port=find_free_port(), host="127.0.0.1")
