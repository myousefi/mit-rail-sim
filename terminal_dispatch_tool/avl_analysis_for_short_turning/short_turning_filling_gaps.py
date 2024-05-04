# %%
# %%
import os

import pandas as pd
import plotly.express as px
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(find_dotenv())

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")

start_date = "2024-04-07"
end_date = "2024-05-01"

engine = create_engine(
    f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
).connect()

query_text = text(
    """
WITH NB_Arrivals AS (
    SELECT
        run_id,
        deviation,
        event_time AS arrival_time_at_uic_halsted_nb,
        LAG(event_time) OVER (PARTITION BY scada ORDER BY event_time) AS previous_arrival_time,
        LEAD(event_time) OVER (PARTITION BY scada ORDER BY event_time) AS next_arrival_time
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'wc011t' -- UIC-Halsted NB Arrival
        AND event_time::date BETWEEN '2024-02-13' AND '2024-02-26'
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
)
SELECT
    NB.run_id,
    NB.deviation,
    NB.arrival_time_at_uic_halsted_nb,
    NB.previous_arrival_time,
    NB.next_arrival_time,
    NB.arrival_time_at_uic_halsted_nb - NB.previous_arrival_time AS backward_headway,
    NB.next_arrival_time - NB.arrival_time_at_uic_halsted_nb AS forward_headway,
    SB.event_time AS departure_time_at_uic_halsted_sb
FROM
    NB_Arrivals AS NB
JOIN
    avas_spectrum.qt2_trainevent AS SB
ON
    NB.run_id = SB.run_id
    AND SB.scada = 'wd005t' -- UIC-Halsted SB Departure
    AND SB.event_time BETWEEN NB.arrival_time_at_uic_halsted_nb - INTERVAL '30 MINUTES' AND NB.arrival_time_at_uic_halsted_nb
ORDER BY
    NB.run_id, NB.arrival_time_at_uic_halsted_nb;
   """
)

results = engine.execute(query_text, {"start_date": start_date, "end_date": end_date})

df = pd.DataFrame(results.fetchall(), columns=results.keys())

# Convert 'event_time' to datetime if it's not already
df["event_time"] = pd.to_datetime(df["arrival_time_at_uic_halsted_nb"])

df["time_of_day"] = (
    df["event_time"] - df["event_time"].dt.normalize() + pd.to_datetime("2024-04-07")
)

# Ensure the data is sorted by event_time
df = df.sort_values("time_of_day")

# Set the index to 'event_time' for resampling
df.set_index("time_of_day", drop=False, inplace=True)


# %%
import plotly.express as px

# Create a scatter plot of the arrival times at UIC-Halsted NB
fig = px.scatter(
    df,
    x="arrival_time_at_uic_halsted_nb",
    y="run_id",
    title="Arrivals at UIC-Halsted NB with Corresponding SB Departures within 30 Minutes",
    hover_data=df.columns,
    labels={
        "arrival_time_at_uic_halsted_nb": "Arrival Time at UIC-Halsted NB",
        "run_id": "Run ID",
    },
)

# Show the plot
fig.show()

# %%
df["headway_ratio"] = df["forward_headway"] / df["backward_headway"]

fig = px.scatter(
    df,
    x="time_of_day",
    y="headway_ratio",
    hover_data=df.columns,
    color="deviation",
    color_continuous_scale=px.colors.diverging.Geyser,  # symmetric color scale
    color_continuous_midpoint=0,  # centering the color scale around zero
)

# Update the layout to add a title and axis labels
fig.update_layout(
    title="Short Turning Gaps Analysis",
    xaxis_title="Time of Day",
    yaxis_title="Headway Ratio (Forward/Backward)",
    plot_bgcolor="white",
    margin=dict(l=50, r=50, t=50, b=50),
    height=600,
    width=800,
)

# Customize the legend
fig.update_layout(
    legend=dict(
        title="Legend", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
    )
)

import plotly.graph_objs as go

# Add a horizontal line at y=1
fig.add_trace(
    go.Scatter(
        x=df["time_of_day"],
        y=[1] * len(df),
        mode="lines",
        name="Perfect Line",
        line=dict(color="black", width=2, dash="dash"),
    )
)
fig.update_yaxes(type="log")

# Customize the axes
fig.update_xaxes(
    tickangle=-45,
    tickformat="%H:%M",  # assuming x-axis is time of day
    showgrid=True,
    gridcolor="LightGrey",
)
fig.update_yaxes(showgrid=True, gridcolor="LightGrey")

fig.show()

html_output = fig.to_html()
output_file_path = "/Users/moji/Presentations/One-on-One Meetings/02-26-2024/short_turning_gaps_analysis.html"
with open(output_file_path, "w") as file:
    file.write(html_output)


# %%
