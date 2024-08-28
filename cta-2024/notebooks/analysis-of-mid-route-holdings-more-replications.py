# %%
import glob
import os
from pathlib import Path

import pandas as pd
import plotly.io as pio


pio.templates.default = "simple_white"
# pio.renderers.default = "browser"


import plotly.express as px
import plotly.graph_objects as go

from transit_lab_simmetro.validation.validation_dash import STATION_ORDER


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

directory = "/Users/moji/Projects/transit_lab_simmetro/cta-2024/mid_route_holding_more_replications"


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
    "LaSalle",
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
            width=1000,
            height=600,
            category_orders={"station": ordered_scenarios},
            text=period_data[0].round(2),
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
import pandas as pd

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
    table_data["avg_percentage"] = table_data["avg_percentage"].apply(
        lambda x: f"{x:.2%}"
    )
    print(f"\nAverage Counts and Percentages for {schd} Schedule:")
    print(table_data.to_markdown(index=False))

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
            marker=dict(color=color),
            boxmean=True,
        )
    )

    # Add annotations for the average number of rows with holding per replication_id
    for _, row in station_counts.iterrows():
        fig.add_annotation(
            x=row["station"],
            y=190,
            text=f"Avg: {row['avg_count']:.1f}",
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
    station_order = ORDERED_SCENARIOS_AM if schd == "AM" else ORDERED_SCENARIOS_PM

    # Remove O'Hare from station_order if it exists
    if "O-Hare" in station_order:
        station_order.remove("O-Hare")

    # Replace Clark-Lake with Clark/Lake in station_order
    if "Clark-Lake" in station_order:
        station_order[station_order.index("Clark-Lake")] = "Clark/Lake"

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
            marker=dict(color=color),
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

    # Save the plot as an SVG file
    fig.write_image(OUTPUT_DIRECTORY / f"passengers_held_distribution_{schd}.svg")

    # Display the plot
    fig.show(renderer="browser")

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
    category_orders={"station": ORDERED_SCENARIOS_PM},
    labels={
        "station": "Scenario",
        "number_of_passengers_on_train_after_stop": "Number of Passengers on Train After Stop",
        "station_name": "Station Name",
    },
)

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
passenger_df = pd.concat(
    [
        all_data["period=version_83,schd=PM,station=Clark-Lake"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=LaSalle"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=UIC-Halsted"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Racine"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=Pulaski"]["passenger_test"],
        all_data["period=version_83,schd=PM,station=NO-CONTROL"]["passenger_test"],
    ],
    keys=pd.CategoricalIndex(
        ["Clark-Lake", "LaSalle", "UIC-Halsted", "Racine", "Pulaski", "NO-CONTROL"],
        categories=ORDERED_SCENARIOS_PM,
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

# Calculate the sum of wait times for each max_holding, origin, and replication_id combination
daily_total_wait_time_by_origin = (
    temp.groupby(["scenario", "origin", "replication_id"])
    .agg(waiting_time=("waiting_time", "sum"))
    .reset_index()
)

# Calculate the mean of wait times over replications for each max_holding and origin combination
daily_total_wait_time_by_origin = (
    daily_total_wait_time_by_origin.groupby(["scenario", "origin"])
    .agg(waiting_time=("waiting_time", "mean"))
    .reset_index()
)

daily_total_wait_time_by_origin_pivot = daily_total_wait_time_by_origin.pivot(
    index="origin", columns="scenario", values="waiting_time"
)
daily_total_wait_time_by_origin_pivot["Savings (minutes)"] = (
    daily_total_wait_time_by_origin_pivot["NO-CONTROL"]
    - daily_total_wait_time_by_origin_pivot["UIC-Halsted"]
)

print(daily_total_wait_time_by_origin_pivot)

# %%
fig = go.Figure(
    data=[
        go.Bar(
            x=daily_total_wait_time_by_origin_pivot.index,
            y=daily_total_wait_time_by_origin_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in daily_total_wait_time_by_origin_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Waiting Time by Origin Station (Northbound)",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Waiting Times (minutes)", font=dict(size=18)),
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
        "text": "Savings in Total Daily Waiting Time by Origin Station (Northbound)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Waiting Times(minutes)",
)

total_waiting_time_savings = (
    daily_total_wait_time_by_origin_pivot["NO-CONTROL"].sum()
    - daily_total_wait_time_by_origin_pivot["UIC-Halsted"].sum()
)

# Add annotations for total savings in waiting_time and journey_time
fig.add_annotation(
    x=1.0,
    y=1.1,
    xanchor="right",
    xref="paper",
    yref="paper",
    text=f"Total Waiting Time Savings: {total_waiting_time_savings:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)


fig.show(renderer="browser")

fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / "savings_in_total_daily_waiting_time_by_origin_station_Northbound_PM_UIC_NOCONTROL.svg"
    )
)

# %%
temp = passenger_df.query(
    "direction == 'Northbound' and (scenario == 'UIC-Halsted' or scenario == 'NO-CONTROL')"
)

temp["scenario"] = temp["scenario"].astype("str")

daily_total_journey_time_by_origin = (
    temp.groupby(["scenario", "origin", "replication_id"])
    .agg(
        journey_time=("journey_time", "sum"),
    )
    .reset_index()
)

daily_total_journey_time_by_origin = (
    daily_total_journey_time_by_origin.groupby(["scenario", "origin"])
    .agg(journey_time=("journey_time", "mean"))
    .reset_index()
)

daily_total_journey_time_by_origin_pivot = daily_total_journey_time_by_origin.pivot(
    index="origin", columns="scenario", values="journey_time"
)
daily_total_journey_time_by_origin_pivot["Savings (minutes)"] = (
    daily_total_journey_time_by_origin_pivot["NO-CONTROL"]
    - daily_total_journey_time_by_origin_pivot["UIC-Halsted"]
)


total_journey_time_savings = (
    daily_total_journey_time_by_origin_pivot["NO-CONTROL"].sum()
    - daily_total_journey_time_by_origin_pivot["UIC-Halsted"].sum()
)

fig = go.Figure(
    data=[
        go.Bar(
            x=daily_total_journey_time_by_origin_pivot.index,
            y=daily_total_journey_time_by_origin_pivot["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in daily_total_journey_time_by_origin_pivot["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Journey Time by Origin Station (Northbound)",
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
        "text": "Savings in Total Daily Journey Time by Origin Station (Northbound)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Journey Times (minutes)",
)


fig.add_annotation(
    x=1.0,
    y=1.1,
    xanchor="right",
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
        / "savings_in_total_daily_journey_time_by_origin_station_Northbound_PM_UIC_NOCONTROL.svg"
    )
)

# %%

passenger_df = pd.concat(
    [
        all_data["period=version_83,schd=AM,station=O-Hare"]["passenger_test"],
        all_data["period=version_83,schd=AM,station=NO-CONTROL"]["passenger_test"],
    ],
    keys=pd.CategoricalIndex(
        ["O-Hare", "NO-CONTROL"],
        categories=["NO-CONTROL", "O-Hare"],
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

southbound_data_am["scenario"] = southbound_data_am["scenario"].astype("str")

daily_total_wait_time_by_origin_am = (
    southbound_data_am.groupby(["scenario", "origin", "replication_id"])
    .agg(waiting_time=("waiting_time", "sum"))
    .reset_index()
)

daily_total_wait_time_by_origin_am = (
    daily_total_wait_time_by_origin_am.groupby(["scenario", "origin"])
    .agg(waiting_time=("waiting_time", "mean"))
    .reset_index()
)

daily_total_wait_time_by_origin_pivot_am = daily_total_wait_time_by_origin_am.pivot(
    index="origin", columns="scenario", values="waiting_time"
)
daily_total_wait_time_by_origin_pivot_am["Savings (minutes)"] = (
    daily_total_wait_time_by_origin_pivot_am["NO-CONTROL"]
    - daily_total_wait_time_by_origin_pivot_am["O-Hare"]
)

fig_am_wait = go.Figure(
    data=[
        go.Bar(
            x=daily_total_wait_time_by_origin_pivot_am.index,
            y=daily_total_wait_time_by_origin_pivot_am["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in daily_total_wait_time_by_origin_pivot_am["Savings (minutes)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Waiting Time by Origin Station (Southbound)",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Waiting Times (minutes)", font=dict(size=18)),
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
        "text": "Savings in Total Daily Waiting Time by Origin Station (Southbound)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Waiting Times(minutes)",
)

total_waiting_time_savings_am = (
    daily_total_wait_time_by_origin_pivot_am["NO-CONTROL"].sum()
    - daily_total_wait_time_by_origin_pivot_am["O-Hare"].sum()
)

fig_am_wait.add_annotation(
    x=1.0,
    y=1.1,
    xanchor="right",
    xref="paper",
    yref="paper",
    text=f"Total Waiting Time Savings: {total_waiting_time_savings_am:.0f} minutes",
    showarrow=False,
    font=dict(size=16),
)

fig_am_wait.show(renderer="browser")

fig_am_wait.write_image(
    str(
        OUTPUT_DIRECTORY
        / "savings_in_total_daily_waiting_time_by_origin_station_Southbound_AM_OHARE_NOCONTROL.svg"
    )
)

# Journey Time Savings
total_journey_time_by_origin_am = southbound_data_am.groupby(
    ["scenario", "replication_id", "origin"]
)["journey_time"].sum()

daily_total_journey_time_by_origin_am = (
    southbound_data_am.groupby(["scenario", "origin", "replication_id"])
    .agg(journey_time=("journey_time", "sum"))
    .reset_index()
)

daily_total_journey_time_by_origin_am = (
    daily_total_journey_time_by_origin_am.groupby(["scenario", "origin"])
    .agg(journey_time=("journey_time", "mean"))
    .reset_index()
)


daily_total_journey_time_by_origin_pivot_am = (
    daily_total_journey_time_by_origin_am.pivot(
        index="origin", columns="scenario", values="journey_time"
    )
)
daily_total_journey_time_by_origin_pivot_am["Savings (minutes)"] = (
    daily_total_journey_time_by_origin_pivot_am["NO-CONTROL"]
    - daily_total_journey_time_by_origin_pivot_am["O-Hare"]
)

total_journey_time_savings_am = (
    daily_total_journey_time_by_origin_pivot_am["NO-CONTROL"].sum()
    - daily_total_journey_time_by_origin_pivot_am["O-Hare"].sum()
)

fig_am_journey = go.Figure(
    data=[
        go.Bar(
            x=daily_total_journey_time_by_origin_pivot_am.index,
            y=daily_total_journey_time_by_origin_pivot_am["Savings (minutes)"],
            text=[
                f"{y:.0f}"
                for y in daily_total_journey_time_by_origin_pivot_am[
                    "Savings (minutes)"
                ]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Journey Time by Origin Station (Southbound)",
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
        "text": "Savings in Total Daily Journey Time by Origin Station (Southbound)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Journey Times (minutes)",
)

fig_am_journey.add_annotation(
    x=1.0,
    y=1.1,
    xanchor="right",
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
        / "savings_in_total_daily_journey_time_by_origin_station_Southbound_AM_OHARE_NOCONTROL.svg"
    )
)

# %%
# Group by scenario, origin, and replication_id, and count the passenger_ids
daily_total_passengers_boarded_by_origin_am = (
    southbound_data_am.groupby(["scenario", "origin", "replication_id"])
    .agg(passengers_boarded=("passenger_id", "count"))
    .reset_index()
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
        / "average_number_of_passengers_boarded_by_origin_station_Southbound_AM_OHARE_NOCONTROL.svg"
    )
)


# %%
# # %%
# temp = passenger_df.query(
#     "direction == 'Northbound' and (scenario == 'UIC-Halsted' or scenario == 'NO-CONTROL')"
# )

# temp["scenario"] = temp["scenario"].astype("str")

# avg_waiting_time = temp.groupby(["scenario", "origin"])["waiting_time"].mean() / 60

# avg_waiting_time_df = avg_waiting_time.reset_index()

# fig = go.Figure(
#     data=[
#         go.Bar(
#             x=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "NO-CONTROL"][
#                 "origin"
#             ],
#             y=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "NO-CONTROL"][
#                 "waiting_time"
#             ],
#             name="NO-CONTROL",
#             text=[
#                 f"{y:.2f}"
#                 for y in avg_waiting_time_df[
#                     avg_waiting_time_df["scenario"] == "NO-CONTROL"
#                 ]["waiting_time"]
#             ],
#             textposition="auto",
#             textfont=dict(size=8),
#         ),
#         go.Bar(
#             x=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "UIC-Halsted"][
#                 "origin"
#             ],
#             y=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "UIC-Halsted"][
#                 "waiting_time"
#             ],
#             name="UIC-Halsted",
#             text=[
#                 f"{y:.2f}"
#                 for y in avg_waiting_time_df[
#                     avg_waiting_time_df["scenario"] == "UIC-Halsted"
#                 ]["waiting_time"]
#             ],
#             textposition="auto",
#             textfont=dict(size=8),
#         ),
#     ],
#     layout=go.Layout(
#         title=dict(
#             text="Comparison of Average Waiting Times: No Control vs UIC-Halsted Holding (Northbound)",
#             font=dict(size=24),
#         ),
#         yaxis_title=dict(text="Average Waiting Time (minutes)", font=dict(size=18)),
#         yaxis=dict(
#             tickfont=dict(size=14),
#             gridwidth=1,
#             gridcolor="LightGray",
#         ),
#         xaxis=dict(tickfont=dict(size=14), tickangle=45),
#         barmode="group",
#         legend=dict(
#             font=dict(size=16),
#             yanchor="top",
#             xanchor="right",
#         ),
#     ),
# )

# fig.update_layout(
#     width=1600,
#     height=600,
# )

# fig.show(renderer="browser")

# # %%
# import plotly.graph_objects as go
# import numpy as np

# # Filter the data for Northbound direction and the desired scenarios
# northbound_data = passenger_df[
#     (passenger_df["direction"] == "Northbound")
#     & (passenger_df["scenario"].isin(["NO-CONTROL", "UIC-Halsted"]))
# ]

# # Calculate the total waiting time for each scenario and origin station
# total_waiting_time = northbound_data.groupby(["scenario", "origin"])[
#     "waiting_time"
# ].sum()

# # Reset the index to convert the grouped data into a DataFrame
# total_waiting_time_df = total_waiting_time.reset_index()

# # Pivot the data to have scenarios as columns and origin stations as rows
# total_waiting_time_pivot = total_waiting_time_df.pivot(
#     index="origin", columns="scenario", values="waiting_time"
# )

# # Calculate the percent decrease in total waiting time
# percent_decrease = (
#     (total_waiting_time_pivot["NO-CONTROL"] - total_waiting_time_pivot["UIC-Halsted"])
#     / total_waiting_time_pivot["NO-CONTROL"]
#     * 100
# )

# # Calculate the average total number of passengers for each origin station across the two scenarios
# total_passengers = (
#     northbound_data.groupby(["scenario", "replication_id", "origin"])
#     .size()
#     .reset_index(name="total_passengers")
# )
# avg_total_passengers = total_passengers.groupby("origin")["total_passengers"].mean()

# # Create the bar plot
# fig = go.Figure(
#     data=[
#         go.Bar(
#             x=percent_decrease.index,
#             y=percent_decrease,
#             text=[f"{y:.2f}%" for y in percent_decrease],
#             textposition="auto",
#             textfont=dict(size=12),
#             marker=dict(
#                 color=avg_total_passengers,
#                 colorscale="Viridis",
#                 showscale=True,
#                 colorbar=dict(title="Avg. Total Passengers"),
#             ),
#         )
#     ],
#     layout=go.Layout(
#         title=dict(
#             text="Percent Decrease in Total Waiting Time: UIC-Halsted vs No Control (Northbound)",
#             font=dict(size=24),
#         ),
#         yaxis_title=dict(text="Percent Decrease (%)", font=dict(size=18)),
#         yaxis=dict(
#             tickfont=dict(size=14),
#             gridwidth=1,
#             gridcolor="LightGray",
#         ),
#         xaxis=dict(tickfont=dict(size=14), tickangle=45),
#         legend=dict(
#             font=dict(size=16),
#             yanchor="top",
#             xanchor="right",
#         ),
#     ),
# )

# fig.update_layout(
#     width=1600,
#     height=600,
# )

# fig.show(renderer="browser")

# # %%
# import plotly.graph_objects as go

# # Filter the data for Northbound direction and the desired scenarios
# northbound_data = passenger_df[
#     (passenger_df["direction"] == "Northbound")
#     & (passenger_df["scenario"].isin(["NO-CONTROL", "UIC-Halsted"]))
# ]

# # Calculate the total waiting time for each scenario and origin station
# total_waiting_time = northbound_data.groupby(["scenario", "origin"])[
#     "waiting_time"
# ].sum()

# # Reset the index to convert the grouped data into a DataFrame
# total_waiting_time_df = total_waiting_time.reset_index()

# # Pivot the data to have scenarios as columns and origin stations as rows
# total_waiting_time_pivot = total_waiting_time_df.pivot(
#     index="origin", columns="scenario", values="waiting_time"
# )

# # Calculate the percent decrease in total waiting time
# percent_decrease = (
#     (total_waiting_time_pivot["NO-CONTROL"] - total_waiting_time_pivot["UIC-Halsted"])
#     / total_waiting_time_pivot["NO-CONTROL"]
#     * 100
# )

# # Create the bar plot
# fig = go.Figure(
#     data=[
#         go.Bar(
#             x=percent_decrease.index,
#             y=percent_decrease,
#             text=[f"{y:.2f}%" for y in percent_decrease],
#             textposition="auto",
#             textfont=dict(size=12),
#         )
#     ],
#     layout=go.Layout(
#         title=dict(
#             text="Percent Decrease in Total Waiting Time: UIC-Halsted vs No Control (Northbound)",
#             font=dict(size=24),
#         ),
#         yaxis_title=dict(text="Percent Decrease (%)", font=dict(size=18)),
#         yaxis=dict(
#             tickfont=dict(size=14),
#             gridwidth=1,
#             gridcolor="LightGray",
#         ),
#         xaxis=dict(tickfont=dict(size=14), tickangle=45),
#         legend=dict(
#             font=dict(size=16),
#             yanchor="top",
#             xanchor="right",
#         ),
#     ),
# )

# fig.update_layout(
#     width=1600,
#     height=600,
# )

# fig.show(renderer="browser")

# # %%
# temp = passenger_df.query(
#     "direction == 'Northbound' and (scenario == 'UIC-Halsted' or scenario == 'NO-CONTROL')"
# )

# temp["scenario"] = temp["scenario"].astype("str")

# avg_waiting_time = temp.groupby(["scenario", "origin"])["waiting_time"].mean() / 60

# avg_waiting_time_df = avg_waiting_time.reset_index()

# fig = go.Figure(
#     data=[
#         go.Bar(
#             x=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "NO-CONTROL"][
#                 "origin"
#             ],
#             y=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "NO-CONTROL"][
#                 "waiting_time"
#             ],
#             name="NO-CONTROL",
#             text=[
#                 f"{y:.2f}"
#                 for y in avg_waiting_time_df[
#                     avg_waiting_time_df["scenario"] == "NO-CONTROL"
#                 ]["waiting_time"]
#             ],
#             textposition="auto",
#             textfont=dict(size=8),
#         ),
#         go.Bar(
#             x=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "UIC-Halsted"][
#                 "origin"
#             ],
#             y=avg_waiting_time_df[avg_waiting_time_df["scenario"] == "UIC-Halsted"][
#                 "waiting_time"
#             ],
#             name="UIC-Halsted",
#             text=[
#                 f"{y:.2f}"
#                 for y in avg_waiting_time_df[
#                     avg_waiting_time_df["scenario"] == "UIC-Halsted"
#                 ]["waiting_time"]
#             ],
#             textposition="auto",
#             textfont=dict(size=8),
#         ),
#     ],
#     layout=go.Layout(
#         title=dict(
#             text="Comparison of Average Waiting Times: No Control vs UIC-Halsted Holding (Northbound)",
#             font=dict(size=24),
#         ),
#         yaxis_title=dict(text="Average Waiting Time (minutes)", font=dict(size=18)),
#         yaxis=dict(
#             tickfont=dict(size=14),
#             gridwidth=1,
#             gridcolor="LightGray",
#         ),
#         xaxis=dict(tickfont=dict(size=14), tickangle=45),
#         barmode="group",
#         legend=dict(
#             font=dict(size=16),
#             yanchor="top",
#             xanchor="right",
#         ),
#     ),
# )

# fig.update_layout(
#     width=1600,
#     height=600,
# )

# fig.show(renderer="browser")


# # %%
# import plotly.express as px

# # Filter the data for Northbound direction and the desired scenarios
# northbound_data = passenger_df[
#     (passenger_df["direction"] == "Northbound")
#     & (passenger_df["scenario"].isin(["NO-CONTROL", "UIC-Halsted"]))
# ]

# # Calculate the average waiting time in minutes for each scenario and origin station
# avg_waiting_time = (
#     northbound_data.groupby(["scenario", "origin"])["waiting_time"].mean() / 60
# )

# # Reset the index to convert the grouped data into a DataFrame
# avg_waiting_time_df = avg_waiting_time.reset_index()

# # Create the bar plot
# fig = px.bar(
#     avg_waiting_time_df,
#     x="origin",
#     y="waiting_time",
#     color="scenario",
#     barmode="group",
#     category_orders={
#         "scenario": ["NO-CONTROL", "UIC-Halsted"]
#     },  # set the order of scenarios
#     labels={
#         "waiting_time": "Average Waiting Time (minutes)",
#         "origin": "Origin Station",
#         "scenario": "Scenario",
#     },
#     title="Comparison of Average Waiting Times: No Control vs UIC-Halsted Holding (Northbound)",
# )

# # Update layout for better visual appearance
# fig.update_layout(
#     width=1600,
#     height=600,
#     plot_bgcolor="white",
#     title={
#         "text": "Comparison of Average Waiting Times: No Control vs UIC-Halsted Holding (Northbound)",
#         "x": 0.5,
#         "font": {"size": 24},
#     },
#     xaxis_title="Origin Station",
#     yaxis_title="Average Waiting Time (minutes)",
#     legend_title="Scenario",
# )

# # Customize x-axis labels
# fig.update_xaxes(tickangle=45)

# # Add value labels to the bars
# fig.update_traces(
#     texttemplate="%{y:.2f}",
#     textposition="auto",
#     textfont={"size": 12},
# )

# # Save the plot as an SVG file
# fig.write_image("average_waiting_times_comparison.svg")

# # Show the plot in the browser
# fig.show(renderer="browser")

# # Save the interactive HTML file to disk
# fig.write_html("average_waiting_times_comparison.html")

# # %%
# import plotly.express as px

# # Custom color palette
# color_discrete_map = {
#     "Northbound": "#636EFA",  # Example color for Northbound
#     "Southbound": "#EF553B",  # Example color for Southbound
# }

# passenger_df["waiting_time_minutes"] = passenger_df["waiting_time"] / 60

# # Create the box plot with custom colors and notches
# fig = px.box(
#     passenger_df,
#     x="origin",
#     y="waiting_time_minutes",
#     color="direction",
#     # color_discrete_map=color_discrete_map,
#     facet_col="scenario",
#     notched=True,  # show notches
#     category_orders={"scenario": ["Pulaski", "Racine", "UIC-Halsted", "Clark-Lake"]},
#     labels={
#         "waiting_time": "Waiting Time (minutes)",
#         "origin": "Origin Station",
#         "scenario": "Scenario",
#         "direction": "Direction",
#     },
#     title="Passenger Waiting Times by Station and Scenario",
# )

# # Update traces with inclusive quartile method
# fig.update_traces(quartilemethod="inclusive")

# # Customize hover data
# fig.update_traces(
#     hoverinfo="y+name",
#     hovertemplate="Waiting Time: %{y} minutes<br>Scenario: %{facet_col}<extra></extra>",
# )

# # Update layout for responsive design
# fig.update_layout(
#     autosize=True, margin=dict(l=40, r=40, t=80, b=40), hovermode="closest"
# )

# # Update legend position and layout
# fig.update_layout(
#     legend=dict(
#         title="Direction",
#         orientation="h",
#         yanchor="bottom",
#         y=1.02,
#         xanchor="right",
#         x=1,
#     )
# )
# # Show the figure in the browser
# fig.show(renderer="browser")

# # Save the interactive HTML file to disk
# output_file_path = os.path.join(OUTPUT_DIRECTORY, "waiting_times.html")
# pio.write_html(fig, output_file_path)

# # %%
# import plotly.express as px

# # Create the box plot with custom colors and facet rows for direction
# fig = px.box(
#     passenger_df,
#     x="origin",
#     y="waiting_time_minutes",
#     color="scenario",  # Use station as color
#     facet_row="direction",  # Use direction as facet row
#     category_orders={
#         "origin": STATION_ORDER,  # Ensure the order of stations is consistent
#         "direction": ["Northbound", "Southbound"],  # Consistent order for direction
#         "scenario": ["Pulaski", "Racine", "UIC-Halsted", "Clark-Lake"],
#     },
#     labels={
#         "waiting_time_minutes": "Waiting Time (minutes)",
#         "origin": "Station",
#         "direction": "Direction",
#     },
#     title="Waiting Times by Station and Direction",
# )

# # Update layout for responsive design
# fig.update_layout(
#     autosize=True, margin=dict(l=40, r=40, t=80, b=40), hovermode="closest"
# )

# # Update layout for legend
# fig.update_layout(
#     legend=dict(
#         title="Holding Station@",
#         orientation="h",
#         yanchor="top",
#         y=1,
#         xanchor="right",
#         x=1,
#     )
# )

# # Update y-axis titles for facet rows
# fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

# # Show the figure in the browser
# fig.show(renderer="browser")

# # Save the interactive HTML file to disk
# output_file_path = os.path.join(OUTPUT_DIRECTORY, "waiting_times_by_direction.html")
# pio.write_html(fig, output_file_path)

# # %%
# pivot_table = passenger_df.pivot_table(
#     index="origin",
#     columns="destination",
#     values="index",
#     aggfunc="count",
#     fill_value=0,
# )

# import plotly.graph_objects as go

# fig = go.Figure(
#     data=[go.Heatmap(z=pivot_table.values, x=pivot_table.columns, y=pivot_table.index)]
# )

# fig.update_layout(
#     title="Passenger Flow",
#     autosize=False,
#     width=500,
#     height=500,
#     margin=dict(l=65, r=50, b=65, t=90),
# )

# fig.show()

# # %%
# import numpy as np

# # Get unique values in the "scenario" column
# unique_scenarios = passenger_df["scenario"].unique()

# # Create a dictionary to store the pivot tables
# pivot_tables = {}

# # Iterate over each unique scenario
# for scenario in unique_scenarios:
#     # Filter the dataframe for the current scenario
#     scenario_df = passenger_df[passenger_df["scenario"] == scenario]

#     # Create pivot table with 90th percentile of waiting_time
#     pivot_table_90th_waiting_time = scenario_df.pivot_table(
#         index="origin",
#         columns="destination",
#         values="waiting_time",
#         aggfunc=lambda x: np.percentile(x, 90),
#         fill_value=0,
#     )

#     # Create pivot table with 50th percentile of waiting_time
#     pivot_table_50th_waiting_time = scenario_df.pivot_table(
#         index="origin",
#         columns="destination",
#         values="waiting_time",
#         aggfunc=lambda x: np.percentile(x, 50),
#         fill_value=0,
#     )

#     # Create pivot table with 90th percentile of travel_time
#     pivot_table_90th_travel_time = scenario_df.pivot_table(
#         index="origin",
#         columns="destination",
#         values="travel_time",
#         aggfunc=lambda x: np.percentile(x, 90),
#         fill_value=0,
#     )

#     # Create pivot table with 50th percentile of travel_time
#     pivot_table_50th_travel_time = scenario_df.pivot_table(
#         index="origin",
#         columns="destination",
#         values="travel_time",
#         aggfunc=lambda x: np.percentile(x, 50),
#         fill_value=0,
#     )

#     pivot_table_10th_journey_time = scenario_df.pivot_table(
#         index="origin",
#         columns="destination",
#         values="journey_time",
#         aggfunc=lambda x: np.percentile(x, 10),
#         fill_value=0,
#     )

#     pivot_table_50th_journey_time = scenario_df.pivot_table(
#         index="origin",
#         columns="destination",
#         values="journey_time",
#         aggfunc=lambda x: np.percentile(x, 50),
#         fill_value=0,
#     )

#     pivot_table_90th_journey_time = scenario_df.pivot_table(
#         index="origin",
#         columns="destination",
#         values="journey_time",
#         aggfunc=lambda x: np.percentile(x, 90),
#         fill_value=0,
#     )

#     # Store the pivot tables in the dictionary
#     pivot_tables[scenario] = {
#         "pivot_table_90th_waiting_time": pivot_table_90th_waiting_time,
#         "pivot_table_50th_waiting_time": pivot_table_50th_waiting_time,
#         "pivot_table_90th_travel_time": pivot_table_90th_travel_time,
#         "pivot_table_50th_travel_time": pivot_table_50th_travel_time,
#         "pivot_table_10th_journey_time": pivot_table_10th_journey_time,
#         "pivot_table_50th_journey_time": pivot_table_50th_journey_time,
#         "pivot_table_90th_journey_time": pivot_table_90th_journey_time,
#     }
# from typing import List

# import matplotlib.pyplot as plt
# import pandas as pd
# import seaborn as sns


# def plot_difference_heatmap(pivot_tables, scenario):
#     # Calculate the difference between the pivot tables for the given scenario
#     difference = (
#         pivot_tables[scenario]["pivot_table_50th_journey_time"]
#         - pivot_tables["UIC-Halsted"]["pivot_table_50th_journey_time"]
#     )

#     # Plot the heatmap
#     plt.figure(figsize=(10, 8))
#     sns.heatmap(
#         difference, annot=False, fmt=".1f", cmap="coolwarm", vmin=-150, vmax=150
#     )
#     plt.title(
#         f"Difference in 50th Percentile Journey Time between {scenario} and UIC-Halsted"
#     )

#     plt.show()


# # %%
# STATION_ORDER_RENAME = list(
#     map(
#         lambda station: "Clark-Lake" if station == "Clark/Lake" else station,
#         STATION_ORDER,
#     )
# )

# scenario_impacts = {}
# for scenario in ORDERED_SCENARIOS:
#     if scenario == "None":
#         continue

#     positively_impacted = []
#     negatively_impacted = []

#     index = STATION_ORDER_RENAME.index(scenario)

#     for i, origin in enumerate(STATION_ORDER):
#         for j, destination in enumerate(STATION_ORDER):
#             if i >= index:
#                 if j > i:
#                     positively_impacted.append((origin, destination))

#     for i, origin in enumerate(STATION_ORDER):
#         for j, destination in enumerate(STATION_ORDER):
#             if i < index:
#                 if j > index:
#                     negatively_impacted.append((origin, destination))

#     scenario_impacts[scenario] = {
#         "positive": positively_impacted,
#         "negative": negatively_impacted,
#     }

# # %%


# def impact_viz(scenario):
#     station_table = pd.DataFrame(index=STATION_ORDER, columns=STATION_ORDER).fillna(0)

#     # Specify index as origin and columns as destination
#     station_table = station_table.rename_axis("origin").rename_axis(
#         "destination", axis="columns"
#     )

#     for impacted_pair in scenario_impacts[scenario]["positive"]:
#         station_table.loc[impacted_pair[0], impacted_pair[1]] = 1

#     for impacted_pair in scenario_impacts[scenario]["negative"]:
#         station_table.loc[impacted_pair[0], impacted_pair[1]] = 2

#     from matplotlib.colors import ListedColormap

#     cmap = ListedColormap(["gray", "green", "red"])

#     # Plotting
#     plt.figure(figsize=(8, 8))
#     sns.heatmap(station_table, cmap=cmap, cbar=False, annot=True)

#     plt.title(f"Impacted OD Pairs for holding @{scenario}")

#     plt.show()


# for scenario in ORDERED_SCENARIOS:
#     if scenario == "None":
#         continue
#     impact_viz(scenario)

# # %%

# # %%
# weights = (
#     (
#         passenger_df.groupby(["origin", "destination"]).size()
#         / passenger_df.groupby(["origin", "destination"]).size().sum()
#     )
#     .reset_index()
#     .pivot(index="origin", columns="destination", values=0)
# )

# import plotly.graph_objects as go

# # Calculate the proportions for each origin and destination and convert to percentages
# origin_proportions = weights.sum(axis=1) * 100
# destination_proportions = weights.sum(axis=0) * 100

# # Create a grouped bar chart using plotly with both origin and destination proportions as percentages
# fig = go.Figure()

# # Add trace for destination proportions
# fig.add_trace(
#     go.Bar(
#         x=weights.columns,
#         y=destination_proportions,
#         name="Destination",
#     )
# )

# # Add trace for origin proportions
# fig.add_trace(go.Bar(x=weights.index, y=origin_proportions, name="Origin"))

# # Update layout for the grouped bar chart
# fig.update_layout(
#     barmode="group",
#     title="Station Proportions in Passenger Data",
#     xaxis_title="Station",
#     yaxis_title="Proportion (%)",
#     legend_title="Proportions",
# )

# # Render the plot in the browser
# fig.show(renderer="browser")
# fig.write_html(
#     "/Users/moji/Presentations/One-on-One Meetings/03-04-2024/station_proportions.html"
# )

# # %%
# weights = (
#     (
#         passenger_df[passenger_df["direction"] == "Northbound"]
#         .groupby(["origin", "destination"])
#         .size()
#         / passenger_df[passenger_df["direction"] == "Northbound"]
#         .groupby(["origin", "destination"])
#         .size()
#         .sum()
#     )
#     .reset_index()
#     .pivot(index="origin", columns="destination", values=0)
# )

# import plotly.graph_objects as go

# # Calculate the proportions for each origin and destination and convert to percentages
# origin_proportions = weights.sum(axis=1) * 100
# destination_proportions = weights.sum(axis=0) * 100

# # Create a grouped bar chart using plotly with both origin and destination proportions as percentages
# fig = go.Figure()

# # Add trace for destination proportions
# fig.add_trace(
#     go.Bar(
#         x=weights.columns,
#         y=destination_proportions,
#         name="Destination",
#     )
# )

# # Add trace for origin proportions
# fig.add_trace(go.Bar(x=weights.index, y=origin_proportions, name="Origin"))

# # Update layout for the grouped bar chart
# fig.update_layout(
#     barmode="group",
#     title="Station Proportions in Passenger Data (Northbound)",
#     xaxis_title="Station",
#     yaxis_title="Proportion (%)",
#     legend_title="Proportions",
# )

# # Render the plot in the browser
# fig.show(renderer="browser")
# fig.write_html(
#     "/Users/moji/Presentations/One-on-One Meetings/03-04-2024/station_proportions_Northbound.html"
# )

# # %%
# weights = (
#     (
#         passenger_df[passenger_df["direction"] == "Northbound"]
#         .groupby(["origin", "destination"])
#         .size()
#         / passenger_df[passenger_df["direction"] == "Northbound"]
#         .groupby(["origin", "destination"])
#         .size()
#         .sum()
#     )
#     .reset_index()
#     .pivot(index="origin", columns="destination", values=0)
# )


# def impact_analyzer(scenario, metric, pivot_tables=pivot_tables, weights=weights):
#     diff_table = pivot_tables[scenario][metric] - pivot_tables["None"][metric]

#     output_entry = {
#         "scenario": scenario,
#         "metric": metric,
#     }
#     # Calculate the weighted average difference in journey time for negatively impacted OD-pairs
#     sum_weights = 0
#     sum_weighted_diff = 0

#     for origin, destination in scenario_impacts[scenario]["negative"]:
#         time_diff = diff_table.loc[origin, destination]
#         weight = weights.loc[origin, destination]

#         sum_weighted_diff += time_diff * weight
#         sum_weights += weight

#     output_entry["average_negative_impact"] = sum_weighted_diff / sum_weights

#     output_entry["percentage_negative_impact"] = sum_weights

#     # Calculate the weighted average difference in journey time for positively impacted OD-pairs
#     sum_weights = 0
#     sum_weighted_diff = 0

#     for origin, destination in scenario_impacts[scenario]["positive"]:
#         time_diff = diff_table.loc[origin, destination]
#         weight = weights.loc[origin, destination]

#         sum_weighted_diff += time_diff * weight
#         sum_weights += weight

#     output_entry["average_positive_impact"] = sum_weighted_diff / sum_weights

#     output_entry["percentage_positive_impact"] = sum_weights

#     return output_entry


# impact_data_list_of_json = []
# for scenario in ORDERED_SCENARIOS:
#     if scenario == "None":
#         continue
#     for metric in [
#         "pivot_table_10th_journey_time",
#         "pivot_table_50th_journey_time",
#         "pivot_table_90th_journey_time",
#     ]:
#         impact_data_list_of_json.append(impact_analyzer(scenario, metric))


# df = pd.DataFrame(impact_data_list_of_json)
# df.head()

# # %%
# df.columns = [
#     "Scenario",
#     "Metric",
#     "Average Negative Impact (Sec)",
#     "Percentage of Negatively Impacted",
#     "Average Positive Impact (Sec) ",
#     "Percentage of Positively Impacted",
# ]

# metrics_rename = {
#     "pivot_table_10th_journey_time": "10th Percentile Journey Time",
#     "pivot_table_50th_journey_time": "50th Percentile Journey Time",
#     "pivot_table_90th_journey_time": "90th Percentile Journey Time",
# }

# df["Metric"] = df["Metric"].map(metrics_rename)

# # %%

# df.to_clipboard(index=False)

# # %%
# temp
# # %%
# import plotly.graph_objects as go

# fig = go.Figure()

# holding_counts = []
# non_holding_counts = []

# for i, scenario in enumerate(ORDERED_SCENARIOS):
#     if scenario == "None":
#         continue

#     if scenario == "Clark-Lake":
#         station = "Clark/Lake"
#     else:
#         station = scenario

#     df = temp[temp["scenario"] == scenario].query("station_name == @station")
#     df["is_holding"] = df["dwell_time"] > 60

#     holding_counts.append(df["is_holding"].value_counts()[True])
#     non_holding_counts.append(df["is_holding"].value_counts()[False])

# fig.add_trace(go.Bar(x=ORDERED_SCENARIOS[1:], y=holding_counts, name="Holding"))
# fig.add_trace(go.Bar(x=ORDERED_SCENARIOS[1:], y=non_holding_counts, name="Non-Holding"))

# fig.update_layout(
#     title="Number of Holdings vs Non-Holdings by Scenario",
#     xaxis=dict(title="Scenario"),
#     yaxis=dict(title="Count"),
#     barmode="group",
#     bargap=0.15,
#     bargroupgap=0.1,
# )

# import plotly.graph_objects as go

# fig = go.Figure()

# holding_counts = []
# non_holding_counts = []

# for i, scenario in enumerate(ORDERED_SCENARIOS):
#     if scenario == "None":
#         continue

#     if scenario == "Clark-Lake":
#         station = "Clark/Lake"
#     else:
#         station = scenario

#     df = temp[temp["scenario"] == scenario].query("station_name == @station")
#     df["is_holding"] = df["dwell_time"] > 60

#     holding_counts.append(df["is_holding"].value_counts()[True])
#     non_holding_counts.append(df["is_holding"].value_counts()[False])

# fig.add_trace(go.Bar(x=ORDERED_SCENARIOS[1:], y=holding_counts, name="Holding"))
# fig.add_trace(go.Bar(x=ORDERED_SCENARIOS[1:], y=non_holding_counts, name="Non-Holding"))

# fig.update_layout(
#     title="Number of Holdings vs Non-Holdings by Scenario",
#     xaxis=dict(title="Scenario"),
#     yaxis=dict(title="Count"),
#     barmode="group",
#     bargap=0.15,
#     bargroupgap=0.1,
# )

# fig.write_html(
#     "/Users/moji/Presentations/One-on-One Meetings/03-13-2023/holdings_vs_non_holdings.html"
# )


# fig.show()

# # %%
# # %%
# holding_ratios = []

# for i, scenario in enumerate(ORDERED_SCENARIOS[1:]):
#     if scenario == "Clark-Lake":
#         station = "Clark/Lake"
#     else:
#         station = scenario

#     df = temp[temp["scenario"] == scenario].query("station_name == @station")
#     df["is_holding"] = df["dwell_time"] > 60

#     holding_count = df["is_holding"].value_counts()[True]
#     total_count = len(df)

#     holding_ratio = holding_count / total_count
#     holding_ratios.append(holding_ratio)

# holding_ratio_df = pd.DataFrame(
#     {"Scenario": ORDERED_SCENARIOS[1:], "Holding Ratio": holding_ratios}
# )

# holding_ratio_df.T.to_clipboard(index=False)

# # %%
