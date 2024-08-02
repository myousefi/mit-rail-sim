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

directory = "/Users/moji/Projects/mit_rail_sim/cta-2024/mid_route_holding_even_more_replications"


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

ORDERED_SCENARIOS_PM = [
    "NO-CONTROL",
    "Pulaski",
    "Racine",
    "UIC-Halsted",
    "Clinton",
    "LaSalle",
    "Jackson",
    "Monroe",
    "Washington",
    "Clark-Lake",
]

data_list_am = []
data_list_pm = []
for key in all_data.keys():
    period, schd, station = key.split(",")
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

df_pm = pd.concat(
    [data[3] for data in data_list_pm],
    keys=pd.MultiIndex.from_tuples(
        [(data[0], data[1], data[2]) for data in data_list_pm],
        names=["period", "schd", "station"],
    ),
).reset_index(names=["period", "schd", "station", "index"])

df_am["station"] = pd.Categorical(
    df_am["station"], categories=ORDERED_SCENARIOS_AM, ordered=True
)
df_am = df_am.sort_values(["period", "schd", "station"]).reset_index(drop=True)

df_pm["station"] = pd.Categorical(
    df_pm["station"], categories=ORDERED_SCENARIOS_PM, ordered=True
)
df_pm = df_pm.sort_values(["period", "schd", "station"]).reset_index(drop=True)


# %%
df_combined = pd.concat([df_am.assign(schd="AM"), df_pm.assign(schd="PM")])

df_combined["period"] = df_combined["period"].replace(
    {
        "version_81": "Winter 2023",
        "version_83": "Spring 2024",
    }
)

# %%
for direction, schd, ordered_scenarios in [
    ("Southbound", "AM", ORDERED_SCENARIOS_AM),
    ("Northbound", "PM", ORDERED_SCENARIOS_PM),
]:
    for period in ["Winter 2023", "Spring 2024"]:
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
            title=f"Denied Boardings by Station - {direction} - {schd} | {period}",
            barmode="group",
            width=1600,
            height=600,
            category_orders={"station": ordered_scenarios},
            text=period_data[0].round(1),
        )

        fig.update_layout(
            xaxis_title="Station",
            yaxis_title="% of Passengers Boarding at Station",
            # uniformtext=dict(
            # mode="hide", minsize=10
            # ),  # Add this line to auto-position the numbers
        )

        fig.show(renderer="browser")
        fig.write_image(
            str(OUTPUT_DIRECTORY / f"denied_boardings_{direction}_{schd}_{period}.svg")
        )
        fig.write_html(
            str(OUTPUT_DIRECTORY / f"denied_boardings_{direction}_{schd}_{period}.html")
        )

# %%
for schd in ["AM", "PM"]:
    df_combined_renamed = df_combined.replace({"station": {"Clark-Lake": "Clark/Lake"}})

    temp = df_combined_renamed.query(
        "period == 'Spring 2024' and schd == @schd and station != 'NO-CONTROL' and station != 'O-Hare' and applied_holding > 0.0"
    )

    station_data = df_combined_renamed.query(
        "period == 'Spring 2024' and schd == @schd and station != 'NO-CONTROL' and station != 'O-Hare' and station_name == station"
    )

    # Determine the station order based on the schedule (AM or PM)
    station_order = ORDERED_SCENARIOS_AM if schd == "AM" else ORDERED_SCENARIOS_PM

    color = "#1F77B4" if schd == "PM" else "#FF7F0E"

    # Calculate the average number of rows with holding per replication_id for each station
    station_counts = (
        temp.groupby(["station", "replication_id"]).size().reset_index(name="count")
    )
    station_counts = (
        station_counts.groupby("station")["count"].mean().reset_index(name="avg_count")
    )

    # Calculate the average percentage of trains with applied_holding > 0 for each station
    station_percentages = (
        station_data.groupby(["station", "replication_id"])
        .agg({"applied_holding": lambda x: (x > 0).mean()})
        .reset_index()
    )
    station_percentages = (
        station_percentages.groupby("station")["applied_holding"]
        .mean()
        .reset_index(name="avg_percentage")
    )

    # Create a DataFrame for the table
    table_data = pd.merge(station_counts, station_percentages, on="station")
    table_data["avg_percentage"] = table_data["avg_percentage"].apply(lambda x: f"{x:.2%}")

    # Convert the 'station' column to a categorical type with the desired order
    table_data["station"] = pd.Categorical(table_data["station"], categories=station_order, ordered=True)

    # Sort the DataFrame based on the 'station' column
    table_data = table_data.sort_values("station")

    print(f"\nAverage Counts and Percentages for {schd} Schedule:")
    print(table_data.to_markdown(index=False))

    table_data.to_clipboard()
    # Create the box plot with a strip plot overlay
    fig = go.Figure()

    fig.add_trace(
        go.Box(
            x=temp["station"],
            y=temp["applied_holding"],
            boxpoints="all",
            jitter=0.3,
            pointpos=-1.8,
            name="Holding Time",
            marker=dict(color=color, size=3),
            boxmean=True,
        )
    )

    # Add annotations for the average number of rows with holding per replication_id
    for _, row in station_counts.iterrows():
        fig.add_annotation(
            x=row["station"],
            y=190,
            text=f"{row['avg_count']:.1f}",
            showarrow=False,
            yshift=10,
            font=dict(size=12),
        )

    # Add annotations for the average percentage of trains with applied_holding > 0
    for _, row in station_percentages.iterrows():
        fig.add_annotation(
            x=row["station"],
            y=190,
            text=f"{row['avg_percentage']:.2%}",
            showarrow=False,
            yshift=-10,
            font=dict(size=12),
        )

    fig.update_layout(
        title=f"Distribution of Holding Times - {schd}",
        # xaxis=dict(title="Station", categoryorder="array", categoryarray=station_order),
        yaxis=dict(title="Holding Time (seconds)"),
        height=600,
        width=1000,
    )

    # Save the plot as an SVG file
    fig.write_image(OUTPUT_DIRECTORY / f"holding_times_{schd}.svg")

    # Display the plot
    fig.show(renderer="browser")

# %%

for schd in ["AM", "PM"]:
    df_combined_renamed = df_combined.replace({"station": {"Clark-Lake": "Clark/Lake"}})

    station_data = df_combined_renamed.query(
        "period == 'Spring 2024' and schd == @schd and station != 'NO-CONTROL' and station != 'O-Hare' and station_name == station and applied_holding > 0"
    )

    # Determine the station order based on the schedule (AM or PM)
    station_order = ORDERED_SCENARIOS_AM.copy() if schd == "AM" else ORDERED_SCENARIOS_PM.copy()

    # Remove O'Hare from station_order if it exists
    if "O-Hare" in station_order:
        station_order.remove("O-Hare")

    # Replace Clark-Lake with Clark/Lake in station_order
    if "Clark-Lake" in station_order:
        station_order[station_order.index("Clark-Lake")] = "Clark/Lake"

    # Remove NO-CONTROL from station_order if it exists
    if "NO-CONTROL" in station_order:
        station_order.remove("NO-CONTROL")

    station_data = station_data[station_data["station"].isin(station_order)]
    
    color = "#1F77B4" if schd == "PM" else "#FF7F0E"

    # Create the box plot
    fig = go.Figure()

    fig.add_trace(
        go.Box(
            x=station_data["station"],
            y=station_data["number_of_passengers_on_train_after_stop"],
            boxpoints="all",
            jitter=0.3,
            pointpos=-1.8,
            name="Number of Passengers Held",
            marker=dict(color=color, size=3),
            boxmean=True,
        )
    )

    # Calculate the average number of passengers held for each station
    passengers_held_avg = station_data.groupby("station")[
        "number_of_passengers_on_train_after_stop"
    ].mean()

    # Add annotations for the average number of passengers held
    for station, avg_passengers in passengers_held_avg.items():
        fig.add_annotation(
            x=station,
            y=station_data[station_data["station"] == station][
                "number_of_passengers_on_train_after_stop"
            ].max(),
            text=f"Avg: {avg_passengers:.1f}",
            showarrow=False,
            yshift=20,
            font=dict(size=12),
        )

    fig.update_layout(
        title=f"Distribution of Number of Passengers Held - {schd}",
        xaxis=dict(title="Station", categoryorder="array", categoryarray=station_order),
        yaxis=dict(title="Number of Passengers Held"),
        height=600,
        width=1000,
    )

    # Create a DataFrame for the table
    table_data = passengers_held_avg.reset_index(drop=False).copy()
    table_data["station"] = pd.Categorical(table_data["station"], categories=station_order, ordered=True)
    table_data = table_data.sort_values("station")

    table_data["number_of_passengers_on_train_after_stop"] = table_data["number_of_passengers_on_train_after_stop"].round(1)
    print(f"\nAverage Number of Passengers Held for {schd} Schedule:")
    print(table_data.to_markdown(index=False))

    table_data.to_clipboard()
    # Save the plot as an SVG file
    fig.write_image(OUTPUT_DIRECTORY / f"passengers_held_distribution_{schd}.svg")

    # Display the plot
    fig.show(renderer="browser")

#TODO copy the information to a table 
# %%
temp = df_combined.query(
    "direction == 'Northbound' and period == 'Spring 2024' and schd == 'PM'"
)

fig = px.box(
    temp,
    facet_row_spacing=0.2,
    x="station_name",
    y="dwell_time",
    facet_col="station",
    facet_col_wrap=2,
    hover_data=temp.columns,
    category_orders={"station": ORDERED_SCENARIOS_PM},
    labels={"dwell_time": "Dwell Time (Sec)", "station_name": "Station Name"},
)

fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig.update_layout(width=1000, height=800)
fig.show(renderer="browser")

# %%
temp = df_combined.query(
    "direction == 'Northbound' and period == 'Spring 2024' and schd == 'PM' and (station == 'UIC-Halsted' or station == 'NO-CONTROL')"
)

fig = px.box(
    temp,
    x="station_name",
    y="number_of_passengers_on_train_after_stop",
    title="Train Loads for Holding at UIC-Halsted and No Control",
    color="station",
    # category_orders={"station": ORDERED_SCENARIOS_PM},
    labels={
        "station": "Scenario",
        "number_of_passengers_on_train_after_stop": "Number of Passengers on Train After Stop",
        "station_name": "Station Name",
    },
)

fig.update_traces(marker=dict(size=3))

fig.update_layout(
    width=1600,
    height=600,
)

fig.update_xaxes(tickangle=45)

# Print the colors used in the figure
colors = fig.data[0].marker.color
print("Colors used in the figure:")
for color in colors:
    print(color)

fig.write_image(OUTPUT_DIRECTORY / "train_loads_uic_halsted_no_control.svg")

fig.show(renderer="browser")

# Save the interactive HTML file to disk
pio.write_html(
    fig,
    OUTPUT_DIRECTORY / "train_loads.html",
)

# %%
# Concatenate the data for all specified scenarios
passenger_df = pd.concat(
    [
        all_data["period=version_83,schd=PM,station=NO-CONTROL"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Pulaski"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Racine"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=UIC-Halsted"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Clinton"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=LaSalle"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Jackson"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Monroe"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Washington"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Clark-Lake"]["passenger_test"],
    ],
    keys=pd.CategoricalIndex(
        ["NO-CONTROL", "Pulaski", "Racine", "UIC-Halsted", "Clinton", 
         "LaSalle", "Jackson", "Monroe", "Washington", "Clark/Lake"],
        categories=["NO-CONTROL", "Pulaski", "Racine", "UIC-Halsted", "Clinton", 
         "LaSalle", "Jackson", "Monroe", "Washington", "Clark/Lake"],
        ordered=True,
    ),
).reset_index(names=["scenario", "index"])


passenger_df["waiting_time"] = passenger_df["waiting_time"] / 60
passenger_df["travel_time"] = passenger_df["travel_time"] / 60
passenger_df["journey_time"] = passenger_df["journey_time"] / 60

passenger_df.head()

# %%
import plotly.express as px

# Filter the data for Northbound direction and the desired scenarios
northbound_data = passenger_df[
    (passenger_df["direction"] == "Northbound")
    & (passenger_df["scenario"].isin(["NO-CONTROL", "UIC-Halsted"]))
]

fig = px.box(
    northbound_data,
    x="origin",
    y="waiting_time",
    color="scenario",
    notched=True,  # show notches
    category_orders={
        "scenario": ["NO-CONTROL", "UIC-Halsted"]
    },  # set the order of scenarios
    labels={
        "waiting_time": "Waiting Time (minutes)",
        "origin": "Origin Station",
        "scenario": "Scenario",
    },
    title="Comparison of Waiting Times: No Control vs UIC-Halsted Holding (Northbound)",
)
fig.update_traces(quartilemethod="inclusive")  # use inclusive method for quartiles
fig.show(renderer="browser")

# %%
temp = passenger_df.query(
    "direction == 'Northbound' and (scenario == 'UIC-Halsted' or scenario == 'NO-CONTROL')"
)

temp["scenario"] = temp["scenario"].astype("str")

# Step 1: Group the data by scenario, origin, and destination
grouped_data = temp.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean wait time for each group
mean_wait_times = grouped_data["waiting_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = temp.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total wait time for each origin and scenario
total_wait_time = (mean_wait_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_wait_time = total_wait_time.reset_index().rename(columns={0: "total_wait_time"})
total_wait_time_pivot = total_wait_time.pivot(index="origin", columns="scenario", values="total_wait_time")

total_wait_time_pivot["Savings (minutes)"] = (
    total_wait_time_pivot["NO-CONTROL"]
    - total_wait_time_pivot["UIC-Halsted"]
)

total_waiting_time_savings = (
    total_wait_time_pivot["NO-CONTROL"].sum()
    - total_wait_time_pivot["UIC-Halsted"].sum()
)

fig = go.Figure(
    data=[
        go.Bar(
            x=total_wait_time_pivot.index,
            y=total_wait_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_wait_time_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Wait Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to NO-CONTROL",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Wait Times (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Wait Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to NO-CONTROL",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Wait Times(minutes)",
)

# Add annotations for total savings in waiting_time and journey_time
fig.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Wait Time Savings: {total_waiting_time_savings:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)


fig.show(renderer="browser")

fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_waiting_time_by_origin_station_Northbound_PM_UIC_NOCONTROL.svg"
    )
)

# %%
import plotly.graph_objects as go

# Filter the data for Clark/Lake and UIC-Halsted scenarios
temp = passenger_df.query(
    "direction == 'Northbound' and (scenario == 'Clark/Lake' or scenario == 'UIC-Halsted')"
)

temp["scenario"] = temp["scenario"].astype("str")

# Step 1: Group the data by scenario, origin, and destination
grouped_data = temp.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean wait time for each group
mean_wait_times = grouped_data["waiting_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = temp.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total wait time for each origin and scenario
total_wait_time = (mean_wait_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_wait_time = total_wait_time.reset_index().rename(columns={0: "total_wait_time"})
total_wait_time_pivot = total_wait_time.pivot(index="origin", columns="scenario", values="total_wait_time")

total_wait_time_pivot["Savings (minutes)"] = (
    total_wait_time_pivot["Clark/Lake"]
    - total_wait_time_pivot["UIC-Halsted"]
)

total_waiting_time_savings = (
    total_wait_time_pivot["Clark/Lake"].sum()
    - total_wait_time_pivot["UIC-Halsted"].sum()
)

fig = go.Figure(
    data=[
        go.Bar(
            x=total_wait_time_pivot.index,
            y=total_wait_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_wait_time_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Wait Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to Clark/Lake",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Wait Times (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Wait Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to Clark/Lake",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Wait Times (minutes)",
)

# Add annotations for total savings in wait_time
fig.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Wait Time Savings: {total_waiting_time_savings:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig.show(renderer="browser")

fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_wait_time_by_origin_station_Northbound_PM_ClarkLake_UIC.svg"
    )
)

# %%
temp = passenger_df.query(
    "direction == 'Northbound' and (scenario == 'UIC-Halsted' or scenario == 'NO-CONTROL')"
)

temp["scenario"] = temp["scenario"].astype("str")
# Step 1: Group the data by scenario, origin, and destination
grouped_data = temp.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean journey time for each group
mean_journey_times = grouped_data["journey_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = temp.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total journey time for each origin and scenario
total_journey_time = (mean_journey_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_journey_time = total_journey_time.reset_index().rename(columns={0: "total_journey_time"})

total_journey_time_pivot = total_journey_time.pivot(index="origin", columns="scenario", values="total_journey_time")

total_journey_time_pivot["Savings (minutes)"] = (
    total_journey_time_pivot["NO-CONTROL"]
    - total_journey_time_pivot["UIC-Halsted"]
)

total_journey_time_savings = (
    total_journey_time_pivot["NO-CONTROL"].sum()
    - total_journey_time_pivot["UIC-Halsted"].sum()
)

fig = go.Figure(
    data=[
        go.Bar(
            x=total_journey_time_pivot.index,
            y=total_journey_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_journey_time_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Journey Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to NO-CONTROL",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Journey Time (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Journey Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to NO-CONTROL",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Journey Times (minutes)",
)


fig.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Journey Time Savings: {total_journey_time_savings:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig.show(renderer="browser")

fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_journey_time_by_origin_station_Northbound_PM_UIC_NOCONTROL.svg"
    )
)

# %%
import plotly.graph_objects as go

# Filter the data for Clark-Lake and UIC-Halsted scenarios
temp = passenger_df.query(
    "direction == 'Northbound' and (scenario == 'Clark/Lake' or scenario == 'UIC-Halsted')"
)

temp["scenario"] = temp["scenario"].astype("str")

# Step 1: Group the data by scenario, origin, and destination
grouped_data = temp.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean journey time for each group
mean_journey_times = grouped_data["journey_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = temp.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total journey time for each origin and scenario
total_journey_time = (mean_journey_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_journey_time = total_journey_time.reset_index().rename(columns={0: "total_journey_time"})

total_journey_time_pivot = total_journey_time.pivot(index="origin", columns="scenario", values="total_journey_time")

total_journey_time_pivot["Savings (minutes)"] = (
    total_journey_time_pivot["Clark/Lake"]
    - total_journey_time_pivot["UIC-Halsted"]
)

total_journey_time_savings = (
    total_journey_time_pivot["Clark/Lake"].sum()
    - total_journey_time_pivot["UIC-Halsted"].sum()
)

fig = go.Figure(
    data=[
        go.Bar(
            x=total_journey_time_pivot.index,
            y=total_journey_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_journey_time_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Journey Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to Clark/Lake",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Journey Time (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Journey Time by Origin Station for Northbound Passengers with UIC-Halsted Control Point Compared to Clark/Lake",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Journey Times (minutes)",
)

# Add annotations for total savings in journey_time
fig.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Journey Time Savings: {total_journey_time_savings:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig.show(renderer="browser")

fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_journey_time_by_origin_station_Northbound_PM_ClarkLake_UIC.svg"
    )
)

# %%

passenger_df = pd.concat(
    [
        all_data["period=version_83,schd=AM,station=NO-CONTROL"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=Chicago"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=Western (O-Hare Branch)"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=Logan Square"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=Irving Park"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=Jefferson Park"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=Cumberland"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=O-Hare"]["passenger_test"]
    ],
    keys=pd.CategoricalIndex(
        ["NO-CONTROL", "Chicago", "Western (O-Hare Branch)", "Logan Square", "Irving Park", "Jefferson Park", "Cumberland", "O-Hare"],
        categories=["NO-CONTROL", "Chicago", "Western (O-Hare Branch)", "Logan Square", "Irving Park", "Jefferson Park", "Cumberland", "O-Hare"],
        ordered=True,
    ),
).reset_index(names=["scenario", "index"])

passenger_df["waiting_time"] = passenger_df["waiting_time"] / 60
passenger_df["travel_time"] = passenger_df["travel_time"] / 60
passenger_df["journey_time"] = passenger_df["journey_time"] / 60

passenger_df.head()

# %%

southbound_data_am = passenger_df.query(
    "direction == 'Southbound' and (scenario == 'NO-CONTROL' or scenario == 'O-Hare')"
)
# Step 1: Group the data by scenario, origin, and destination
grouped_data = southbound_data_am.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the median wait time for each group
mean_wait_times = grouped_data["waiting_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = southbound_data_am.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total wait time for each origin and scenario
total_wait_time = (mean_wait_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_wait_time = total_wait_time.reset_index().rename(columns={0: "total_wait_time"})

total_wait_time_pivot = total_wait_time.pivot(index="origin", columns="scenario", values="total_wait_time")

total_wait_time_pivot

total_wait_time_pivot["Savings (minutes)"] = (
    total_wait_time_pivot["NO-CONTROL"]
    - total_wait_time_pivot["O-Hare"]
)

fig_am_wait = go.Figure(
    data=[
        go.Bar(
            x=total_wait_time_pivot.index,
            y=total_wait_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_wait_time_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Wait Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to NO-CONTROL",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Wait Times (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig_am_wait.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Wait Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to NO-CONTROL",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Wait Times(minutes)",
)

total_waiting_time_savings_am = (
    total_wait_time_pivot["NO-CONTROL"].sum()
    - total_wait_time_pivot["O-Hare"].sum()
)

fig_am_wait.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Wait Time Savings: {total_waiting_time_savings_am:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig_am_wait.show(renderer="browser")

fig_am_wait.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_waiting_time_by_origin_station_Southbound_AM_OHARE_NOCONTROL.svg"
    )
)

# %%
southbound_data_am = passenger_df.query(
    "direction == 'Southbound' and (scenario == 'Jefferson Park' or scenario == 'O-Hare')"
)

# Step 1: Group the data by scenario, origin, and destination
grouped_data = southbound_data_am.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean wait time for each group
mean_wait_times = grouped_data["waiting_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = southbound_data_am.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total wait time for each origin and scenario
total_wait_time = (mean_wait_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_wait_time = total_wait_time.reset_index().rename(columns={0: "total_wait_time"})

total_wait_time_pivot = total_wait_time.pivot(index="origin", columns="scenario", values="total_wait_time")

total_wait_time_pivot["Savings (minutes)"] = (
    total_wait_time_pivot["Jefferson Park"]
    - total_wait_time_pivot["O-Hare"]
)

fig_am_wait = go.Figure(
    data=[
        go.Bar(
            x=total_wait_time_pivot.index,
            y=total_wait_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_wait_time_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Wait Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to Jefferson Park",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Wait Times (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig_am_wait.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Wait Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to Jefferson Park",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Wait Times (minutes)",
)

total_waiting_time_savings_am = (
    total_wait_time_pivot["Jefferson Park"].sum()
    - total_wait_time_pivot["O-Hare"].sum()
)

fig_am_wait.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Wait Time Savings: {total_waiting_time_savings_am:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig_am_wait.show(renderer="browser")

fig_am_wait.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_waiting_time_by_origin_station_Southbound_AM_JEFFERSONPARK_OHARE.svg"
    )
)


# %%
southbound_data_am = passenger_df.query(
    "direction == 'Southbound' and (scenario == 'NO-CONTROL' or scenario == 'O-Hare')"
)

# Step 1: Group the data by scenario, origin, and destination
grouped_data = southbound_data_am.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean journey time for each group
mean_journey_times = grouped_data["journey_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = southbound_data_am.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total journey time for each origin and scenario
total_journey_time = (mean_journey_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_journey_time = total_journey_time.reset_index().rename(columns={0: "total_journey_time"})

total_journey_time_pivot = total_journey_time.pivot(index="origin", columns="scenario", values="total_journey_time")

total_journey_time_pivot["Savings (minutes)"] = (
    total_journey_time_pivot["NO-CONTROL"]
    - total_journey_time_pivot["O-Hare"]
)



total_journey_time_savings_am = (
    total_journey_time_pivot["NO-CONTROL"].sum()
    - total_journey_time_pivot["O-Hare"].sum()
)

fig_am_journey = go.Figure(
    data=[
        go.Bar(
            x=total_journey_time_pivot.index,
            y=total_journey_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_journey_time_pivot[
                    "Savings (minutes)"
                ]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Journey Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to NO-CONTROL",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Journey Time (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig_am_journey.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Journey Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to NO-CONTROL",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Journey Times (minutes)",
)

fig_am_journey.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Journey Time Savings: {total_journey_time_savings_am:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig_am_journey.show(renderer="browser")

fig_am_journey.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_journey_time_by_origin_station_Southbound_AM_OHARE_NOCONTROL.svg"
    )
)
# %%
southbound_data_am = passenger_df.query(
    "direction == 'Southbound' and (scenario == 'Jefferson Park' or scenario == 'O-Hare')"
)

# Step 1: Group the data by scenario, origin, and destination
grouped_data = southbound_data_am.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean journey time for each group
mean_journey_times = grouped_data["journey_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = southbound_data_am.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total journey time for each origin and scenario
total_journey_time = (mean_journey_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_journey_time = total_journey_time.reset_index().rename(columns={0: "total_journey_time"})

total_journey_time_pivot = total_journey_time.pivot(index="origin", columns="scenario", values="total_journey_time")

total_journey_time_pivot["Savings (minutes)"] = (
    total_journey_time_pivot["Jefferson Park"]
    - total_journey_time_pivot["O-Hare"]
)

total_journey_time_savings_am = (
    total_journey_time_pivot["Jefferson Park"].sum()
    - total_journey_time_pivot["O-Hare"].sum()
)

fig_am_journey = go.Figure(
    data=[
        go.Bar(
            x=total_journey_time_pivot.index,
            y=total_journey_time_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in total_journey_time_pivot[
                    "Savings (minutes)"
                ]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Journey Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to Jefferson Park",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Journey Time (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig_am_journey.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Savings in Total Daily Journey Time by Origin Station for Southbound Passengers with O'Hare Control Point Compared to Jefferson Park",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Journey Times (minutes)",
)

fig_am_journey.add_annotation(
    x=0.01,
    y=1.1,
    xanchor="left",
    xref="paper",
    yref="paper",
    text=f"Total Journey Time Savings: {total_journey_time_savings_am:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig_am_journey.show(renderer="browser")

fig_am_journey.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_journey_time_by_origin_station_Southbound_AM_OHARE_JEFFERSONPARK.svg"
    )
)

# %%
# Group by scenario, origin, and replication_id, and count the passenger_ids
daily_total_passengers_boarded_by_origin_am = (
    southbound_data_am.groupby(["scenario", "origin", "replication_id"])
    .agg(passengers_boarded=("passenger_id", "count"))
    .reset_index()
    .query("passengers_boarded > 0")
)

# Calculate the mean number of passengers boarded for each scenario and origin
daily_total_passengers_boarded_by_origin_am = (
    daily_total_passengers_boarded_by_origin_am.groupby(["scenario", "origin"])
    .agg(passengers_boarded=("passengers_boarded", "mean"))
    .reset_index()
)

# Create the bar plot with two traces (one for each scenario)
fig_am_passengers_boarded = go.Figure(
    data=[
        go.Bar(
            name=scenario,
            x=daily_total_passengers_boarded_by_origin_am[
                daily_total_passengers_boarded_by_origin_am["scenario"] == scenario
            ]["origin"],
            y=daily_total_passengers_boarded_by_origin_am[
                daily_total_passengers_boarded_by_origin_am["scenario"] == scenario
            ]["passengers_boarded"],
            text=[
                f"{y:.0f}"
                for y in daily_total_passengers_boarded_by_origin_am[
                    daily_total_passengers_boarded_by_origin_am["scenario"] == scenario
                ]["passengers_boarded"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
        for scenario in daily_total_passengers_boarded_by_origin_am["scenario"].unique()
    ],
    layout=go.Layout(
        title=dict(
            text="Average Number of Passengers Boarded by Origin Station (Southbound)",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Number of Passengers Boarded", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig_am_passengers_boarded.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Average Number of Passengers Boarded by Origin Station (Southbound)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Number of Passengers Boarded",
    barmode="group",
)

fig_am_passengers_boarded.show(renderer="browser")

fig_am_passengers_boarded.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"average_number_of_passengers_boarded_by_origin_station_Southbound_AM_OHARE_NOCONTROL.svg"
    )
)

# %%
import plotly.express as px

southbound_data_am = passenger_df.query(
    "direction == 'Southbound' and (scenario == 'NO-CONTROL' or scenario == 'O-Hare')"
)

southbound_data_am.set_index(["origin", "destination", "scenario", "replication_id"], inplace=True)

# Filter the data for Southbound direction, origin at Harlem (O-Hare Branch), and the desired scenarios
harlem_southbound_data = southbound_data_am[
    (southbound_data_am.index.get_level_values("origin") == "Harlem (O-Hare Branch)")
]

fig = px.box(
    harlem_southbound_data.reset_index(),
    x="destination",
    y="journey_time",
    color="scenario",
    category_orders={
        "scenario": ["NO-CONTROL", "O-Hare"]
    },  # set the order of scenarios
    labels={
        "journey_time": "Journey Time (minutes)",
        "destination": "Destination Station",
        "scenario": "Scenario",
    },
    title="Comparison of Journey Times from Harlem (O-Hare Branch) to Southbound Stations",
)

fig.update_layout(
    xaxis=dict(
        tickangle=45,
        title_text="Destination Station",
        title_font={"size": 14},
        tickfont={"size": 12},
    ),
    yaxis=dict(
        title_text="Journey Time (minutes)",
        title_font={"size": 14},
        tickfont={"size": 12},
    ),
    legend=dict(title_text="Scenario", title_font={"size": 14}, font={"size": 12}),
)

fig.show(renderer="browser")

# %%
import plotly.express as px

# Filter the data for Southbound direction, origin at O'Hare, and the desired scenarios
ohare_southbound_data = southbound_data_am[
    (southbound_data_am.index.get_level_values("origin") == "O-Hare")
]

fig = px.box(
    ohare_southbound_data.reset_index(),
    x="destination",
    y="journey_time",
    color="scenario",
    category_orders={
        "scenario": ["NO-CONTROL", "O-Hare"]
    },  # set the order of scenarios
    labels={
        "journey_time": "Journey Time (minutes)",
        "destination": "Destination Station",
        "scenario": "Scenario",
    },
    title="Comparison of Journey Times from O'Hare to Southbound Stations",
)

fig.update_layout(
    xaxis=dict(
        tickangle=45,
        title_text="Destination Station",
        title_font={"size": 14},
        tickfont={"size": 12},
    ),
    yaxis=dict(
        title_text="Journey Time (minutes)",
        title_font={"size": 14},
        tickfont={"size": 12},
    ),
    legend=dict(title_text="Scenario", title_font={"size": 14}, font={"size": 12}),
)

fig.show(renderer="browser")

# %%
import plotly.graph_objects as go

# Filter the data for Southbound direction, origin at O'Hare, and the desired scenarios
ohare_southbound_data = southbound_data_am[
    (southbound_data_am.index.get_level_values("origin") == "Harlem (O-Hare Branch)")
]

# Calculate the median journey times for each scenario and destination
median_journey_times = ohare_southbound_data.reset_index().groupby(["scenario", "destination"])["journey_time"].mean().unstack().T

# Calculate the difference in median journey times between NO-CONTROL and O-Hare scenarios
median_diff = median_journey_times["NO-CONTROL"] - median_journey_times["O-Hare"]

# Create a bar plot
fig = go.Figure(
    data=[
        go.Bar(
            x=median_diff.index,
            y=median_diff.values,
            text=[f"{y:.2f}" for y in median_diff.values],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Difference in Mean Journey Times (NO-CONTROL - O'Hare)",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Difference in Median Journey Time (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Difference in Mean Journey Times (NO-CONTROL - O'Hare)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Destination Station",
    yaxis_title="Difference in Median Journey Time (minutes)",
)

fig.show(renderer="browser")

# %%
import plotly.graph_objects as go

# Filter the data for Southbound direction, origin at Harlem (O-Hare Branch), and the desired scenarios
harlem_southbound_data = southbound_data_am[
    (southbound_data_am.index.get_level_values("origin") == "Harlem (O-Hare Branch)")
]

# Calculate the sum of journey times for each scenario, destination, and replication_id
sum_journey_times = harlem_southbound_data.reset_index().groupby(["scenario", "destination", "replication_id"])["journey_time"].sum().reset_index()

# Calculate the average sum of journey times over replication_ids for each scenario and destination
avg_sum_journey_times = sum_journey_times.groupby(["scenario", "destination"])["journey_time"].mean().unstack().T


# Calculate the difference in average sum of journey times between NO-CONTROL and O-Hare scenarios
avg_sum_diff = avg_sum_journey_times["NO-CONTROL"] - avg_sum_journey_times["O-Hare"]

# Create a bar plot
fig = go.Figure(
    data=[
        go.Bar(
            x=avg_sum_diff.index,
            y=avg_sum_diff.values,
            text=[f"{y:.2f}" for y in avg_sum_diff.values],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Difference in Average Sum of Journey Times (NO-CONTROL - O'Hare)",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Difference in Average Sum of Journey Times (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
    ),
)

fig.update_layout(
    width=1600,
    height=600,
    plot_bgcolor="white",
    title={
        "text": "Difference in Average Sum of Journey Times (NO-CONTROL - O'Hare)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Destination Station",
    yaxis_title="Difference in Average Sum of Journey Times (minutes)",
)

fig.show(renderer="browser")

# %%
import plotly.graph_objects as go

# Filter the data for Southbound direction, origin at Harlem (O-Hare Branch), and the desired scenarios
harlem_southbound_data = southbound_data_am[
    (southbound_data_am.index.get_level_values("origin") == "Harlem (O-Hare Branch)")
]

harlem_southbound_data.groupby("scenario").agg(
    {"waiting_time": "sum", "journey_time": "sum"}
)



# %%
import pandas as pd

# Step 1: Group the data by scenario, origin, and destination
grouped_data = southbound_data_am.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the median wait time for each group
mean_wait_times = grouped_data["waiting_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = southbound_data_am.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total wait time for each origin and scenario
total_wait_time = (mean_wait_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_wait_time = total_wait_time.reset_index().rename(columns={0: "total_wait_time"})

total_wait_time_pivot = total_wait_time.pivot(index="origin", columns="scenario", values="total_wait_time")

total_wait_time_pivot



# %%
import pandas as pd
import itertools

scenarios = ORDERED_SCENARIOS_AM

passenger_df = pd.concat(
    [all_data[f"period=version_83,schd=AM,station={station}"]["passenger_test"] for station in scenarios],
    keys=scenarios,
).reset_index(names=["scenario", "index"])
        
temp = passenger_df.query(
    "direction == 'Southbound' and scenario in @scenarios"
)

temp["scenario"] = temp["scenario"].astype("str")

# Step 1: Group the data by scenario, origin, and destination
grouped_data = temp.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean wait time for each group
mean_wait_times = grouped_data["waiting_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = temp.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total wait time for each origin and scenario
total_wait_time = (mean_wait_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_wait_time = total_wait_time.reset_index().rename(columns={0: "total_wait_time"})

total_wait_time_pivot = total_wait_time.pivot(index="origin", columns="scenario", values="total_wait_time").T

# Step 6: Calculate the savings between each pair of scenarios
savings_df = pd.DataFrame(index=scenarios, columns=scenarios)

for scenario1, scenario2 in itertools.combinations(scenarios, 2):
    savings_df.loc[scenario1, scenario2] = (
        total_wait_time_pivot.loc[scenario1].sum()
        - total_wait_time_pivot.loc[scenario2].sum()
    )
    savings_df.loc[scenario2, scenario1] = (
        total_wait_time_pivot.loc[scenario2].sum()
        - total_wait_time_pivot.loc[scenario1].sum()
    )

savings_df.head()

# %%


