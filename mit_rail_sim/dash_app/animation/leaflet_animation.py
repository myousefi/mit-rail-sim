import os
from datetime import datetime, timedelta

import folium
import geopandas as gpd
import pandas as pd
from folium import plugins

from mit_rail_sim.utils import project_root

os.chdir(project_root / "mit_rail_sim" / "dash_app" / "animation")


def get_color(number_of_passengers, min_passengers=0, max_passengers=960):
    # Normalize the passenger count to a value between 0 and 1
    normalized_value = (number_of_passengers - min_passengers) / (
        max_passengers - min_passengers
    )
    normalized_value = max(0, min(normalized_value, 1))  # Clamp between 0 and 1

    # Interpolate between green and red
    red = normalized_value
    green = 1 - normalized_value
    blue = 0

    # Convert to hex color code
    return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


# Function to generate a GeoJSON feature for each row
def generate_feature(row, north_bound_line, max_travel_distance):
    fraction = row["location_from_terminal"] / max_travel_distance
    point = north_bound_line.interpolate(fraction, normalized=True)

    color = get_color(row["number_of_passengers_on_board"])

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [point.x, point.y],
        },
        "properties": {
            "times": [
                (
                    datetime(2023, 12, 10) + timedelta(seconds=row["time_in_seconds"])
                ).isoformat()
            ],
            "style": {"color": color, "weight": 5},
            "icon": "circle",
            "iconstyle": {
                "fillColor": color,
                "fillOpacity": 0.0,
                "stroke": "false",
                "radius": 4,
            },
        },
    }

    return feature


# Read and preprocess the CSV file into a DataFrame (from the second script)
csv_path = project_root / "mit_rail_sim" / "animation" / "train_test.csv"

df = pd.read_csv(csv_path)
df["time_in_seconds"] = pd.to_timedelta(df["time_in_seconds"], unit="s")
origin_timestamp = pd.Timestamp("2023-12-01 00:00:00")
df["adjusted_time"] = origin_timestamp + df["time_in_seconds"]
df = (
    df.groupby(["train_id", pd.Grouper(key="adjusted_time", freq="20S")])
    .first()
    .reset_index()
)
df["time_in_seconds"] = (df["adjusted_time"] - origin_timestamp).dt.total_seconds()
df.drop(columns=["adjusted_time"], inplace=True)

# Choose the first replication
df = df[df["replication_id"] == df["replication_id"].iloc[0]]


# Read shapefiles
stations_gdf = gpd.read_file("./processed_data/stations.shp")
rail_lines_gdf = gpd.read_file("./processed_data/all_lines.shp")
north_bound_line = rail_lines_gdf[rail_lines_gdf["Name"] == "NorthBound"].geometry.iloc[
    0
]

# Create base folium map
m = folium.Map(
    [41.92147007783234, -87.7808453375612], zoom_start=12, tiles="cartodb positron"
)


# Add stations and rail lines to map
for idx, row in stations_gdf.iterrows():
    folium.Circle(
        [row.geometry.y, row.geometry.x],
        tooltip=row["Name"],
        color="blue",
        fill=True,
        fill_color="white",
        fill_opacity=0,
        radius=100,
        # icon=folium.Icon(color="blue", icon="train", prefix="fa"),
    ).add_to(m)

for idx, row in rail_lines_gdf.iterrows():
    geom = row["geometry"]
    x, y = geom.xy
    folium.PolyLine(
        locations=[(lat, lon) for lat, lon in zip(y, x)], color="blue"
    ).add_to(m)

# Sort the DataFrame by 'train_id' and 'time_in_seconds'
df.sort_values(["train_id", "time_in_seconds"], inplace=True)


max_travel_distance = df["location_from_terminal"].max()

# Generate features using apply
features = df.apply(
    generate_feature, axis=1, args=(north_bound_line, max_travel_distance)
).tolist()

train_geojson = {"type": "FeatureCollection", "features": features}

# Add TimeDimension
plugins.TimestampedGeoJson(
    train_geojson,
    period="PT20S",
    duration="PT2S",  # Add this line
    add_last_point=False,
    auto_play=False,
    loop=False,
    max_speed=1,
    loop_button=True,
    date_options="YYYY/MM/DD HH:mm:ss",
    time_slider_drag_update=False,
).add_to(m)

legend_html = """
<div style="position: fixed;
     bottom: 80px; left: 50px; width: 200px; height: 100px;
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color: white; padding: 5px;">
     <h4>Passenger Scale</h4>
     <div style="background: linear-gradient(to right, #00ff00, #ff0000);
         width: 100%; height: 10px; border: 1px solid #000;"></div>
     <p style="margin-top: 5px;">Few - Many</p>
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

# Show map map to HTML
m.save("map_with_time_dimension.html")
