import json

import pandas as pd

from transit_lab_simmetro.utils import project_root

# Step 1: Create a list of all blocks associated with stations and the blocks that come immediately after them
with open(project_root / "alt_file_northbound_updated.json", "r") as f:
    data = json.load(f)
    station_blocks = []
    for i, block in enumerate(data[:-1]):  # Exclude the last block to avoid index error
        if "STATION" in block:
            station_blocks.append(
                (
                    block["BLOCK_ALT"],
                    data[i + 1]["BLOCK_ALT"],
                    block["STATION"]["STATION_NAME"],
                )
            )

# Load the track_events dataset
track_events = pd.read_csv(
    project_root / "transit_lab_simmetro" / "validation" / "data" / "track_events.csv",
    parse_dates=["event_time"],
)

# Step 2: Use pd.merge_asof to find the next event for each block in the list of station blocks
track_events_sorted = track_events.sort_values(by="event_time")

import json

import dash
import pandas as pd
import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output

# Load your data and preprocess it to get station_blocks just like in your script
# (same as Step 1 and the start of Step 2 in your script)

app = dash.Dash(__name__)

# Get the list of unique station names for the dropdown menu
station_names = sorted(
    set(station_name for block1, block2, station_name in station_blocks)
)

app.layout = html.Div(
    [
        dcc.Dropdown(
            id="station-dropdown",
            options=[{"label": name, "value": name} for name in station_names],
            value=station_names[0],  # default value
        ),
        dcc.Graph(id="histogram"),
    ]
)


@app.callback(Output("histogram", "figure"), [Input("station-dropdown", "value")])
def update_histogram(selected_station):
    # Find the blocks corresponding to the selected station
    blocks = [
        (block1, block2)
        for block1, block2, station_name in station_blocks
        if station_name == selected_station
    ]
    block1, block2 = blocks[0]  # Assume there's at least one match

    # Extract events and calculate time differences, just like in your script
    # (similar to the later part of Step 2, and Steps 3 and 4 in your script)

    block1_events = track_events_sorted[track_events_sorted["scada"] == block1]
    block2_events = track_events_sorted[track_events_sorted["scada"] == block2]
    block2_events["time"] = block2_events["event_time"]

    merged = pd.merge_asof(
        block1_events,
        block2_events,
        on="event_time",
        by="run_id",  # I'm not sure if this is necessary, but it's in your script
        direction="forward",
        suffixes=("_block1", "_block2"),
        tolerance=pd.Timedelta("5 minute"),
    )

    merged["time_difference"] = (
        merged["time"] - merged["event_time"]
    ).dt.total_seconds()

    # filter by fence method
    q1 = merged["time_difference"].quantile(0.25)
    q3 = merged["time_difference"].quantile(0.75)
    iqr = q3 - q1
    merged = merged[
        (merged["time_difference"] >= q1 - 1.5 * iqr)
        & (merged["time_difference"] <= q3 + 1.5 * iqr)
    ]

    # Create the histogram using Plotly Express
    fig = px.histogram(
        merged, x="time_difference", title="Histogram of Time Differences"
    )

    return fig


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
