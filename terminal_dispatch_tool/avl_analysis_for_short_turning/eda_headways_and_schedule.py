# %%
# import os

import os
from re import template
import pandas as pd
import plotly.express as px
# from dotenv import find_dotenv, load_dotenv
# from sqlalchemy import create_engine, text

# load_dotenv(find_dotenv())

# USERNAME = os.getenv("USERNAME")
# PASSWORD = os.getenv("PASSWORD")
# HOST = os.getenv("HOST")
# PORT = os.getenv("PORT")
# DATABASE = os.getenv("DATABASE")

# start_date = os.getenv("start_date")
# end_date = os.getenv("end_date")


# engine = create_engine(
#     f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
# ).connect()
from mit_rail_sim.utils.db_con import engine, text

OUTPUT_DIRECTORY = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"

winter_2023_start_date = "2023-11-13"
winter_2023_end_date = "2024-02-07"
spring_2024_start_date = "2024-04-07"
spring_2024_end_date = "2024-05-31"

query_text = text(
    """
SELECT
    run_id,
    locationdesc,
    deviation,
    headway,
    event_time,
    CASE scada
        WHEN 'nwc720t' THEN 'O-Hare Arrival'
        WHEN 'nwd720t' THEN 'O-Hare Departure'
        WHEN 'wd452t' THEN 'Forest Park Arrival'
        WHEN 'wc452t' THEN 'Forest Park Departure'
        WHEN 'wd005t' THEN 'UIC-Halsted SB Arrival'
        WHEN 'wd013t' THEN 'UIC-Halsted SB Departure'
        WHEN 'wd008t' THEN 'UIC-Halsted NB Arrival'
        WHEN 'wc005t' THEN 'UIC-Halsted NB Departure'
    END AS station_event,
    CASE
        WHEN event_time::date BETWEEN :winter_2023_start_date AND :winter_2023_end_date THEN 'Winter 2023'
        WHEN event_time::date BETWEEN :spring_2024_start_date AND :spring_2024_end_date THEN 'Spring 2024'
    END AS period
FROM
    avas_spectrum.qt2_trainevent
WHERE
    (event_time::date BETWEEN :winter_2023_start_date AND :winter_2023_end_date
     OR event_time::date BETWEEN :spring_2024_start_date AND :spring_2024_end_date)
    AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
    AND action = 'MOVE'
    AND run_id LIKE 'B%'
    AND scada IN ('nwc720t', 'nwd720t', 'wd452t', 'wc452t', 'wd005t', 'wd013t', 'wd008t', 'wc005t')
ORDER BY
    event_time;
"""
)

results = engine.execute(
    query_text,
    {
        "winter_2023_start_date": winter_2023_start_date,
        "winter_2023_end_date": winter_2023_end_date,
        "spring_2024_start_date": spring_2024_start_date,
        "spring_2024_end_date": spring_2024_end_date,
    },
)

df = pd.DataFrame(results.fetchall())

# Convert 'event_time' to datetime if it's not already
df["event_time"] = pd.to_datetime(df["event_time"])

df["time_of_day"] = (
    df["event_time"] - df["event_time"].dt.normalize() + pd.to_datetime("2024-04-07")
)

# Ensure the data is sorted by event_time
df = df.sort_values("time_of_day")

# Set the index to 'event_time' for resampling
df.set_index("time_of_day", drop=False, inplace=True)


# %%

# Calculate interquartile range (IQR) for 'deviation'
Q1 = df["deviation"].quantile(0.25)
Q3 = df["deviation"].quantile(0.75)
IQR = Q3 - Q1

# Filter out the outliers
df = df[(df["deviation"] >= (Q1 - 1.5 * IQR)) & (df["deviation"] <= (Q3 + 1.5 * IQR))]

df["deviation"] = -df["deviation"]


# %%

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Set the theme to 'simple_white'
px.defaults.template = "simple_white"


output_directory = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"


def plot_station_event(df, station_event):
    # Filter the DataFrame for the current station_event
    df_station = df[df["station_event"] == station_event]

    # Create a subplot for each station_event
    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Define colors for each period
    colors = {"Winter 2023": "blue", "Spring 2024": "red"}

    for period in ["Winter 2023", "Spring 2024"]:
        # Filter the DataFrame for the current period
        df_period = df_station[df_station["period"] == period]

        # Calculate the rolling mean with a 30-minute window
        df_period["rolling_mean"] = df_period["deviation"].rolling("60T").mean()

        # Filter out event_times before 00:05
        df_period = df_period[
            df_period["time_of_day"].dt.time >= pd.to_datetime("00:10").time()
        ]

        # Create a scatter plot for the deviations
        scatter = go.Scatter(
            x=df_period["time_of_day"],
            y=df_period["deviation"],
            mode="markers",
            name=f"Delay ({period})",
            marker=dict(size=2, color=colors[period], opacity=0.3),
            hoverinfo="x+y",
            showlegend=False,
        )

        # Create a line plot for the moving average
        line = go.Scatter(
            x=df_period["time_of_day"],
            y=df_period["rolling_mean"],
            mode="lines",
            name=period,
            line=dict(color=colors[period]),
            hoverinfo="x+y",
        )

        fig.add_trace(scatter, secondary_y=False)
        fig.add_trace(line, secondary_y=False)

    # Update layout for a better visual appearance
    fig.update_layout(
        title=f"Delay and 30-min Moving Average for {station_event}",
        xaxis_title="Time of Day",
        yaxis_title="Delay",
        hovermode="x unified",
        template="simple_white",
        legend=dict(
            title="Period",
            x=1,
            y=1,
            xanchor="right",
            yanchor="top",
            orientation="v",
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(0, 0, 0, 1)",
            borderwidth=1,
        ),
    )

    fig.update_xaxes(
        tickformat="%H:%M",
        tickangle=-45,
    )

    # Show the plot in the browser
    fig.show(renderer="browser")

    filename = f"{station_event.replace(' ', '_')}_deviation_ema.html"
    file_path = os.path.join(output_directory, filename)

    # Write the figure to an HTML file
    fig.write_html(file_path)

    # Save the figure as SVG with specified dimensions
    svg_filename = f"{station_event.replace(' ', '_')}_deviation_ema.svg"
    svg_file_path = os.path.join(output_directory, svg_filename)
    fig.write_image(svg_file_path, format="svg", width=1600, height=600)


# Plot for each unique station_event
for station_event in df["station_event"].unique():
    plot_station_event(df, station_event)


# %%


# %%
