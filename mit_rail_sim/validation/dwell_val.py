import json
from datetime import datetime

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html
from pandas.tseries.holiday import USFederalHolidayCalendar

from mit_rail_sim.utils import find_free_port, project_root

# Constants
STATION_ORDER = [
    "Forest Park",
    "Harlem (Forest Park Branch)",
    "Oak Park",
    "Austin",
    "Cicero",
    "Pulaski",
    "Kedzie-Homan",
    "Western (Forest Park Branch)",
    "Illinois Medical District",
    "Racine",
    "UIC-Halsted",
    "Clinton",
    "LaSalle",
    "Jackson",
    "Monroe",
    "Washington",
    "Clark/Lake",
    "Grand",
    "Chicago",
    "Division",
    "Damen",
    "Western (O-Hare Branch)",
    "California",
    "Logan Square",
    "Belmont",
    "Addison",
    "Irving Park",
    "Montrose",
    "Jefferson Park",
    "Harlem (O-Hare Branch)",
    "Cumberland",
    "Rosemont",
    "O-Hare",
]

STATION_BLOCK = {
    "Forest Park": "wc461t",
    "Harlem (Forest Park Branch)": "wc444t",
    "Oak Park": "wc401t",
    "Austin": "wc361t",
    "Cicero": "wc279t",
    "Pulaski": "wc225t",
    "Kedzie-Homan": "wc172t",
    "Western (Forest Park Branch)": "wc117t",
    "Illinois Medical District": "wc075t",
    "Racine": "wc035t",
    "UIC-Halsted": "wc008t",
    "Clinton": "dc014t",
    "LaSalle": "dc036t",
    "Jackson": "dc056t",
    "Monroe": "dc066t",
    "Washington": "dc075t",
    "Clark/Lake": "dc088t",
    "Grand": "dc138t",
    "Chicago": "dc164t",
    "Division": "dc210t",
    "Damen": "ln1232t",
    "Western (O-Hare Branch)": "ln1269t",
    "California": "ln1301t",
    "Logan Square": "nwc110t",
    "Belmont": "nwc146t",
    "Addison": "nwc185t",
    "Irving Park": "nwc218t",
    "Montrose": "nwc270t",
    "Jefferson Park": "nwc325t",
    "Harlem (O-Hare Branch)": "nwc468t",
    "Cumberland": "nwc547t",
    "Rosemont": "nwc606t",
    "O-Hare": "nwc724t",
}

RUN_TIME_BLOCKS = {
    "Forest Park": ("wc461t", "wc444t"),
    "Harlem (Forest Park Branch)": ("wc434", "wc401t"),
    "Oak Park": ("wc387t", "wc361t"),
    "Austin": ("wc350t", "wc279t"),
    "Cicero": ("wc266t", "wc225t"),
    "Pulaski": ("wc216", "wc172t"),
    "Kedzie-Homan": ("wc162", "wc117t"),
    "Western (Forest Park Branch)": ("wc108", "wc075t"),
    "Illinois Medical District": ("wc063t", "wc035t"),
    "Racine": ("wc030", "wc008t"),
    "UIC-Halsted": ("wc003t", "dc014t"),
    "Clinton": ("dc023t", "dc036t"),
    "LaSalle": ("dc044t", "dc056t"),
    "Jackson": ("dc061t", "dc066t"),
    "Monroe": ("dc072t", "dc075t"),
    "Washington": ("dc082t", "dc088t"),
    "Clark/Lake": ("dc099t", "dc138t"),
    "Grand": ("dc145t", "dc164t"),
    "Chicago": ("dc171t", "dc210t"),
    "Division": ("dc215t", "ln1232t"),
    "Damen": ("ln1240t", "ln1269t"),
    "Western (O-Hare Branch)": ("ln1273", "ln1301t"),
    "California": ("ln1310t", "nwc110t"),
    "Logan Square": ("nwc118t", "nwc146t"),
    "Belmont": ("nwc154t", "nwc185t"),
    "Addison": ("nwc189", "nwc218t"),
    "Irving Park": ("nwc225t", "nwc270t"),
    "Montrose": ("nwc278t", "nwc325t"),
    "Jefferson Park": ("nwc332t", "nwc468t"),
    "Harlem (O-Hare Branch)": ("nwc486t", "nwc547t"),
    "Cumberland": ("nwc561t", "nwc606t"),
    "Rosemont": ("nwc615t", "nwc724t"),
    "O-Hare": (None, None),
}


# Utility Functions
def filter_by_time_and_weekday(df, start_time, end_time):
    return df[
        (df["event_datetime"].dt.time >= start_time)
        & (df["event_datetime"].dt.time <= end_time)
        & (df["weekday"] < 5)
    ].copy()


def remove_holidays(df):
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(
        start=df["event_datetime"].min(), end=df["event_datetime"].max()
    )
    return df[~df["event_datetime"].dt.date.isin(holidays)].copy()


app = Dash(__name__)
app.title = "Dwell Validation"

app.layout = html.Div(
    [
        dcc.Dropdown(
            id="station-selector",
            options=[{"label": station, "value": station} for station in STATION_ORDER],
            value="Clark/Lake",  # default value
        ),
        dcc.Graph(id="dwell-plot"),
    ]
)


@app.callback(Output("dwell-plot", "figure"), [Input("station-selector", "value")])
def update_plot(selected_station):
    global dwell
    global dwell_scatter
    dwell_s = dwell[dwell["station"] == selected_station].copy()
    dwell_ind = dwell_scatter[dwell_scatter["station"] == selected_station].copy()
    fig = px.line(dwell_s, x="time", y="duration", color="source")
    fig = px.scatter(dwell_ind, x="time", y="duration", color="source")

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Dwell Duration (minutes)",
        title=f"Dwell Duration at {selected_station}",
        legend_title="Data Source",
    )
    return fig


if __name__ == "__main__":
    # Data Preparation
    merged_data = pd.read_csv("./data/track_events.csv", parse_dates=["event_time"])
    merged_data["event_datetime"] = pd.to_datetime(merged_data["event_time"])
    merged_data["weekday"] = merged_data["event_datetime"].dt.weekday
    merged_data["date"] = merged_data["event_datetime"].dt.date
    merged_data = merged_data[
        (merged_data["event_datetime"].dt.date >= datetime(2023, 4, 15).date())
        & (merged_data["event_datetime"].dt.date <= datetime(2023, 4, 30).date())
    ]

    # merged_data["event_time"] = merged_data["event_datetime"]
    merged_data.sort_values(by=["event_datetime"], inplace=True)
    track_df = merged_data.copy()

    two_next_scada = {}
    with open(project_root / "alt_file_northbound_updated.json", "r") as f:
        blocks = json.load(f)
        for index, block in enumerate(blocks):
            try:
                two_next_scada[block["BLOCK_ALT"]] = blocks[index + 2]["BLOCK_ALT"]
            except IndexError:
                break

    merged_data["dwell_arrtodep"] = (
        abs(merged_data.groupby(["date", "run_id"])["event_time"].diff(-2)).dt.seconds
        / 60
    )

    merged_data["next_scada"] = merged_data["scada"].map(two_next_scada)

    def calc_dwell(group):
        group["dwell_arrtodep"] = abs(group["event_time"].diff(-2)).dt.seconds / 60
        group["consecutive_scada"] = group["next_scada"].eq(group["scada"].shift(-2))
        return group

    merged_data = merged_data.groupby(["date", "run_id"], as_index=False).apply(
        calc_dwell
    )

    # merged_data["consecutive_scada"] = merged_data.groupby(["date", "run_id"])[merged_data["scada"].shift(-2).eq(merged_data["next_scada"])]

    merged_data = merged_data[merged_data["scada"].isin(STATION_BLOCK.values())]
    merged_data = merged_data[merged_data["consecutive_scada"]]

    merged_data["station"] = merged_data["scada"].map(
        {v: k for k, v in STATION_BLOCK.items()}
    )

    # print(merged_data.head())

    simulation_results = pd.read_csv("./simulation_results/station_test.csv")
    block_test = pd.read_csv("./simulation_results/block_test.csv")

    # Step 1: Add difference_in_activation column to block_test
    block_test.sort_values(
        by=["replication_id", "train_id", "time_in_seconds"], inplace=True
    )
    block_test["difference_in_activation"] = -block_test.groupby(
        ["replication_id", "train_id"]
    )["time_in_seconds"].diff(-2)

    # Create a new column in station_test dataframe to hold the corresponding block_id values
    simulation_results["block_id"] = simulation_results["station_name"].map(
        STATION_BLOCK
    )

    # Merge the dataframes on replication_id, train_id and block_id
    simulation_results = pd.merge(
        simulation_results,
        block_test,
        on=["replication_id", "train_id", "block_id"],
        how="left",
        suffixes=("_station", ""),
    )

    simulation_results.dropna(inplace=True)

    simulation_results.to_csv(
        project_root
        / "mit_rail_sim"
        / "validation"
        / "simulation_results"
        / "simulation_merged.csv",
        index=False,
    )
    print("saved")
    simulation_results["headway"] = simulation_results["headway"] / 60
    simulation_results["dwell_time"] = simulation_results["dwell_time"] / 60
    simulation_results["difference_in_activation"] = (
        simulation_results["difference_in_activation"] / 60
    )

    simulation_results.rename(columns={"station_name": "station"}, inplace=True)

    simulation_results["time"] = pd.to_timedelta(
        simulation_results["time_in_seconds"], unit="s"
    ) + pd.Timestamp("2023-04-15")

    merged_data["time"] = (
        merged_data["event_datetime"] - merged_data["event_datetime"].dt.normalize()
    ) + pd.Timestamp("2023-04-15")
    # simulation_results["event_time"] = (
    #     simulation_results["event_time"] - simulation_results["event_time"].dt.normalize()
    # )

    merged_data.reset_index(inplace=True)
    # dwells = pd.DataFrame(columns=["time", "station", "source"])
    # dwells.set_index(["time", "station"], inplace=True)

    dwell = pd.concat(
        [
            simulation_results.groupby(
                [pd.Grouper(key="time", freq="30min", origin="epoch"), "station"]
            )["difference_in_activation"].mean(),
            merged_data.groupby(
                [pd.Grouper(key="time", freq="30min", origin="epoch"), "station"]
            )["dwell_arrtodep"].mean(),
            # simulation_results.groupby(
            #     [pd.Grouper(key="time", freq="30min", origin="epoch"), "station"]
            # )["dwell_time"].mean(),
        ],
        keys=["Simulation Data", "Real World Data"],
        # , "Dwell Model"],
    ).reset_index(name="duration")

    dwell.rename(
        columns={
            "level_0": "source",
            "level_1": "time",
            "level_2": "station",
            # "0: "duration",
        },
        inplace=True,
    )

    dwell_scatter = (
        pd.concat(
            [
                simulation_results[
                    ["time", "station", "difference_in_activation"]
                ].rename(columns={"difference_in_activation": "duration"}),
                merged_data[["time", "station", "dwell_arrtodep"]].rename(
                    columns={"dwell_arrtodep": "duration"}
                ),
                # simulation_results[["time", "station", "dwell_time"]].rename(
                #     columns={"dwell_time": "duration"}
                # ),
            ],
            keys=["Simulation Data", "Real World Data"],
            # "Dwell Model"],
        )
        .reset_index(level=0)
        .rename(columns={"level_0": "source"})
    )

    app.run_server(debug=True, port=find_free_port())
