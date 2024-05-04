import datetime
import functools
import json

import dash

# import diskcache as dc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import dcc, html
from dash.dependencies import Input, Output

from mit_rail_sim.utils import engine, find_free_port, project_root, text

pio.templates.default = "simple_white"


app = dash.Dash(__name__)

# Define color mapping for directions
color_mapping = {
    "NB": "blue",  # Example color for Northbound
    "SB": "red",  # Example color for Southbound
}

# @functools.lru_cache(maxsize=100, typed=False)
# Create a disk cache instance
# cache = dc.Cache(project_root / "mit_rail_sim" / "validation")


# @cache.memoize(expire=86400)
def query_from_aws(selected_date):
    query_text = text(
        """
        SELECT
            event_type,
            run_id,
            scada,
            locationdesc,
            event_time,
            deviation,
            headway,
            qt2_trackid,
            action,
            CASE
                WHEN dir_id = 1 THEN 'NB'
                WHEN dir_id = 5 THEN 'SB'
            END AS direction
        FROM
            cta01.avas_spectrum.qt2_trainevent
        WHERE
            line_id = 1
            AND event_time::date = :selected_date
        ORDER BY
            event_time;
        """
    )

    # Ensure that the parameters are passed as a dictionary directly
    results = engine.execute(query_text, {"selected_date": selected_date})
    df = pd.DataFrame(results.fetchall(), columns=results.keys())
    return df


# Loading static data
with open(project_root / "inputs" / "infra.json", "r") as f:
    data = json.load(f)
    track_dist = {}
    station_dict = {}
    distance = 0
    for block in data["Northbound"]:
        distance += block["DISTANCE"]
        track_dist[block["BLOCK_ALT"]] = distance
        if "STATION" in block:
            station_dict[block["STATION"]["STATION_NAME"]] = (
                distance - block["DISTANCE"] / 2
            )

    for block in data["Southbound"]:
        distance -= block["DISTANCE"]
        track_dist[block["BLOCK_ALT"]] = distance

# Layout of the app
two_days_before_today = datetime.date.today() - datetime.timedelta(days=2)
app.layout = html.Div(
    [
        dcc.DatePickerSingle(id="date-picker-single", date=str(two_days_before_today)),
        dcc.Graph(id="graph", style={"height": "100vh", "width": "100vw"}),
    ]
)


# Callback to update the graph based on the selected date
@app.callback(Output("graph", "figure"), [Input("date-picker-single", "date")])
def update_figure(selected_date):
    df = query_from_aws(selected_date)

    print(df.head())
    print(df.info())

    # df = df[df["event_time"].dt.date == pd.to_datetime(selected_date).date()]
    df["event_seconds"] = (
        df["event_time"] - pd.to_datetime(selected_date)
    ).dt.total_seconds()

    df = df.sort_values(by="event_seconds")

    df["track_dist"] = df["scada"].map(track_dist)
    sorted_run_ids = df["run_id"].unique()
    sorted_run_ids = sorted_run_ids[
        pd.Series(sorted_run_ids).str.extract(r"(\d+)")[0].astype(int).argsort()
    ]

    # Create custom hover text
    hover_columns = df.columns
    # .drop(
    #     ["event_seconds", "track_dist", "gap"]
    # )  # Exclude columns already used in the plot
    df["hover_text"] = df[hover_columns].apply(
        lambda x: "<br>".join(
            [
                f"{col}: {val}"
                for col, val in zip(hover_columns, x.astype(str))
                if pd.notna(val)
            ]
        ),
        axis=1,
    )

    fig = go.Figure()

    # Threshold for gaps (in seconds)
    time_gap_threshold = 60 * 40
    dist_gap_threshold = 10_000
    for run_id in sorted_run_ids:
        run_data = df[df["run_id"] == run_id]

        # Group by direction
        for direction, group_data in run_data.groupby("direction"):
            # Insert NaNs for large gaps
            group_data["gap"] = (
                group_data["event_seconds"].diff() > time_gap_threshold
            ) | (abs(group_data["track_dist"].diff()) > dist_gap_threshold)
            group_data.loc[group_data["gap"], ["event_seconds", "track_dist"]] = [
                float("nan"),
                float("nan"),
            ]

            color = color_mapping.get(
                direction, "black"
            )  # Default to 'black' if direction not found

            fig.add_trace(
                go.Scatter(
                    x=group_data["event_seconds"],
                    y=group_data["track_dist"],
                    mode="lines",
                    name=f"{run_id} ({direction})",
                    # name=f"{run_id}",
                    # legendgroup=run_id,
                    text=group_data["hover_text"],
                    hoverinfo="text",
                    line=dict(color=color),
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=group_data["event_seconds"] + group_data["deviation"] * 60,
                    y=group_data["track_dist"],
                    mode="markers",
                    name=f"{run_id} ({direction}) - Scheduled",
                    # name=f"{run_id}",
                    # legendgroup=run_id,
                    text=group_data["hover_text"],
                    hoverinfo="text",
                    marker=dict(color=color, opacity=0.1, size=1),
                )
            )
    # fig = px.scatter(
    #     df,
    #     x="event_seconds",
    #     y="track_dist",
    #     color="run_id",
    #     hover_data=[
    #         "event_time",
    #         "run_id",
    #         "scada",
    #         # "headway",
    #         # "locationdesc",
    #         # "headway",
    #         # "deviation",
    #     ],
    #     category_orders={"run_id": sorted_run_ids},
    # )

    # Add horizontal lines for stations
    for station_name, distance in station_dict.items():
        fig.add_hline(
            y=distance,
            line_width=1,
            line_dash="dash",
            line_color="black",
            annotation_text=station_name,
            annotation=dict(
                font_size=10,
                font_color="black",
                showarrow=False,
                xref="x",  # Adjusted the reference to the entire plot
                yref="y",
                x=0,
                yanchor="middle",  # Anchored the annotation to the middle of the y-axis
                yshift=0,  # Adjusted the vertical position of the annotation
                xanchor="right",  # Anchored the annotation to the left side of the plot
            ),
        )

    fig.update_traces(marker=dict(size=3))

    fig.update_layout(
        autosize=True,
        margin=dict(l=200),
        showlegend=True,
    )

    df["event_seconds"] = (
        df["event_time"] - pd.to_datetime(selected_date)
    ).dt.total_seconds()

    # remove y-axis ticks
    fig.update_yaxes(
        tickvals=[],
        ticktext=[],
    )

    fig.update_xaxes(
        tickvals=[1800 * i for i in range(int(df["event_seconds"].max() / 1800) + 1)],
        ticktext=[
            pd.to_datetime(v, unit="s").strftime("%H:%M:%S")
            for v in [
                1800 * i for i in range(int(df["event_seconds"].max() / 1800) + 1)
            ]
        ],
        tickangle=-45,
    )

    return fig


if __name__ == "__main__":
    app.run_server(
        debug=True,
        port=find_free_port(),
        host="127.0.0.1",
    )
