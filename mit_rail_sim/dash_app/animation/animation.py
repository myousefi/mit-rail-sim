import os

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv


# Function to create frame data for each time step
def create_frame_data(time_step_group):
    latitudes = []
    longitudes = []
    hover_texts = []
    for idx, row in time_step_group.iterrows():
        fraction = row["total_travelled_distance"] / max_travel_distance
        point = north_bound_line.interpolate(fraction, normalized=True)
        latitudes.append(point.y)
        longitudes.append(point.x)
        hover_texts.append(f"Train ID: {row['train_id']}")

    return go.Frame(
        data=[
            go.Scattermapbox(
                lat=latitudes,
                lon=longitudes,
                mode="markers",
                marker=dict(size=8, color="red"),
                hoverinfo="text",
                hovertext=hover_texts,
            )
        ],
        name=f"Time {time_step_group['time_in_seconds'].iloc[0]}",
    )


# Change directory and load environment variables
os.chdir("/Users/moji/Projects/mit_rail_sim/mit_rail_sim/dash_app/animation")

load_dotenv()

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

# Data preprocessing
csv_path = "/Users/moji/Projects/mit_rail_sim/mit_rail_sim/animation/train_test.csv"
df = pd.read_csv(csv_path)
origin_timestamp = pd.Timestamp("2023-04-01 00:00:00")
df["time_in_seconds"] = pd.to_timedelta(df["time_in_seconds"], unit="s")
df["adjusted_time"] = origin_timestamp + df["time_in_seconds"]

# Group by and resample the data
df = (
    df.groupby(
        ["replication_id", "train_id", pd.Grouper(key="adjusted_time", freq="10S")]
    )
    .first()
    .reset_index()
)
df["time_in_seconds"] = (df["adjusted_time"] - origin_timestamp).dt.total_seconds()
df.drop(columns=["adjusted_time"], inplace=True)

# Visualization
stations_gdf = gpd.read_file("./processed_data/stations.shp")
rail_lines_gdf = gpd.read_file("./processed_data/all_lines.shp")

# Create base figure
fig = go.Figure()
fig.add_trace(
    go.Scattermapbox(
        lat=stations_gdf.geometry.y,
        lon=stations_gdf.geometry.x,
        mode="markers",
        marker=dict(size=8, color="blue", symbol="rail"),
        text=stations_gdf["Name"],
    )
)

for idx, row in rail_lines_gdf.iterrows():
    name = row["Name"]
    geom = row["geometry"]
    x, y = geom.xy
    fig.add_trace(
        go.Scattermapbox(
            lat=list(y), lon=list(x), mode="lines", line=dict(width=2), name=name
        )
    )

fig.update_layout(
    mapbox=dict(
        accesstoken=MAPBOX_TOKEN, center=dict(lat=41.8781, lon=-87.6298), zoom=10
    ),
    mapbox_style="light",
)

# Filter the data by replication_id and sort by time
train_data_filtered = df[df["replication_id"] == df["replication_id"].iloc[0]]
train_data_filtered.sort_values(by="time_in_seconds", inplace=True)

# Calculate max_travel_distance
max_travel_distance = train_data_filtered["total_travelled_distance"].max()
north_bound_line = rail_lines_gdf[rail_lines_gdf["Name"] == "NorthBound"].geometry.iloc[
    0
]

# Create frames
frames = (
    train_data_filtered.groupby("time_in_seconds").apply(create_frame_data).tolist()
)
fig.frames = frames

slider_steps = []

for time_in_seconds in train_data_filtered["time_in_seconds"].unique():
    step = {
        "args": [
            [f"Time {time_in_seconds}"],  # Note that this should match the frame's name
            {"frame": {"duration": 50, "redraw": True}, "mode": "immediate"},
        ],
        "label": str(int(time_in_seconds)),  # Display value for the slider
        "method": "animate",
    }
    slider_steps.append(step)

sliders = [
    {
        "active": 0,
        "yanchor": "top",
        "xanchor": "left",
        "currentvalue": {
            "font": {"size": 20},
            "prefix": "Time:",
            "visible": True,
            "xanchor": "right",
        },
        "transition": {"duration": 50, "easing": "cubic-in-out"},
        "pad": {"b": 10, "t": 50},
        "len": 0.9,
        "x": 0.1,
        "y": 0,
        "steps": slider_steps,
    }
]

fig.update_layout(sliders=sliders)

# Add animation controls
animation_settings = dict(frame=dict(duration=50, redraw=True), fromcurrent=True)
updatemenus = [
    {
        "buttons": [
            {
                "args": [
                    None,
                    {"frame": {"duration": 50, "redraw": True}, "fromcurrent": True},
                ],
                "label": "Play",
                "method": "animate",
            },
            {
                "args": [
                    [None],
                    {
                        "frame": {"duration": 0, "redraw": True},
                        "mode": "immediate",
                        "transition": {"duration": 0},
                    },
                ],
                "label": "Pause",
                "method": "animate",
            },
        ],
        "direction": "left",
        "pad": {"r": 10, "t": 87},
        "showactive": False,
        "type": "buttons",
        "x": 0.1,
        "xanchor": "right",
        "y": 0,
        "yanchor": "top",
    }
]

fig.update_layout(updatemenus=updatemenus)


fig.show()
