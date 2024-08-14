#!/usr/bin/env python

import json

import click
import pandas as pd
import plotly.graph_objects as go

from mit_rail_sim.utils import project_root

# pio.templates.default = "simple_white"

config = {
    "toImageButtonOptions": {
        "format": "svg",  # Set the format to 'svg'
        "filename": "custom_image",
        "height": 600,  # Set the desired height
        "width": 800,  # Set the desired width
        "scale": 1,  # Optionally scale the image
    }
}
# Define color mapping for directions
color_mapping = {
    "Northbound": "green",
    "Southbound": "orange",
}


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


def update_figure(block_data, station_data):
    block_data = block_data.sort_values(by="time_in_seconds")

    block_data["track_dist"] = block_data["block_id"].map(track_dist)
    sorted_run_ids = block_data["train_id"].unique()
    sorted_run_ids = sorted_run_ids[
        pd.Series(sorted_run_ids).str.extract(r"(\d+)")[0].astype(int).argsort()
    ]

    # Create custom hover text
    hover_columns = block_data.columns
    # .drop(
    #     ["time_in_seconds", "track_dist", "gap"]
    # )  # Exclude columns already used in the plot
    block_data["hover_text"] = block_data[hover_columns].apply(
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
        run_data = block_data[block_data["train_id"] == run_id]

        # Group by direction
        for direction, group_data in run_data.groupby("direction"):
            # Insert NaNs for large gaps
            group_data["gap"] = (
                group_data["time_in_seconds"].diff() > time_gap_threshold
            ) | (abs(group_data["track_dist"].diff()) > dist_gap_threshold)
            group_data.loc[group_data["gap"], ["time_in_seconds", "track_dist"]] = [
                float("nan"),
                float("nan"),
            ]

            color = color_mapping.get(
                direction, "black"
            )  # Default to 'black' if direction not found

            fig.add_trace(
                go.Scatter(
                    x=group_data["time_in_seconds"],
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

    # Add horizontal lines for stations
    for station_name, distance in station_dict.items():
        fig.add_hline(
            y=distance,
            line_width=1,
            line_dash="dash",
            line_color="black",
            annotation_text=station_name,
            annotation=dict(
                font_size=8,
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
        margin=dict(l=100, b=50, t=10, r=50),
        showlegend=False,
    )

    # remove y-axis ticks
    fig.update_yaxes(
        tickvals=[],
        ticktext=[],
    )

    fig.update_xaxes(
        tickvals=[
            1800 * i for i in range(int(block_data["time_in_seconds"].max() / 1800) + 1)
        ],
        ticktext=[
            pd.to_datetime(v, unit="s").strftime("%H:%M:%S")
            for v in [
                1800 * i
                for i in range(int(block_data["time_in_seconds"].max() / 1800) + 1)
            ]
        ],
        tickangle=-45,
    )

    # Plot circles for applied holdings
    max_applied_holding = station_data["applied_holding"].max()

    for _, row in station_data[station_data["applied_holding"] > 0].iterrows():
        closest_block = block_data[
            (block_data["train_id"] == row["train_id"])
            & (block_data["direction"] == row["direction"])
        ]
        closest_block["time_diff"] = abs(
            closest_block["time_in_seconds"] - row["time_in_seconds"]
        )
        closest_block = closest_block.sort_values("time_diff").iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[row["time_in_seconds"]],
                y=[closest_block["track_dist"]],
                mode="markers",
                marker=dict(
                    symbol="circle",
                    size=row["applied_holding"] / max_applied_holding * 20,
                    color="rgba(255, 0, 0, 0.5)",
                    line=dict(color="black", width=2),
                ),
                showlegend=False,
                hoverinfo="text",
                hovertext=f"Applied Holding: {row['applied_holding']}<br>Time: {pd.to_datetime(row['time_in_seconds'], unit='s')}<br>Train ID: {row['train_id']} {row['direction']} </br>",
            )
        )

    max_denied_boarding = station_data[
        "number_of_passengers_on_platform_after_stop"
    ].max()
    for _, row in station_data[
        station_data["denied_boarding"] > 0
        # (station_data["number_of_passengers_on_platform_after_stop"] > 0)
        # & (station_data["number_of_passengers_on_train_after_stop"] > 960)
        # & (station_data["direction"] == "Northbound")
    ].iterrows():
        closest_block = block_data[
            (block_data["train_id"] == row["train_id"])
            & (block_data["direction"] == row["direction"])
        ]
        closest_block["time_diff"] = abs(
            closest_block["time_in_seconds"] - row["time_in_seconds"]
        )
        closest_block = closest_block.sort_values("time_diff").iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[row["time_in_seconds"]],
                y=[closest_block["track_dist"]],
                mode="markers",
                marker=dict(
                    symbol="square",
                    size=row["denied_boarding"] / max_denied_boarding * 20,
                    color="rgba(0, 0, 255, 0.5)",
                    line=dict(color="black", width=2),
                ),
                showlegend=False,
                hoverinfo="text",
                hovertext=f"Denied Boarding: {row['denied_boarding']}<br>Time: {pd.to_datetime(row['time_in_seconds'], unit='s')}<br>Train ID: {row['train_id']}",
            )
        )

    return fig


def get_available_replication_ids(train_data):
    return train_data["replication_id"].unique()


@click.command()
@click.argument(
    "results_dir",
    type=click.Path(exists=True),
    default=project_root
    / "cta_experiments_jan"
    / "outputs"
    / "2024-04-22"
    / "12-05-13",
)
@click.option(
    "-r",
    "--replication_id",
    type=int,
    default=None,
    help="Replication ID to display. If not provided, will prompt user to select from available IDs.",
)
def main(results_dir, replication_id):
    block_data = pd.read_csv(str(results_dir) + "/block_test.csv")

    available_ids = get_available_replication_ids(block_data)

    if replication_id is None:
        if len(available_ids) == 1:
            replication_id = available_ids[0]
        else:
            replication_number = click.prompt(
                "Select replication ID",
                type=click.Choice([str(i) for i in range(len(available_ids))]),
                default="0",
            )
            replication_id = available_ids[int(replication_number)]

    block_data = block_data[block_data["replication_id"] == replication_id]

    station_data = pd.read_csv(str(results_dir) + "/station_test.csv")

    station_data = station_data[station_data["replication_id"] == replication_id]

    fig = update_figure(block_data, station_data)
    fig.show(renderer="browser", config=config)


# Load the CSV file and run the app
if __name__ == "__main__":
    main()
