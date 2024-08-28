import json

import pandas as pd

df = pd.read_csv("transit_lab_simmetro/validation/data/events.csv")[
    ["station", "scada", "locationdesc"]
]

# keep only unique combinations of station and scada and locationdesc
df = df.drop_duplicates(subset=["station", "scada", "locationdesc"])

rail_data = json.load(open("file.json", "r"))

station_list = []
for block in rail_data:
    if "STATION" in block:
        station_list.append((block["STATION"]["STATION_NAME"], block["BLOCK"]))

stations_dict = {station: block for station, block in station_list}

print(stations_dict)
stations = pd.DataFrame(station_list, columns=["station", "block"])

# merge the two dataframes
df = df.merge(stations, on="station")

# sort df according to station names as they appear in the station_list
df["station"] = pd.Categorical(df["station"], categories=stations["station"].unique())
df = df.sort_values("station")

df["matching"] = df.apply(
    lambda row: str(row["block"]).replace("-", "").lower() in str(row["scada"]).lower(),
    axis=1,
)


df.to_clipboard(index=True)
print(df)
