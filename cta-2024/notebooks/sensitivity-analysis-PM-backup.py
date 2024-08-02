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


directory = "/Users/moji/Projects/mit_rail_sim/cta-2024/sensitivity_analysis_PM_backup"

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


all_data["max_holding=0,period=version_83,schd=PM,station=UIC-Halsted"] = read_csv_files_in_subdir("/Users/moji/Projects/mit_rail_sim/cta-2024/mid_route_holding_even_more_replications/period=version_83,schd=PM,station=NO-CONTROL")


print(all_data.keys())
# %%
# Next step of analysis
OUTPUT_DIRECTORY = Path(
    "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/tests/"
)

ORDERED_SCENARIOS = ["0", "60", "120", "180"]

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
                    tickfont=dict(size=18),
                    ticksuffix="%",
                    gridwidth=1,
                    gridcolor="LightGray",
                    dtick=1,
                ),
                xaxis=dict(tickfont=dict(size=18), tickangle=45),
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
import plotly.graph_objects as go

# Define the service standard and crush load values
service_standard = 640
crush_load = 960

temp = df_combined.query(
    "direction == 'Northbound' and period == 'Spring 2024' and schd == 'PM' and (max_holding == '0' or max_holding == '180')"
)

fig = go.Figure(
    data=[
        go.Box(
            x=temp[temp["max_holding"] == scenario]["station_name"],
            y=temp[temp["max_holding"] == scenario]["number_of_passengers_on_train_after_stop"],
            name=name,
            boxpoints="all",
            jitter=0.3,
            pointpos=-1.8,
            marker=dict(size=6),
        )
        for scenario, name in [("0", "NO-CONTROL"), ("180", "Max Holding: 180s")]
    ],
    layout=go.Layout(
        title=dict(
            text="Train Loads for NO-CONTROL and Max Holding 180s",
            font=dict(size=24),
        ),
        yaxis_title=dict(
            text="Number of Passengers on Train After Stop", font=dict(size=18)
        ),
        yaxis=dict(
            tickfont=dict(size=14),
            gridwidth=1,
            gridcolor="LightGray",
        ),
        xaxis=dict(tickfont=dict(size=14), tickangle=45),
        boxmode="group",
        legend=dict(
            title="Scenario",
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
        "text": "Train Loads for NO-CONTROL and Max Holding 180s",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Station Name",
    yaxis_title="Number of Passengers on Train After Stop",
    shapes=[
        dict(
            type="line",
            yref="y",
            y0=service_standard,
            y1=service_standard,
            xref="paper",
            x0=0,
            x1=1,
            line=dict(
                color="green",
                width=4,
                dash="dash",
            ),
        ),
        dict(
            type="line",
            yref="y",
            y0=crush_load,
            y1=crush_load,
            xref="paper",
            x0=0,
            x1=1,
            line=dict(
                color="red",
                width=4,
                dash="dash",
            ),
        ),
    ],
    annotations=[
        dict(
            xref="paper",
            yref="y",
            x=0,  # Position the label at the left
            y=service_standard + 40,  # Position the label slightly above the line
            text="Service Standard",
            showarrow=False,
            font=dict(size=18, color="black"),
        ),
        dict(
            xref="paper",
            yref="y",
            x=0,  # Position the label at the left
            y=crush_load + 40,  # Position the label slightly above the line
            text="Crush Load",
            showarrow=False,
            font=dict(size=18, color="black"),
        ),
    ],
)

fig.write_image(OUTPUT_DIRECTORY / "train_loads_no_control_max_holding_180.svg")
fig.show(renderer="browser")

# Save the interactive HTML file to disk
fig.write_html(OUTPUT_DIRECTORY / "train_loads_no_control_max_holding_180.html")


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
        all_data["max_holding=300,period=version_83,schd=PM,station=UIC-Halsted"][
            "passenger_test"
        ],
    ],
    keys=pd.CategoricalIndex(
        ["0", "60", "120", "180", "240", "300"],
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

temp["scenario"] = temp["max_holding"].astype("str")

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

for scenario in ORDERED_SCENARIOS[1:]:
    total_wait_time_pivot[f"Savings ({scenario}s)"] = (
        total_wait_time_pivot["0"]
        - total_wait_time_pivot[scenario]
    )


# Create the plot
fig = go.Figure(
    data=[
        go.Bar(
            x=total_wait_time_pivot.index,
            y=total_wait_time_pivot[f"Savings ({scenario}s)"],
            name=f"Max Holding: {scenario}s",
            text=[
                f"{y:.0f}"
                for y in total_wait_time_pivot[f"Savings ({scenario}s)"]
            ],
            textposition="auto",
            textfont=dict(size=12),
        )
        for scenario in ORDERED_SCENARIOS[1:]
    ],
    layout=go.Layout(
        title=dict(
            text="Savings in Total Daily Wait Time by Origin Station (Northbound)",
            font=dict(size=24),
        ),
        yaxis_title=dict(text="Savings in Wait Times (minutes)", font=dict(size=18)),
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
        "text": "Savings in Total Daily Wait Time by Origin Station (Northbound)",
        "x": 0.5,
        "font": {"size": 24},
    },
    xaxis_title="Origin Station",
    yaxis_title="Savings in Wait Times (minutes)",
)

# Add annotations for total savings in waiting_time for each scenario
for i, scenario in enumerate(ORDERED_SCENARIOS[1:]):
    total_waiting_time_savings = (
        total_wait_time_pivot["0"].sum()
        - total_wait_time_pivot[scenario].sum()
    )
    fig.add_annotation(
        x=0.01,
        y=1.1 - i * 0.06,
        xanchor="left",
        xref="paper",
        yref="paper",
        text=f"Total Wait Time Savings ({scenario}s): {total_waiting_time_savings:.0f} minutes",
        showarrow=False,
        font=dict(size=18),
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

temp["scenario"] = temp["max_holding"].astype("str")

# Step 1: Group the data by scenario, origin, and destination
grouped_data = temp.groupby(["scenario", "origin", "destination"])

# Step 2: Calculate the mean journey time for each group
mean_travel_times = grouped_data["journey_time"].mean().unstack()

# Step 3: Calculate the average number of passengers for each origin-destination pair
avg_passengers = temp.groupby(["origin", "destination", "scenario", "replication_id"])["passenger_id"].count().reset_index().query("passenger_id > 0").groupby(["origin", "destination"])["passenger_id"].mean().unstack()

# Step 4: Calculate the total journey time for each origin and scenario
total_journey_time = (mean_travel_times * avg_passengers).sum(axis=1)

# Step 5: Reset the index to have origin and scenario as columns
total_journey_time = total_journey_time.reset_index().rename(columns={0: "total_journey_time"})

# Pivot the DataFrame to have origin stations as rows and scenarios as columns
total_journey_time_pivot = total_journey_time.pivot(index="origin", columns="scenario", values="total_journey_time")

# Calculate savings for each scenario compared to the no-control scenario
for scenario in ORDERED_SCENARIOS[1:]:
    total_journey_time_pivot[f"Savings ({scenario}s)"] = (
        total_journey_time_pivot["0"]
        - total_journey_time_pivot[scenario]
    )


# Create the plot
fig = go.Figure(
    data=[
        go.Bar(
            x=total_journey_time_pivot.index,
            y=total_journey_time_pivot[f"Savings ({scenario}s)"],
            name=f"Max Holding: {scenario}s",
            text=[
                f"{y:.0f}"
                for y in total_journey_time_pivot[
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
        total_journey_time_pivot["0"].sum()
        - total_journey_time_pivot[scenario].sum()
    )
    fig.add_annotation(
        x=0.01,
        y=1.1 - i * 0.05,
        xanchor="left",
        xref="paper",
        yref="paper",
        text=f"Total Journey Time Savings ({scenario}s): {total_journey_time_savings:.0f} minutes",
        showarrow=False,
        font=dict(size=18),
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
        df_0["number_of_passengers_on_platform_before_stop"].reset_index(drop=True).to_frame("NO-CONTROL"),
        df_180["number_of_passengers_on_platform_before_stop"].reset_index(drop=True).to_frame("Holding at UIC-Halsted (<180s)"),
    ],
    axis=1,
)

# Melt the DataFrame to create a 'Scenario' column
df_plot = df_plot.melt(var_name="Scenario", value_name="Number of Passengers on Platform")

# Define the desired order of scenarios
scenario_order = ["NO-CONTROL", "Holding at UIC-Halsted (<180s)"]

# Convert the 'Scenario' column to a categorical type with the desired order
df_plot["Scenario"] = pd.Categorical(df_plot["Scenario"], categories=scenario_order, ordered=True)

# Sort the DataFrame based on the 'Scenario' column
df_plot = df_plot.sort_values("Scenario")

# Define custom color map
color_map = {"NO-CONTROL": '#1F77B4', "Holding at UIC-Halsted (<180s)": '#D62728'}

# Create the histogram plot with box plot on the margin
fig = px.histogram(
    df_plot,
    x="Number of Passengers on Platform",
    color="Scenario",
    marginal="box",
    barmode="group",
    title="Distribution of Platform Crowding at Clark/Lake",
    labels={"value": "Number of Passengers on Platform"},
    color_discrete_map=color_map,  # Apply custom color map
    category_orders={"Scenario": scenario_order},  # Specify the order of scenarios
)

# Customize the layout
fig.update_layout(
    xaxis_title="Number of Passengers on Platform",
    yaxis_title="Frequency",
    legend_title="Scenario",
    legend=dict(
        traceorder="normal",  # Display legend items in the specified order
        x=1,
        y=1,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(0, 0, 0, 0)",
        borderwidth=0,
    ),
)

# Show the plot
fig.show(renderer="browser")

# Save the plot as an image file
fig.write_image(
    str(
        OUTPUT_DIRECTORY
        / "platform_crowding_distribution_Clark_Lake_holding_vs_no_control.svg"
    ),
    width=1600,
    height=600,
)



# %%
# import plotly.express as px
# import plotly.express as px

# # Filter the data for max_holding=180 and max_holding=0
# df_180 = df_combined[df_combined["max_holding"] == "180"]
# df_0 = df_combined[df_combined["max_holding"] == "0"]

# # Combine the filtered data into a single DataFrame
# df_plot = pd.concat(
#     [
#         df_180[["station_name", "number_of_passengers_on_platform_before_stop"]].assign(
#             Scenario="Holding at UIC-Halsted (<180s)"
#         ),
#         df_0[["station_name", "number_of_passengers_on_platform_before_stop"]].assign(
#             Scenario="NO-CONTROL"
#         ),
#     ],
#     ignore_index=True,
# )

# # Define the desired order of scenarios
# scenario_order = ["Holding at UIC-Halsted (<180s)", "NO-CONTROL"]

# # Convert the 'Scenario' column to a categorical type with the desired order
# df_plot["Scenario"] = pd.Categorical(df_plot["Scenario"], categories=scenario_order, ordered=True)

# # Define custom color map
# color_map = {"NO-CONTROL": '#1F77B4', "Holding at UIC-Halsted (<180s)": '#D62728'}

# fig = px.box(
#     df_plot,
#     x="station_name",
#     y="number_of_passengers_on_platform_before_stop",
#     color="Scenario",
#     title="Platform Crowding at Each Station",
#     labels={
#         "station_name": "Station",
#         "number_of_passengers_on_platform_before_stop": "Number of Passengers on Platform",
#     },
#     category_orders={
#         "station_name": STATION_ORDER
#     },  # Assuming you have defined the station order
#     color_discrete_map=color_map,  # Apply custom color map
# )

# # Customize the layout
# fig.update_layout(
#     xaxis_title="Station",
#     yaxis_title="Number of Passengers on Platform",
#     legend=dict(
#         title="Scenario",
#         x=1,
#         y=1,
#         xanchor="right",
#         yanchor="top",
#         bgcolor="rgba(255, 255, 255, 0.8)",
#         bordercolor="rgba(0, 0, 0, 0)",
#         borderwidth=0,
#     ),
#     xaxis_tickangle=-45,
# )

# # Reduce the size of markers for outliers
# fig.update_traces(marker=dict(size=5))

# # Show the plot
# fig.show(renderer="browser")

# # Save the plot as an image file
# fig.write_image(
#     str(
#         OUTPUT_DIRECTORY
#         / "platform_crowding_boxplot_all_stations_holding_vs_no_control.svg"
#     ),
#     width=1600,
#     height=600,
# )


# %%
# Define the desired order of scenarios and custom color map
scenario_order = ["NO-CONTROL", "Holding at UIC-Halsted (<180s)"]
color_map = {"NO-CONTROL": '#1F77B4', "Holding at UIC-Halsted (<180s)": '#D62728'}

# Filter the data for max_holding=180 and max_holding=0 at Clark/Lake station
df_180_clark_lake = df_combined[
    (df_combined["max_holding"] == "180")
    & (df_combined["station_name"] == "Clark/Lake")
]
df_0_clark_lake = df_combined[
    (df_combined["max_holding"] == "0") & (df_combined["station_name"] == "Clark/Lake")
]

# Combine the filtered data into a single DataFrame for Clark/Lake station
df_plot_clark_lake = pd.concat(
    [
        df_0_clark_lake["number_of_passengers_on_platform_before_stop"].reset_index(drop=True).to_frame("NO-CONTROL"),
        df_180_clark_lake["number_of_passengers_on_platform_before_stop"].reset_index(drop=True).to_frame("Holding at UIC-Halsted (<180s)"),
    ],
    axis=1,
)

# Melt the DataFrame to create a 'Scenario' column for Clark/Lake station
df_plot_clark_lake = df_plot_clark_lake.melt(var_name="Scenario", value_name="Number of Passengers on Platform")

# Convert the 'Scenario' column to a categorical type with the desired order for Clark/Lake station
df_plot_clark_lake["Scenario"] = pd.Categorical(df_plot_clark_lake["Scenario"], categories=scenario_order, ordered=True)

# Sort the DataFrame based on the 'Scenario' column for Clark/Lake station
df_plot_clark_lake = df_plot_clark_lake.sort_values("Scenario")

# Create the histogram plot with box plot on the margin for Clark/Lake station
fig_clark_lake = px.histogram(
    df_plot_clark_lake,
    x="Number of Passengers on Platform",
    color="Scenario",
    marginal="box",
    barmode="group",
    title="Distribution of Platform Crowding at Clark/Lake",
    labels={"value": "Number of Passengers on Platform"},
    color_discrete_map=color_map,
    category_orders={"Scenario": scenario_order},
)

# Customize the layout for Clark/Lake station plot
fig_clark_lake.update_layout(
    xaxis_title="Number of Passengers on Platform",
    yaxis_title="Frequency",
    legend_title="Scenario",
    legend=dict(
        traceorder="normal",
        x=1,
        y=1,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(0, 0, 0, 0)",
        borderwidth=0,
    ),
)

# Show the plot for Clark/Lake station
fig_clark_lake.show(renderer="browser")

# Save the plot for Clark/Lake station as an image file
fig_clark_lake.write_image(
    str(
        OUTPUT_DIRECTORY
        / "platform_crowding_distribution_Clark_Lake_holding_vs_no_control.svg"
    ),
    width=1600,
    height=600,
)

# Filter the data for max_holding=180 and max_holding=0 for all stations
df_180_all = df_combined[df_combined["max_holding"] == "180"]
df_0_all = df_combined[df_combined["max_holding"] == "0"]

# Combine the filtered data into a single DataFrame for all stations
df_plot_all = pd.concat(
    [
        df_180_all[["station_name", "number_of_passengers_on_platform_before_stop"]].assign(
            Scenario="Holding at UIC-Halsted (<180s)"
        ),
        df_0_all[["station_name", "number_of_passengers_on_platform_before_stop"]].assign(
            Scenario="NO-CONTROL"
        ),
    ],
    ignore_index=True,
)

# Convert the 'Scenario' column to a categorical type with the desired order for all stations
df_plot_all["Scenario"] = pd.Categorical(df_plot_all["Scenario"], categories=scenario_order, ordered=True)

# Create the box plot for all stations
fig_all = px.box(
    df_plot_all,
    x="station_name",
    y="number_of_passengers_on_platform_before_stop",
    color="Scenario",
    title="Platform Crowding at Each Station",
    labels={
        "station_name": "Station",
        "number_of_passengers_on_platform_before_stop": "Number of Passengers on Platform",
    },
    category_orders={
        "station_name": STATION_ORDER,
        "Scenario": scenario_order,
    },
    color_discrete_map=color_map,
)

# Customize the layout for all stations plot
fig_all.update_layout(
    xaxis_title="Station",
    yaxis_title="Number of Passengers on Platform",
    legend=dict(
        title="Scenario",
        x=1,
        y=1,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(0, 0, 0, 0)",
        borderwidth=0,
    ),
    xaxis_tickangle=45,

)

# Reduce the size of markers for outliers in all stations plot
fig_all.update_traces(marker=dict(size=3))

# Show the plot for all stations
fig_all.show(renderer="browser")

# Save the plot for all stations as an image file
fig_all.write_image(
    str(
        OUTPUT_DIRECTORY
        / "platform_crowding_boxplot_all_stations_holding_vs_no_control.svg"
    ),
    width=1600,
    height=600,
)

# %%
# Filter the data for max_holding=180 and max_holding=0 for selected stations
df_180_selected = df_combined[
    (df_combined["max_holding"] == "180") &
    (df_combined["station_name"].isin(STATION_ORDER[STATION_ORDER.index("Illinois Medical District"):STATION_ORDER.index("Damen")+1]))
]
df_0_selected = df_combined[
    (df_combined["max_holding"] == "0") &
    (df_combined["station_name"].isin(STATION_ORDER[STATION_ORDER.index("Illinois Medical District"):STATION_ORDER.index("Damen")+1]))
]

# Combine the filtered data into a single DataFrame for selected stations
df_plot_selected = pd.concat(
    [
        df_180_selected[["station_name", "number_of_passengers_on_platform_before_stop"]].assign(
            Scenario="Holding at UIC-Halsted (<180s)"
        ),
        df_0_selected[["station_name", "number_of_passengers_on_platform_before_stop"]].assign(
            Scenario="NO-CONTROL"
        ),
    ],
    ignore_index=True,
)

# Convert the 'Scenario' column to a categorical type with the desired order for selected stations
df_plot_selected["Scenario"] = pd.Categorical(df_plot_selected["Scenario"], categories=scenario_order, ordered=True)

# Create the box plot for selected stations
fig_selected = px.box(
    df_plot_selected,
    x="station_name",
    y="number_of_passengers_on_platform_before_stop",
    color="Scenario",
    title="Platform Crowding at Selected Stations",
    labels={
        "station_name": "Station",
        "number_of_passengers_on_platform_before_stop": "Number of Passengers on Platform",
    },
    category_orders={
        "station_name": STATION_ORDER[STATION_ORDER.index("Illinois Medical District"):STATION_ORDER.index("Damen")+1],
        "Scenario": scenario_order,
    },
    color_discrete_map=color_map,
)

# Customize the layout for selected stations plot
fig_selected.update_layout(
    xaxis_title="Station",
    yaxis_title="Number of Passengers on Platform",
    legend=dict(
        title="Scenario",
        x=1,
        y=1,
        xanchor="right",
        yanchor="bottom",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(0, 0, 0, 0)",
        borderwidth=0,
    ),
    xaxis_tickangle=45,
)

# Reduce the size of markers for outliers in selected stations plot
fig_selected.update_traces(marker=dict(size=3))

# Show the plot for selected stations
fig_selected.show(renderer="browser")

# Save the plot for selected stations as an image file
fig_selected.write_image(
    str(
        OUTPUT_DIRECTORY
        / "platform_crowding_boxplot_selected_stations_holding_vs_no_control.svg"
    ),
    width=1600,
    height=600,
)


# %%
# Filter the data for max_holding=180 and max_holding=0 for all stations
df_180_all = df_combined[df_combined["max_holding"] == "180"]
df_0_all = df_combined[df_combined["max_holding"] == "0"]

# Combine the filtered data into a single DataFrame for all stations
df_plot_all = pd.concat(
    [
        df_180_all[["station_name", "number_of_passengers_on_train_after_stop"]].assign(
            Scenario="Holding at UIC-Halsted (<180s)"
        ),
        df_0_all[["station_name", "number_of_passengers_on_train_after_stop"]].assign(
            Scenario="NO-CONTROL"
        ),
    ],
    ignore_index=True,
)

# Convert the 'Scenario' column to a categorical type with the desired order for all stations
df_plot_all["Scenario"] = pd.Categorical(df_plot_all["Scenario"], categories=scenario_order, ordered=True)
# Define the service standard and crush load values
service_standard = 640
crush_load = 960

# Create the box plot for all stations
fig_all = px.box(
    df_plot_all,
    x="station_name",
    y="number_of_passengers_on_train_after_stop",
    color="Scenario",
    title="Train Load at Each Station",
    labels={
        "station_name": "Station",
        "number_of_passengers_on_train_after_stop": "Number of Passengers on Train After Stop",
    },
    category_orders={
        "station_name": STATION_ORDER,
        "Scenario": scenario_order,
    },
    color_discrete_map=color_map,
)

# Customize the layout for all stations plot
fig_all.update_layout(
    xaxis_title="Station",
    yaxis_title="Number of Passengers on Train After Stop",
    legend=dict(
        title="Scenario",
        x=1,
        y=1,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(0, 0, 0, 0)",
        borderwidth=0,
    ),
    xaxis_tickangle=45,
    shapes=[
        dict(
            type="line",
            yref="y",
            y0=service_standard,
            y1=service_standard,
            xref="paper",
            x0=0,
            x1=1,
            line=dict(
                color="green",
                width=4,
                dash="dash",
            ),
        ),
        dict(
            type="line",
            yref="y",
            y0=crush_load,
            y1=crush_load,
            xref="paper",
            x0=0,
            x1=1,
            line=dict(
                color="red",
                width=4,
                dash="dash",
            ),
        ),
    ],
    annotations=[
        dict(
            xref="paper",
            yref="y",
            x=0,  # Position the label at the left
            y=service_standard + 40,  # Position the label slightly above the line
            text="Service Standard",
            showarrow=False,
            font=dict(size=18, color="black"),
        ),
        dict(
            xref="paper",
            yref="y",
            x=0,  # Position the label at the left
            y=crush_load + 40,  # Position the label slightly above the line
            text="Crush Load",
            showarrow=False,
            font=dict(size=18, color="black"),
        ),
    ],
)

# Reduce the size of markers for outliers in all stations plot
fig_all.update_traces(marker=dict(size=3))

# Show the plot for all stations
fig_all.show(renderer="browser")

# Save the plot for all stations as an image file
fig_all.write_image(
    str(
        OUTPUT_DIRECTORY
        / "train_load_boxplot_all_stations_holding_vs_no_control.svg"
    ),
    width=1600,
    height=600,
)


# %%
# Define the service standard and crush load values
service_standard = 640
crush_load = 960

# Filter the data for max_holding=180 and max_holding=0 for selected stations
df_180_selected = df_combined[
    (df_combined["max_holding"] == "180") &
    (df_combined["station_name"].isin(STATION_ORDER[STATION_ORDER.index("Illinois Medical District"):STATION_ORDER.index("Damen")+1]))
]
df_0_selected = df_combined[
    (df_combined["max_holding"] == "0") &
    (df_combined["station_name"].isin(STATION_ORDER[STATION_ORDER.index("Illinois Medical District"):STATION_ORDER.index("Damen")+1]))
]

# Combine the filtered data into a single DataFrame for selected stations
df_plot_selected = pd.concat(
    [
        df_180_selected[["station_name", "number_of_passengers_on_train_after_stop"]].assign(
            Scenario="Holding at UIC-Halsted (<180s)"
        ),
        df_0_selected[["station_name", "number_of_passengers_on_train_after_stop"]].assign(
            Scenario="NO-CONTROL"
        ),
    ],
    ignore_index=True,
)

# Convert the 'Scenario' column to a categorical type with the desired order for selected stations
df_plot_selected["Scenario"] = pd.Categorical(df_plot_selected["Scenario"], categories=scenario_order, ordered=True)

# Create the box plot for selected stations
fig_selected = px.box(
    df_plot_selected,
    x="station_name",
    y="number_of_passengers_on_train_after_stop",
    color="Scenario",
    title="Train Load at Selected Stations",
    labels={
        "station_name": "Station",
        "number_of_passengers_on_train_after_stop": "Number of Passengers on Train After Stop",
    },
    category_orders={
        "station_name": STATION_ORDER[STATION_ORDER.index("Illinois Medical District"):STATION_ORDER.index("Damen")+1],
        "Scenario": scenario_order,
    },
    color_discrete_map=color_map,
)

# Customize the layout for selected stations plot
fig_selected.update_layout(
    xaxis_title="Station",
    yaxis_title="Number of Passengers on Train After Stop",
    legend=dict(
        title="Scenario",
        x=1,
        y=1,
        xanchor="right",
        yanchor="bottom",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(0, 0, 0, 0)",
        borderwidth=0,
    ),
    xaxis_tickangle=45,
    shapes=[
        dict(
            type="line",
            yref="y",
            y0=service_standard,
            y1=service_standard,
            xref="paper",
            x0=0,
            x1=1,
            line=dict(
                color="green",
                width=4,
                dash="dash",
            ),
        ),
        dict(
            type="line",
            yref="y",
            y0=crush_load,
            y1=crush_load,
            xref="paper",
            x0=0,
            x1=1,
            line=dict(
                color="red",
                width=4,
                dash="dash",
            ),
        ),
    ],
    annotations=[
        dict(
            xref="paper",
            yref="y",
            x=0,  # Position the label at the left
            y=service_standard + 40,  # Position the label slightly above the line
            text="Service Standard",
            showarrow=False,
            font=dict(size=18, color="black"),
        ),
        dict(
            xref="paper",
            yref="y",
            x=0,  # Position the label at the left
            y=crush_load + 40,  # Position the label slightly above the line
            text="Crush Load",
            showarrow=False,
            font=dict(size=18, color="black"),
        ),
    ],
)

# Reduce the size of markers for outliers in selected stations plot
fig_selected.update_traces(marker=dict(size=3))

# Show the plot for selected stations
fig_selected.show(renderer="browser")

# Save the plot for selected stations as an image file
fig_selected.write_image(
    str(
        OUTPUT_DIRECTORY
        / "train_load_boxplot_selected_stations_holding_vs_no_control.svg"
    ),
    width=1600,
    height=600,
)


# %%
