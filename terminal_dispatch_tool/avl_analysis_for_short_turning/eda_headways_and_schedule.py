# %%
# import os

import os
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

start_date = "2024-04-07"
end_date = "2024-05-01"
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
    END AS station_event
FROM
    avas_spectrum.qt2_trainevent
WHERE
    event_time::date BETWEEN :start_date AND :end_date AND
    EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5 AND
    action = 'MOVE' AND
    run_id LIKE 'B%' AND
    scada IN ('nwc720t', 'nwd720t', 'wd452t', 'wc452t', 'wd005t', 'wd013t', 'wd008t', 'wc005t')
ORDER BY
    event_time;

   """
)

results = engine.execute(query_text, {"start_date": start_date, "end_date": end_date})


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

# %%

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

output_directory = "/Users/moji/Presentations/One-on-One Meetings/02-26-2024"


# Define a function to plot each station_event
def plot_station_event(df, station_event):
    # Filter the DataFrame for the current station_event
    df_station = df[df["station_event"] == station_event]

    # Calculate the rolling mean with a 30-minute window
    df_station["rolling_mean"] = (
        df_station["deviation"].ewm(span=30, adjust=False).mean()
    )

    df_station["rolling_mean"] = df_station["deviation"].rolling("60T").mean()

    # Create a scatter plot for the deviations
    scatter = go.Scatter(
        x=df_station["time_of_day"],
        y=df_station["deviation"],
        mode="markers",
        name="Deviation",
        marker=dict(size=5),
        hoverinfo="x+y",
    )

    # Create a line plot for the moving average
    line = go.Scatter(
        x=df_station["time_of_day"],
        y=df_station["rolling_mean"],
        mode="lines",
        name="30-min Moving Average",
        hoverinfo="x+y",
    )

    # Create a subplot for each station_event
    fig = make_subplots(specs=[[{"secondary_y": False}]])
    fig.add_trace(scatter, secondary_y=False)
    fig.add_trace(line, secondary_y=False)

    # Update layout for a better visual appearance
    fig.update_layout(
        title=f"Deviation and 30-min Moving Average for {station_event}",
        xaxis_title="Time of Day",
        yaxis_title="Deviation",
        hovermode="x unified",
    )

    # Show the plot in the browser
    fig.show(renderer="browser")

    filename = f"{station_event.replace(' ', '_')}_deviation_ema.html"
    file_path = os.path.join(output_directory, filename)

    # Write the figure to an HTML file
    fig.write_html(file_path)


# Plot for each unique station_event
for station_event in df["station_event"].unique():
    plot_station_event(df, station_event)


# %%


# %%
