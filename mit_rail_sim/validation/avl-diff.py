from datetime import time

import dash
import numpy as np
import pandas as pd
import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output
from validation_dash import (
    STATION_BLOCK,
    STATION_ORDER,
    calculate_real_travel_times,
    filter_by_time_and_weekday,
)

from mit_rail_sim.utils import find_free_port, project_root

app = dash.Dash(__name__)

app.layout = html.Div(
    [
        dcc.DatePickerRange(
            id="week1-picker",
            start_date=pd.to_datetime("2023-04-01"),  # Set appropriate default dates
            end_date=pd.to_datetime("2023-04-07"),
            display_format="YYYY-MM-DD",
        ),
        dcc.DatePickerRange(
            id="week2-picker",
            start_date=pd.to_datetime("2023-05-01"),
            end_date=pd.to_datetime("2023-05-07"),
            display_format="YYYY-MM-DD",
        ),
        dcc.Graph(id="heatmap-plot"),
    ]
)


@app.callback(
    Output("heatmap-plot", "figure"),
    [
        Input("week1-picker", "start_date"),
        Input("week1-picker", "end_date"),
        Input("week2-picker", "start_date"),
        Input("week2-picker", "end_date"),
    ],
)
def update_heatmap_plot(start_date1, end_date1, start_date2, end_date2):
    # Convert string dates to datetime objects
    start_date1 = pd.to_datetime(start_date1).date()
    end_date1 = pd.to_datetime(end_date1).date()
    start_date2 = pd.to_datetime(start_date2).date()
    end_date2 = pd.to_datetime(end_date2).date()

    # Filter your data for the selected weeks
    week1_data = merged_data[
        (merged_data["date"] >= start_date1) & (merged_data["date"] <= end_date1)
    ]
    week2_data = merged_data[
        (merged_data["date"] >= start_date2) & (merged_data["date"] <= end_date2)
    ]

    start_time, end_time = time(7), time(11)
    week1_data = filter_by_time_and_weekday(week1_data, start_time, end_time)
    # week1_data = remove_holidays(week1_data)

    week2_data = filter_by_time_and_weekday(week2_data, start_time, end_time)
    # week2_data = remove_holidays(week2_data)

    # Initializing a 2D array to store the differences between real and simulation travel times
    diff_matrix = np.zeros((len(STATION_ORDER), len(STATION_ORDER)))

    for i, origin_station in enumerate(STATION_ORDER):
        for j, destination_station in enumerate(STATION_ORDER):
            if (
                j <= i
            ):  # Only consider stations that come after the origin in STATION_ORDER
                continue

            # Filtering the filtered_df to get real_travel_times for the current OD pair
            week_1_travel_times = calculate_real_travel_times(
                week1_data, week1_data, origin_station, destination_station
            )

            # Getting the simulated travel times using your existing function
            week_2_travel_times = calculate_real_travel_times(
                week2_data, week2_data, origin_station, destination_station
            )

            if week_1_travel_times.empty or week_2_travel_times.empty:
                diff_matrix[i, j] = np.nan
                print(f"Missing data for {origin_station} to {destination_station}")
                print(f"Week 1 travel times: {week_1_travel_times}")
                print(f"Week 2 travel times: {week_2_travel_times}")
                continue

            # Assuming percentile is defined, or set a default value
            percentile = 50  # set a suitable default value
            percentile_real = np.percentile(week_1_travel_times, percentile)
            percentile_sim = np.percentile(week_2_travel_times, percentile)

            # Calculating the difference
            diff_matrix[i, j] = percentile_real - percentile_sim

    # Creating the heatmap plot
    fig = px.imshow(
        diff_matrix,
        labels=dict(x="Destination Stations", y="Origin Stations", color="Difference"),
        x=STATION_ORDER,
        y=STATION_ORDER,
        color_continuous_scale="RdBu_r",  # Choose an appropriate color scale
        color_continuous_midpoint=0,  # Set the midpoint of the color scale to 0
    )
    fig.update_layout(title="Heatmap of Week 1 - Week 2 Travel Times")

    # Updating layout to make the plot bigger
    fig.update_layout(
        title="Heatmap of Difference Between Week 1 and Week 2 Travel Times",
        autosize=False,
        width=1000,  # Set figure width
        height=1000,  # Set figure height
    )

    # Show all x-axis and y-axis labels
    fig.update_xaxes(
        tickvals=list(range(len(STATION_ORDER))), ticktext=STATION_ORDER, tickangle=45
    )
    fig.update_yaxes(tickvals=list(range(len(STATION_ORDER))), ticktext=STATION_ORDER)

    return fig


if __name__ == "__main__":
    # Data Preparation
    merged_data = pd.read_csv(
        project_root / "mit_rail_sim" / "validation" / "data" / "track_events.csv",
        parse_dates=["event_time"],
    )
    merged_data["event_datetime"] = pd.to_datetime(merged_data["event_time"])
    merged_data["weekday"] = merged_data["event_datetime"].dt.weekday
    merged_data["date"] = merged_data["event_datetime"].dt.date
    merged_data.sort_values(by=["event_datetime"], inplace=True)
    merged_data["dwell_arrtodep"] = (
        abs(merged_data.groupby(["date", "run_id"])["event_time"].diff(-1)).dt.seconds
        / 60
    )

    merged_data = merged_data[merged_data["scada"].isin(STATION_BLOCK.values())]
    merged_data["station"] = merged_data["scada"].map(
        {v: k for k, v in STATION_BLOCK.items()}
    )

    app.run_server(debug=True, port=find_free_port())
