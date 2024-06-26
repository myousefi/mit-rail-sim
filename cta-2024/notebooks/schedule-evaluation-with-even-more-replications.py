# %%
import os
from pathlib import Path
import re
import pandas as pd
import glob
import plotly.io as pio


# pio.templates.default = "simple_white"
pio.renderers.default = "browser"

OUTPUT_DIRECTORY = Path(
    "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/sch-eval-more-reps/"
)

if not os.path.exists(OUTPUT_DIRECTORY):
    os.makedirs(OUTPUT_DIRECTORY)


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


directory = "/Users/moji/Projects/mit_rail_sim/cta-2024/mid_route_holding_even_more_replications/"

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

# %%

data = {}
data["AM"] = all_data[
    "period=version_83,schd=AM,station=NO-CONTROL"
]
data["PM"] = all_data[
    "period=version_83,schd=PM,station=NO-CONTROL"
]
# %%
from mit_rail_sim.validation.validation_dash import STATION_ORDER
import plotly.express as px


def alighting_boarding_figures(simulation_results):
    simulation_results = simulation_results[
        simulation_results["station_name"].isin(STATION_ORDER)
    ]
    sorted_simulation_results = simulation_results.sort_values(
        ["station_name", "direction"]
    )
    sorted_simulation_results["station_name"] = sorted_simulation_results[
        "station_name"
    ].astype("category")
    sorted_simulation_results["station_name"] = sorted_simulation_results[
        "station_name"
    ].cat.set_categories(STATION_ORDER, ordered=True)
    sorted_simulation_results = sorted_simulation_results.sort_values(["station_name"])
    fig_boarded = px.box(
        sorted_simulation_results,
        x="station_name",
        y="number_of_passengers_boarded",
        color="direction",
    )
    fig_boarded.update_layout(
        title=f"Boarding - {schd}",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
    )

    fig_alighted = px.box(
        sorted_simulation_results,
        x="station_name",
        y="number_of_passengers_alighted",
        color="direction",
    )
    fig_alighted.update_layout(
        title=f"Alighting - {schd}",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
    )

    fig_on_train = px.box(
        sorted_simulation_results,
        x="station_name",
        y="number_of_passengers_on_train_after_stop",
        color="direction",
        labels={
            "direction": "Direction",
        },
    )
    fig_on_train.update_layout(
        title=f"Train Load - {schd}",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
    )

    return fig_boarded, fig_alighted, fig_on_train


# %%
# df1 = all_data["experiment"]["station_test"]
for schd, df in data.items():
    df = df["station_test"]
    fig_boarded, fig_alighted, fig_on_train = alighting_boarding_figures(df)

    fig_boarded.show()
    fig_alighted.show()

    fig_on_train.update_layout(
        width=1100,
        height=600,
        xaxis=dict(tickangle=45),
    )

    fig_on_train.update_traces(
        marker=dict(
            size=3,
            # opacity=0.1,
        )
    )  # Adjust size as needed

    fig_on_train.update_layout(
        shapes=[
            dict(
                type="line",
                yref="y",
                y0=640,
                y1=640,
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
                y0=960,
                y1=960,
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
                y=680,  # Position the label slightly above the line
                text="Service Standard",
                showarrow=False,
                font=dict(size=22, color="black"),
            ),
            dict(
                xref="paper",
                yref="y",
                x=0,  # Position the label at the left
                y=1000,  # Position the label slightly above the line
                text="Crush Load",
                showarrow=False,
                font=dict(size=22, color="black"),
            ),
        ],
    )

    fig_on_train.show(renderer="browser")

    fig_on_train.write_image(
        OUTPUT_DIRECTORY / f"train_loads_{schd}_both_direction.svg"
    )


colors = fig_on_train.data[0].marker.color, fig_on_train.data[1].marker.color
print(colors)

# %%
for schd, df in data.items():
    df = df["station_test"]

    df["station_name"] = df["station_name"].replace("Western (O-Hare Branch)", "Western")

    total_passengers = df.groupby(["station_name", "direction"])[
        "number_of_passengers_boarded"
    ].sum()
    denied_boardings = df.groupby(["station_name", "direction"])[
        "denied_boarding"
    ].sum()
    percentage_denied_boardings = (denied_boardings / total_passengers) * 100

    percentage_denied_boardings = percentage_denied_boardings[
        percentage_denied_boardings > 0
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=percentage_denied_boardings.reset_index()["station_name"],
                y=percentage_denied_boardings.values,
                text=[
                    f"{y:.1f}%" for y in percentage_denied_boardings.values
                ],  # Format as percentage with one significant digit
                # textfont=dict(size=18),
                textposition="auto",
                marker_color=percentage_denied_boardings.reset_index()["direction"].map(
                    {
                        "Northbound": colors[0],  # Adjust color mapping as needed
                        "Southbound": colors[1],
                    }
                ),
                name="Denied Boardings",
            )
        ]
    )

    fig.update_layout(
        title=f"Percentage of Denied Boardings by Station and Direction - {schd}",
        xaxis_title="Station",
        yaxis_title="Percentage",
        yaxis=dict(ticksuffix="%", range=[0, 4]),
        legend_title="Direction",
        legend=dict(
            yanchor="top",
            xanchor="right",
            traceorder="normal",
            # font=dict(size=14),
        ),
        xaxis=dict(
            tickangle=45
        ),  # Add this line to ensure x-axis labels are not rotated
    )

    fig.show(renderer="browser")

    fig.write_image(OUTPUT_DIRECTORY / f"denied-boarfing-percentage-{schd}.svg")

# %%

for schd in data.keys():
    df = data[schd]["station_test"]

    df["station_name"] = df["station_name"].replace("Western (O-Hare Branch)", "Western")
    
    if schd == "AM":
        df = df[(df["time_in_seconds"] > 6 * 3600) & (df["time_in_seconds"] < 7 * 3600)]
    elif schd == "PM":
        df = df[
            (df["time_in_seconds"] > 16 * 3600) & (df["time_in_seconds"] < 17 * 3600)
        ]
    else:
        raise ValueError("schd should be AM or PM.")

    total_passengers = df.groupby(["station_name", "direction"])[
        "number_of_passengers_boarded"
    ].sum()
    denied_boardings = df.groupby(["station_name", "direction"])[
        "denied_boarding"
    ].sum()
    percentage_denied_boardings = (denied_boardings / total_passengers) * 100

    percentage_denied_boardings = percentage_denied_boardings[
        percentage_denied_boardings > 0
    ]
        

    fig = go.Figure(
        data=[
            go.Bar(
                x=percentage_denied_boardings.reset_index()["station_name"],
                y=percentage_denied_boardings.values,
                text=[
                    f"{y:.1f}%" for y in percentage_denied_boardings.values
                ],  # Format as percentage with one significant digit
                # textfont=dict(size=18),
                textposition="auto",
                marker_color=percentage_denied_boardings.reset_index()["direction"].map(
                    {
                        "Northbound": colors[0],  # Adjust color mapping as needed
                        "Southbound": colors[1],
                    }
                ),
                name="Denied Boardings",
            )
        ]
    )

    fig.update_layout(
        title=f"Percentage of Denied Boardings by Station and Direction - {'6:00-7:00' if schd=='AM' else '16:00-17:00'}",
        xaxis_title="Station",
        yaxis_title="Percentage",
        yaxis=dict(ticksuffix="%", range=[0, 4]),
        legend_title="Direction",
        legend=dict(
            yanchor="top",
            xanchor="right",
            traceorder="normal",
            # font=dict(size=14),
        ),
        xaxis=dict(
            tickangle=45
        ),  # Add this line to ensure x-axis labels are not rotated
    )

    fig.show(renderer="browser")

    fig.write_image(OUTPUT_DIRECTORY / f"denied-boarfing-percentage-peak-hour-{schd}.svg")

# %%
for schd in data.keys():
    df = data[schd]["station_test"]

    df["hour"] = df["time_in_seconds"] // 3600 % 24

    # Group by hour and sum denied boardings
    denied_boardings_by_hour = (
        df.groupby("hour")
        .agg(denied_boardings=("denied_boarding", "sum"))
        .reset_index()
    )

    # Display the results
    print(f"Denied Boardings by Hour for {schd}:")
    print(denied_boardings_by_hour)

# %%
import pandas as pd
import plotly.graph_objects as go

for schd in data.keys():
    df = data[schd]["station_test"]

    # Convert time_in_seconds to HH:MM format
    df["time_hhmm"] = pd.to_datetime(df["time_in_seconds"], unit="s").dt.strftime(
        "%H:%M"
    )

    # Filter out rows where denied_boarding is zero
    df_filtered = df[df["denied_boarding"] > 0]

    df_filtered["datetime"] = pd.to_datetime(df_filtered["time_in_seconds"], unit="s")

    df_filtered.set_index("datetime", inplace=True, drop=False)
    df_filtered.sort_index(inplace=True)

    # Calculate the 30-minute moving average of denied_boarding
    df_filtered["denied_boarding_ma"] = (
        df_filtered["denied_boarding"].rolling("30min").mean()
    )

    # Create the scatter plot
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_filtered["time_hhmm"],
            y=df_filtered["denied_boarding"],
            mode="markers",
            name="Denied Boarding",
            hovertemplate="Time: %{x}<br>Denied Boarding: %{y}<br>Station: %{customdata[0]}<br>Direction: %{customdata[1]}",
            customdata=df_filtered[["station_name", "direction"]],
            marker=dict(size=6, opacity=0.7),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_filtered["time_hhmm"],
            y=df_filtered["denied_boarding_ma"],
            mode="lines",
            name="30-min Moving Average",
            hovertemplate="Time: %{x}<br>Denied Boarding (MA): %{y:.2f}",
            line=dict(color="red", width=2),
        )
    )

    fig.update_layout(
        title=f"Denied Boarding vs Time - {schd}",
        xaxis_title="Time (HH:MM)",
        yaxis_title="Denied Boarding",
        width=1200,
        height=600,
    )

    fig.show(renderer="browser")

    fig.write_image(OUTPUT_DIRECTORY / f"denied_boarding_vs_time_{schd}.svg")
# %%
# df = all_data["experiment"]["station_test"].copy()
for schd, df in data.items():
    df = df["station_test"]

    direction = "Northbound" if schd == "PM" else "Southbound"

    df["is_short_turning"] = df.groupby(["replication_id", "train_id"])[
        "is_short_turning"
    ].transform("max")

    df["is_short_turning"] = df["is_short_turning"].replace({True: "Short Truning", False: "Full Service"})

    df = df[df["direction"] == direction]

    fig = px.box(
        df,
        x="station_name",
        y="number_of_passengers_on_train_after_stop",
        color="is_short_turning",
        points="outliers",
        labels={
            "number_of_passengers_on_train_after_stop": "Number of Passengers",
            "is_short_turning": "Train Type",
            "station_name": "Station",
        },
        width=1600,
        height=600,
    )

    fig.update_layout(
        title=f"Train Load - {schd} - {direction}",
        xaxis_title="Station",
        xaxis=dict(tickangle=45),
        yaxis_title="Number of Passengers",
        yaxis=dict(range=[0, 1000]),
    )

    fig.update_traces(
        marker=dict(size=1),
    )

    fig.update_layout(
        title=f"Train Load - {schd} - {direction}",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
        yaxis=dict(range=[0, 1000]),
        shapes=[
            dict(
                type="line",
                yref="y",
                y0=640,
                y1=640,
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
                y0=960,
                y1=960,
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
                y=680,  # Position the label slightly above the line
                text="Service Standard",
                showarrow=False,
                font=dict(size=18, color="black"),
            ),
            dict(
                xref="paper",
                yref="y",
                x=0,  # Position the label at the left
                y=1000,  # Position the label slightly above the line
                text="Crush Load",
                showarrow=False,
                font=dict(size=18, color="black"),
            ),
        ],
    )

    fig.show(renderer="browser")

    fig.write_image(
        OUTPUT_DIRECTORY / f"train_load_{schd}_short_turned_comparison.svg",
    )

# %%
import plotly.graph_objects as go

# Define the service standard
service_standard = 640

for schd, df in data.items():
    df = df["station_test"]
    direction = "Northbound" if schd == "PM" else "Southbound"
    # Create a new column that indicates whether the number of passengers exceeds the service standard
    df["exceeds_service_standard"] = (
        df["number_of_passengers_on_train_after_stop"] > service_standard
    )

    df = df[df["direction"] == direction]

    # Calculate the percentage for each station
    percentage_exceeds_service_standard = (
        df.groupby("station_name")["exceeds_service_standard"].mean() * 100
    )

    # Convert the Series to a DataFrame and reset the index
    percentage_exceeds_service_standard_df = (
        percentage_exceeds_service_standard.reset_index()
    )

    # Rename the columns
    percentage_exceeds_service_standard_df.columns = [
        "Station",
        "Percentage Exceeding Service Standard",
    ]

    # Display the DataFrame
    percentage_exceeds_service_standard_df
    # Calculate the percentage for each station
    percentage_exceeds_service_standard = (
        df.groupby("station_name")["exceeds_service_standard"].mean() * 100
    )

    # Convert the Series to a DataFrame and reset the index
    percentage_exceeds_service_standard_df = (
        percentage_exceeds_service_standard.reset_index()
    )

    # Rename the columns
    percentage_exceeds_service_standard_df.columns = [
        "Station",
        "Percentage Exceeding Service Standard",
    ]

    # Filter out the stations with non-zero values
    non_zero_stations = percentage_exceeds_service_standard_df[
        percentage_exceeds_service_standard_df["Percentage Exceeding Service Standard"]
        > 0
    ]

    # Convert the DataFrame to a markdown table
    non_zero_stations_markdown = non_zero_stations.round(1).to_markdown(index=False)
    print(schd)
    # Print the markdown table
    print(non_zero_stations_markdown)

    # Copy the DataFrame to the clipboard
    non_zero_stations.round(1).to_clipboard(index=False)

# %%

for schd, df in data.items():
    df = df["station_test"]
    direction = "Northbound" if schd == "PM" else "Southbound"

    # Set the "direction" column as an ordered category
    df["direction"] = pd.Categorical(
        df["direction"], categories=["Northbound", "Southbound"], ordered=True
    )

    fig = px.box(
        df,
        x="station_name",
        y="number_of_passengers_on_platform_before_stop",
        color="direction",
        labels={
            "number_of_passengers_on_platform_before_stop": "Number of Passengers",
            "station_name": "Station",
            "direction": "Direction",
        },
        category_orders={"direction": ["Northbound", "Southbound"]},
    )

    fig.update_layout(
        title=f"Platform Crowding - {schd}",
        xaxis_title="Station",
        yaxis_title="Number of Passengers",
        width=1600,
        height=600,
        xaxis=dict(tickangle=45),
    )

    fig.update_traces(
        marker=dict(size=1),
    )

    # Add meaningful horizontal grid lines
    max_passengers = df["number_of_passengers_on_platform_before_stop"].max()
    grid_interval = 50  # Adjust this value based on your desired interval
    fig.update_yaxes(
        dtick=grid_interval,
        range=[0, max_passengers + grid_interval],
        gridcolor="black",
        gridwidth=2,
    )

    fig.show(renderer="browser")

    fig.write_image(OUTPUT_DIRECTORY / f"platform_crowding_{schd}.svg")

# %%
