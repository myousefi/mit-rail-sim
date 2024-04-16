# Script to process and save geometries
import os

import geopandas as gpd
from dotenv import load_dotenv
from shapely.ops import linemerge

# Change directory
os.chdir("/Users/moji/Projects/mit_rail_sim/mit_rail_sim/dash_app/animation")

# Load environment variables
load_dotenv()

# Read the stations shapefile
stations_shapefile_path = "./assets/cta_rail_lines_and_stations/CTA_RailStations-point.shp"
stations_gdf = gpd.read_file(stations_shapefile_path)
stations_gdf = stations_gdf[stations_gdf["Rail Line"].str.contains("Blue")]

# Read the rail lines shapefile
rail_lines_shapefile_path = "./assets/cta_rail_lines_and_stations/CTA_RailLines-line.shp"
rail_lines_gdf = gpd.read_file(rail_lines_shapefile_path)
rail_lines_gdf = rail_lines_gdf[rail_lines_gdf["ALT_LEGEND"] == "BL"]
rail_lines_gdf = rail_lines_gdf.to_crs(epsg=26916)


# Extract the geometry from the GeoDataFrame
lines = [line for line in rail_lines_gdf.geometry]

# Merge lines
merged_line = linemerge(lines)

# Create parallel lines at 20m distance
north_bound_line = merged_line.parallel_offset(20, side="right")
south_bound_line = merged_line.parallel_offset(20, side="left")

# Create a new GeoDataFrame containing all three lines
all_lines_gdf = gpd.GeoDataFrame(
    {
        "geometry": [merged_line, north_bound_line, south_bound_line],
        "Name": ["Merged", "NorthBound", "SouthBound"],
    },
    crs=rail_lines_gdf.crs,
)

all_lines_gdf = all_lines_gdf.to_crs(epsg=4326)

# Save to shapefile
all_lines_gdf.to_file("./processed_data/all_lines.shp")
stations_gdf.to_file("./processed_data/stations.shp")
