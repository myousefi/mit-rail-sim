import json

import pandas as pd
import plotly.express as px

track_df = pd.read_csv("./data/track_events.csv", parse_dates=["event_time"])
sim_df = pd.read_csv("./simulation_results/block_test.csv")

# Step 1: Create a list of all blocks associated with stations and the blocks that come immediately after them
with open("../../alt_file_northbound_updated.json", "r") as f:
    data = json.load(f)
    station, start, end = [], [], []
    for i, block in enumerate(data[:-1]):
        if "STATION" in block:
            start.append(block["BLOCK_ALT"])
            end.append(data[i + 2]["BLOCK_ALT"])
            station.append(block["STATION"]["STATION_NAME"])

run_time_blocks = {}

for i, station in enumerate(station[:-1]):
    run_time_blocks[station] = (end[i], start[i + 1])

print(run_time_blocks)
