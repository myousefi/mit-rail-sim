# %%
import glob
import os
from pathlib import Path
import pandas as pd

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


directory = "/Users/moji/Projects/mit_rail_sim/cta-2024/sensitivity_analysis_PM/"

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

no_control_dir = "/Users/moji/Projects/mit_rail_sim/cta-2024/holding-spring/period=version_83,schd=PM,station=NO-CONTROL/"

all_data["max_holding=0,period=version_83,schd=PM,station=UIC-Halsted"] = (
    read_csv_files_in_subdir(no_control_dir)
)


print(all_data.keys())

# %%
# Next step of analysis
OUTPUT_DIRECTORY = Path(
    "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"
)

ORDERED_SCENARIOS = [
    "0",
    "60",
    "120",
    "180",
    "240",
]

data_list = []
for key in all_data.keys():
    max_holding, period, schd, station = key.split(",")
    _, max_holding_value = max_holding.split("=")
    _, period_value = period.split("=")
    _, schd_value = schd.split("=")
    _, station_value = station.split("=")
    data_list.append(
        (
            max_holding_value,
            period_value,
            schd_value,
            station_value,
            all_data[key]["station_test"],
        )
    )

df_combined = pd.concat(
    [data[4] for data in data_list],
    keys=pd.MultiIndex.from_tuples(
        [(data[0], data[1], data[2], data[3]) for data in data_list],
        names=["max_holding", "period", "schd", "station"],
    ),
).reset_index(names=["max_holding", "period", "schd", "station", "index"])

df_combined["max_holding"] = pd.Categorical(
    df_combined["max_holding"], categories=ORDERED_SCENARIOS, ordered=True
)
df_combined = df_combined.sort_values(
    ["max_holding", "period", "schd", "station"]
).reset_index(drop=True)

df_combined["period"] = df_combined["period"].replace(
    {
        "version_81": "Winter 2023",
        "version_83": "Spring 2024",
    }
)
# %%
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Assuming df_combined is already created as per your previous steps

OUTPUT_DIRECTORY = Path(
    "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"
)

ORDERED_SCENARIOS = [
    "0",
    "60",
    "120",
    "180",
    "240",
]

for direction in ["Northbound"]:
    for period in ["Spring 2024"]:
        period_data = df_combined[
            (df_combined["period"] == period) & (df_combined["direction"] == direction)
        ]

        total_passengers = period_data.groupby(["max_holding", "station_name"])[
            "number_of_passengers_boarded"
        ].sum()
        denied_boardings = period_data.groupby(["max_holding", "station_name"])[
            "denied_boarding"
        ].sum()
        percentage_denied_boardings = (denied_boardings / total_passengers) * 100

        percentage_denied_boardings = percentage_denied_boardings.reset_index().rename(
            columns={0: "denied_boarding"}
        )

        non_zero_stations = percentage_denied_boardings[
            percentage_denied_boardings["denied_boarding"] > 0
        ]["station_name"].unique()
        period_data = percentage_denied_boardings[
            percentage_denied_boardings["station_name"].isin(non_zero_stations)
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=period_data["station_name"],
                    y=period_data[period_data["max_holding"] == holding][
                        "denied_boarding"
                    ],
                    name=f"{holding}s",
                    text=[
                        f"{x:.1f}%"
                        for x in period_data[period_data["max_holding"] == holding][
                            "denied_boarding"
                        ]
                    ],
                    textposition="auto",
                    # textfont=dict(size=8),
                )
                for holding in ORDERED_SCENARIOS
            ],
            layout=go.Layout(
                title=dict(
                    text=f"Denied Boardings by Station - {direction} | {period}",
                    font=dict(size=24),
                ),
                yaxis_title=dict(
                    text="Percentage of Denied Boardings", font=dict(size=18)
                ),
                yaxis=dict(
                    tickfont=dict(size=14),
                    ticksuffix="%",
                    gridwidth=1,
                    gridcolor="LightGray",
                    dtick=1,
                ),
                xaxis=dict(tickfont=dict(size=14), tickangle=45),
                barmode="group",
                legend=dict(
                    title="Max Holding Time (s)",
                    # font=dict(size=16),
                    yanchor="top",
                    xanchor="right",
                ),
            ),
        )

        fig.show(renderer="browser")
        fig.write_image(
            str(
                OUTPUT_DIRECTORY
                / f"sensitivity_denied_boardings_{direction}_{period}.svg"
            ),
            width=1600,
            height=600,
        )

        fig.write_html(
            str(
                OUTPUT_DIRECTORY
                / f"sensitivity_denied_boardings_{direction}_{period}.html"
            )
        )


# %%
passenger_df = pd.concat(
    [
        all_data["max_holding=0,period=version_83,schd=PM,station=UIC-Halsted"][
            "passenger_test"
        ],
        all_data["max_holding=60,period=version_83,schd=PM,station=UIC-Halsted"][
            "passenger_test"
        ],
        all_data["max_holding=120,period=version_83,schd=PM,station=UIC-Halsted"][
            "passenger_test"
        ],
        all_data["max_holding=180,period=version_83,schd=PM,station=UIC-Halsted"][
            "passenger_test"
        ],
        all_data["max_holding=240,period=version_83,schd=PM,station=UIC-Halsted"][
            "passenger_test"
        ],
    ],
    keys=pd.CategoricalIndex(
        ["0", "60", "120", "180", "240"],
        categories=ORDERED_SCENARIOS,
        ordered=True,
    ),
).reset_index(names=["max_holding", "index"])

passenger_df["waiting_time"] = passenger_df["waiting_time"] / 60
passenger_df["travel_time"] = passenger_df["travel_time"] / 60
passenger_df["journey_time"] = passenger_df["journey_time"] / 60

passenger_df.head()

# %%
temp = passenger_df.query("direction == 'Northbound'")

temp["max_holding"] = temp["max_holding"].astype("str")

# Calculate the sum of wait times for each max_holding, origin, and replication_id combination
daily_total_wait_time_by_origin = (
    temp.groupby(["max_holding", "origin", "replication_id"])
    .agg(waiting_time=("waiting_time", "sum"))
    .reset_index()
    .query("waiting_time > 0")
)

# %%
# Calculate the mean of wait times over replications for each max_holding and origin combination
daily_total_wait_time_by_origin = (
    daily_total_wait_time_by_origin.groupby(["max_holding", "origin"])
    .agg(waiting_time=("waiting_time", "mean"))
    .reset_index()
)


# %%
daily_total_wait_time_by_origin_pivot = daily_total_wait_time_by_origin.pivot(
    index="origin", columns="max_holding", values="waiting_time"
)

# Calculate savings for each scenario compared to the no-control scenario
for scenario in ORDERED_SCENARIOS[1:]:
    daily_total_wait_time_by_origin_pivot[f"Savings ({scenario}s)"] = (
        daily_total_wait_time_by_origin_pivot["0"]
        - daily_total_wait_time_by_origin_pivot[scenario]
    )

print(daily_total_wait_time_by_origin_pivot)

# Create the plot
fig = go.Figure(
    data=[
        go.Bar(
            x=daily_total_wait_time_by_origin_pivot.index,
            y=daily_total_wait_time_by_origin_pivot[f"Savings ({scenario}s)"],
            name=f"Max Holding: {scenario}s",
            text=[
                f"{y:.0f}"
                for y in daily_total_wait_time_by_origin_pivot[f"Savings ({scenario}s)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
        for scenario in ORDERED_SCENARIOS[1:]
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
        barmode="group",
        legend=dict(
            title="Max Holding Time",
            font=dict(size=16),
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.99,
        ),
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
    yaxis_title="Savings in Waiting Times (minutes)",
)

# Add annotations for total savings in waiting_time for each scenario
for i, scenario in enumerate(ORDERED_SCENARIOS[1:]):
    total_waiting_time_savings = (
        daily_total_wait_time_by_origin_pivot["0"].sum()
        - daily_total_wait_time_by_origin_pivot[scenario].sum()
    )
    fig.add_annotation(
        x=0.01,
        y=1.1 - i * 0.05,
        xanchor="left",
        xref="paper",
        yref="paper",
        text=f"Total Waiting Time Savings ({scenario}s): {total_waiting_time_savings:.0f} minutes",
        showarrow=False,
        font=dict(size=16),
    )

fig.show(renderer="browser")

fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_waiting_time_by_origin_station_Northbound_PM_sensitivity.svg"
    )
)

# %%
temp = passenger_df.query("direction == 'Northbound'")

temp["max_holding"] = temp["max_holding"].astype("str")
daily_total_journey_time_by_origin = (
    temp.groupby(["max_holding", "origin", "replication_id"])
    .agg(journey_time=("journey_time", "sum"))
    .reset_index()
    .query("journey_time > 0")
)

daily_total_journey_time_by_origin = (
    daily_total_journey_time_by_origin.groupby(["max_holding", "origin"])
    .agg(journey_time=("journey_time", "mean"))
    .reset_index()
)


# %%
daily_total_journey_time_by_origin_pivot = daily_total_journey_time_by_origin.pivot(
    index="origin", columns="max_holding", values="journey_time"
)

# Calculate savings for each scenario compared to the no-control scenario
for scenario in ORDERED_SCENARIOS[1:]:
    daily_total_journey_time_by_origin_pivot[f"Savings ({scenario}s)"] = (
        daily_total_journey_time_by_origin_pivot["0"]
        - daily_total_journey_time_by_origin_pivot[scenario]
    )


# %%
# Create the plot
fig = go.Figure(
    data=[
        go.Bar(
            x=daily_total_journey_time_by_origin_pivot.index,
            y=daily_total_journey_time_by_origin_pivot[f"Savings ({scenario}s)"],
            name=f"Max Holding: {scenario}s",
            text=[
                f"{y:.0f}"
                for y in daily_total_journey_time_by_origin_pivot[
                    f"Savings ({scenario}s)"
                ]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
        for scenario in ORDERED_SCENARIOS[1:]
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Journey Time by Origin Station (Northbound)",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Journey Times (minutes)", font=dict(size=18)),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
        barmode="group",
        legend=dict(
            title="Max Holding Time",
            font=dict(size=16),
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
        ),
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

# Add annotations for total savings in journey_time for each scenario
for i, scenario in enumerate(ORDERED_SCENARIOS[1:]):
    total_journey_time_savings = (
        daily_total_journey_time_by_origin_pivot["0"].sum()
        - daily_total_journey_time_by_origin_pivot[scenario].sum()
    )
    fig.add_annotation(
        x=0.01,
        y=1.1 - i * 0.05,
        xanchor="left",
        xref="paper",
        yref="paper",
        text=f"Total Journey Time Savings ({scenario}s): {total_journey_time_savings:.0f} minutes",
        showarrow=False,
        font=dict(size=16),
    )

fig.show(renderer="browser")

fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / f"savings_in_total_daily_journey_time_by_origin_station_Northbound_PM_sensitivity.svg"
    )
)

# %%
import plotly.express as px

# Filter the data for max_holding=180 and max_holding=0 at Clark/Lake station
df_180 = df_combined[
    (df_combined["max_holding"] == "180")
    & (df_combined["station_name"] == "Clark/Lake")
]
df_0 = df_combined[
    (df_combined["max_holding"] == "0") & (df_combined["station_name"] == "Clark/Lake")
]

# Combine the filtered data into a single DataFrame
df_plot = pd.concat(
    [
        df_180["number_of_passengers_on_platform_before_stop"].reset_index(drop=True),
        df_0["number_of_passengers_on_platform_before_stop"].reset_index(drop=True),
    ],
    axis=1,
    keys=["Holding at UIC-Halsted (<180s)", "NO-CONTROL"],
)

# Create the histogram plot with box plot on the margin
fig = px.histogram(
    df_plot,
    marginal="box",
    barmode="group",
    title="Distribution of Platform Crowding at Clark/Lake",
    labels={"value": "Number of Passengers on Platform"},
)

# Customize the layout
fig.update_layout(
    xaxis_title="Number of Passengers on Platform",
    yaxis_title="Frequency",
    legend_title="Scenario",
)

# Show the plot
fig.show(renderer="browser")

# Save the plot as an image file
fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / "platform_crowding_distribution_Clark_Lake_holding_vs_no_control.svg"
    ),
    width=800,
    height=600,
)


# %%
