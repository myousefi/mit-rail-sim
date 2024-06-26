# %%
import glob
import os
from pathlib import Path
import stat

import pandas as pd
import plotly.io as pio

from mit_rail_sim.utils.root_path import project_root

pio.templates.default = "simple_white"
# pio.renderers.default = "browser"

import os

import plotly.express as px
import plotly.graph_objects as go

from mit_rail_sim.validation.validation_dash import STATION_ORDER


def read_csv_files_in_subdir(subdir_path):
    csv_files = glob.glob(os.path.join(subdir_path, "*.csv"))
    data_frames = {}

    for file in csv_files:
        if "passenger_test.csv" in file:
            df = pd.read_csv(file)

            # set the origin and destination station orders
            df = df[df["origin"].isin(STATION_ORDER)]
            df["origin"] = df["origin"].astype("category")
            df["origin"] = df["origin"].cat.set_categories(STATION_ORDER, ordered=True)

            df = df[df["destination"].isin(STATION_ORDER)]
            df["destination"] = df["destination"].astype("category")
            df["destination"] = df["destination"].cat.set_categories(
                STATION_ORDER, ordered=True
            )

            df = df.sort_values(["origin", "destination"])
            data_frames["passenger_test"] = df

        elif "station_test.csv" in file:
            df = pd.read_csv(file)
            df["station_name"] = df["station_name"].astype("category")
            df["station_name"] = df["station_name"].cat.set_categories(
                STATION_ORDER, ordered=True
            )
            df = df.sort_values(["station_name"])

            data_frames["station_test"] = df

        elif "block_test.csv" in file:
            data_frames["block_test"] = pd.read_csv(file)

    return data_frames


# directory = Path()

directory = "/Users/moji/Projects/mit_rail_sim/cta-2024/holding-spring-am-artificail-demand-increase"


subdirs = [d for d in glob.glob(os.path.join(directory, "**/")) if os.path.isdir(d)]
all_data = {}

if subdirs:
    for subdir in subdirs:
        subdir_name = os.path.basename(os.path.normpath(subdir))
        all_data[subdir_name] = read_csv_files_in_subdir(subdir)
else:
    all_data["experiment"] = read_csv_files_in_subdir(directory)

for subdir, data_frames in all_data.items():
    print(f"Subdirectory: {subdir}")
    for df_name, df in data_frames.items():
        print(f"Data frame: {df_name}, Shape: {df.shape}")

print(all_data.keys())

# %%
OUTPUT_DIRECTORY = Path(
    "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"
)

# %%
ORDERED_SCENARIOS_AM = [
    "NO-CONTROL",
    "Chicago",
    "Western (O-Hare Branch)",
    "Logan Square",
    "Irving Park",
    "Jefferson Park",
    "Cumberland",
    "O-Hare",
]


data_list_am = []
data_list_pm = []
for key in all_data.keys():
    _, period, _, schd, station = key.split(",")
    _, period_value = period.split("=")
    _, schd_value = schd.split("=")
    _, station_value = station.split("=")
    if schd_value == "AM":
        data_list_am.append(
            (period_value, schd_value, station_value, all_data[key]["station_test"])
        )
    else:
        data_list_pm.append(
            (period_value, schd_value, station_value, all_data[key]["station_test"])
        )

df_am = pd.concat(
    [data[3] for data in data_list_am],
    keys=pd.MultiIndex.from_tuples(
        [(data[0], data[1], data[2]) for data in data_list_am],
        names=["period", "schd", "station"],
    ),
).reset_index(names=["period", "schd", "station", "index"])

df_am["station"] = pd.Categorical(
    df_am["station"], categories=ORDERED_SCENARIOS_AM, ordered=True
)
df_am = df_am.sort_values(["period", "schd", "station"]).reset_index(drop=True)


# %%
# df_combined = pd.concat([df_am.assign(schd="AM"), df_pm.assign(schd="PM")])
df_combined = df_am.assign(schd="AM")

df_combined["period"] = df_combined["period"].replace(
    {
        "version_81": "Winter 2023",
        "version_83": "Spring 2024",
    }
)

# %%
for direction, schd, ordered_scenarios in [
    ("Southbound", "AM", ORDERED_SCENARIOS_AM),
]:
    for period in ["Spring 2024"]:
        period_data = df_combined[
            (df_combined["schd"] == schd)
            & (df_combined["period"] == period)
            & (df_combined["direction"] == direction)
        ]

        total_passengers = period_data.groupby(["station", "station_name"])[
            "number_of_passengers_boarded"
        ].sum()
        denied_boardings = period_data.groupby(["station", "station_name"])[
            "denied_boarding"
        ].sum()
        percentage_denied_boardings = (denied_boardings / total_passengers) * 100

        percentage_denied_boardings = percentage_denied_boardings.reset_index()

        non_zero_stations = percentage_denied_boardings[
            percentage_denied_boardings[0] > 0
        ]["station_name"].unique()
        period_data = percentage_denied_boardings[
            percentage_denied_boardings["station_name"].isin(non_zero_stations)
        ]

        fig = px.bar(
            period_data,
            x="station_name",
            y=0,
            color="station",
            labels={
                "denied_boarding": "Percentage of Denied Boardings",
                "station_name": "Station",
                "station": "Scenario",
            },
            title=f"Denied Boardings by Station - {direction} - {schd} | {period} (25% Uniform Increase in Demand)",
            barmode="group",
            width=1000,
            height=600,
            category_orders={"station": ordered_scenarios},
        )

        fig.update_layout(
            xaxis_title="Station",
            yaxis_title="% of Passengers Boarding at Station",
        )

        fig.show(renderer="browser")
        fig.write_image(
            str(
                OUTPUT_DIRECTORY
                / f"am_artificial_demand_denied_boardings_{direction}_{schd}_{period}.svg"
            )
        )
        fig.write_html(
            str(
                OUTPUT_DIRECTORY
                / f"am_artificial_demand_denied_boardings_{direction}_{schd}_{period}.html"
            )
        )

# %%
