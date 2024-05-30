# %%
# import os

from pathlib import Path
import pandas as pd
import plotly.express as px
# from dotenv import find_dotenv, load_dotenv
# from sqlalchemy import create_engine, text

from mit_rail_sim.utils.db_con import text, engine
# load_dotenv(find_dotenv())

OUTPUT_DIRECTORY = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"

# USERNAME = os.getenv("USERNAME")
# PASSWORD = os.getenv("PASSWORD")
# HOST = os.getenv("HOST")
# PORT = os.getenv("PORT")
# DATABASE = os.getenv("DATABASE")

start_date = "2024-04-07"
end_date = "2024-05-31"

# engine = create_engine(
#     f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
# ).connect()

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
        scada = 'wc005t' -- UIC-Halsted NB Arrival
        AND event_time::date BETWEEN :start_date AND :end_date
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

# Filter out entries with forward or backward headway less than 30 seconds
df = df[
    (df["forward_headway"] >= pd.Timedelta(seconds=30))
    & (df["backward_headway"] >= pd.Timedelta(seconds=30))
]

# Apply IQR outlier filtering on headway_ratio
Q1 = df["headway_ratio"].quantile(0.25)
Q3 = df["headway_ratio"].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
df = df[(df["headway_ratio"] >= lower_bound) & (df["headway_ratio"] <= upper_bound)]


df["deviation"] = -df["deviation"]
fig = px.scatter(
    df,
    x="time_of_day",
    y="headway_ratio",
    hover_data=df.columns,
    labels={"deviation": "Delay"},
    color="deviation",
    color_continuous_scale=px.colors.diverging.RdBu_r,  # symmetric color scale
    color_continuous_midpoint=0,  # centering the color scale around zero
)

# Update the layout to add a title and axis labels
fig.update_layout(
    title="Short Turning Gaps Analysis",
    xaxis_title="Time of Day",
    yaxis_title="Headway Ratio (Forward/Backward)",
    plot_bgcolor="black",
    margin=dict(l=50, r=50, t=50, b=50),
    height=600,
    width=800,
)

# Customize the legend
fig.update_layout(
    legend=dict(
        title="Legend", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
    ),
)

import plotly.graph_objs as go

# Add a horizontal line at y=1
fig.add_trace(
    go.Scatter(
        x=df["time_of_day"],
        y=[1] * len(df),
        mode="lines",
        name="Perfect Line",
        line=dict(color="white", width=2, dash="dash"),
        showlegend=False,
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

fig.show(renderer="browser")

html_output = fig.to_html()

output_file_path = Path(OUTPUT_DIRECTORY + "short_turning_gaps_analysis.html")

with open(output_file_path, "w") as file:
    file.write(html_output)
fig.write_image(
    OUTPUT_DIRECTORY + "short_turning_gaps_analysis.svg", width=700, height=400
)

# %%
# Find the ratio of trains with deviation less than 0 minutes having headway ratio below 1 and time between 15:00 and 18:00

filtered_df = df[
    (df["deviation"] < 0)
    & (df["headway_ratio"] < 1)
    & (df["time_of_day"].dt.hour.between(15, 18))
]

ratio_less_than_0_min_dev = len(filtered_df) / len(
    df[(df["time_of_day"].dt.hour.between(15, 18)) & (df["headway_ratio"] < 1)]
)

print(
    f"Ratio of trains with deviation less than 0 minutes, headway ratio below 1, and time between 15:00-18:00: {ratio_less_than_0_min_dev:.2f}"
)
# %%
# Find the ratio of trains with deviation less than 5 minutes having headway ratio below 1 and time between 15:00 and 18:00
filtered_df = df[
    (df["deviation"] < 5)
    & (df["headway_ratio"] < 1)
    & (df["time_of_day"].dt.hour.between(15, 18))
]
ratio_less_than_5_min_dev = len(filtered_df) / len(
    df[(df["time_of_day"].dt.hour.between(15, 18)) & (df["headway_ratio"] < 1)]
)

print(
    f"Ratio of trains with deviation less than 5 minutes, headway ratio below 1, and time between 15:00-18:00: {ratio_less_than_5_min_dev:.2f}"
)
# %%
import pandas as pd
import plotly.express as px

# Convert headways from timedelta to minutes for easier interpretation and plotting
df["forward_headway_minutes"] = df["forward_headway"].dt.total_seconds() / 60
df["backward_headway_minutes"] = df["backward_headway"].dt.total_seconds() / 60

temp = df.query("event_time.dt.hour.between(15, 18)")
# Plotting the distribution of forward headways
fig_forward = px.histogram(
    data_frame=temp,
    x="forward_headway_minutes",
    title="Distribution of Forward Headways",
    labels={"forward_headway_minutes": "Forward Headway (minutes)"},
    histnorm="percent",
    marginal="box",  # Adds a boxplot to the histogram
    width=800,
    height=500,
)
fig_forward.update_layout(
    xaxis_title="Forward Headway (minutes)",
    yaxis_title="Percentage",
)
fig_forward.show(renderer="browser")

# Plotting the distribution of backward headways
fig_backward = px.histogram(
    temp,
    x="backward_headway_minutes",
    title="Distribution of Backward Headways",
    labels={"backward_headway_minutes": "Backward Headway (minutes)"},
    histnorm="percent",
    marginal="box",  # Adds a boxplot to the histogram
)
fig_backward.update_layout(
    xaxis_title="Backward Headway (minutes)",
    yaxis_title="Percentage",
    width=800,
    height=500,
)
fig_backward.show(renderer="browser")

# Optionally, save the plots to files
fig_forward.write_image(f"{OUTPUT_DIRECTORY}/forward_headways_distribution.svg")
fig_backward.write_image(f"{OUTPUT_DIRECTORY}/backward_headways_distribution.svg")

# %%
query_text = text("""
WITH Departures AS (
    SELECT
        run_id,
        event_time AS departure_time,
        LEAD(event_time) OVER (PARTITION BY scada ORDER BY event_time) AS next_departure_time
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'wc005t' -- Assuming 'wc005t' is the SCADA code for UIC Halsted Northbound Departures
        AND event_time::date BETWEEN :start_date AND :end_date
)
SELECT
    run_id,
    departure_time,
    next_departure_time,
    next_departure_time - departure_time AS headway
FROM
    Departures
WHERE
    next_departure_time IS NOT NULL
ORDER BY
    departure_time;
""")

results = engine.execute(query_text, {"start_date": start_date, "end_date": end_date})
df_all = pd.DataFrame(results.fetchall(), columns=results.keys())

# Convert 'headway' to minutes for easier interpretation
df_all["headway_minutes"] = df_all["headway"].dt.total_seconds() / 60

df_all = df_all.query("departure_time.dt.hour.between(15, 18)")
# Plotting the histogram of headways
fig_all = px.histogram(
    df_all,
    x="headway_minutes",
    title="Distribution of Headways for Trains Leaving UIC Halsted Northbound",
    labels={"headway_minutes": "Headway (minutes)"},
    histnorm="percent",
    hover_data=df_all.columns,
    marginal="box",  # Adds a boxplot to the histogram
)
fig_all.update_layout(
    xaxis_title="Headway (minutes)", yaxis_title="Percentage", width=800, height=500
)
fig_all.show(renderer="browser")

# Optionally, save the plot to a file
fig_all.write_image(
    f"{OUTPUT_DIRECTORY}/northbound_departures_headways_distribution.svg"
)

# %%
combined_headways_df = pd.concat(
    [
        pd.DataFrame(
            {
                "headway_minutes": temp["forward_headway_minutes"].reset_index(
                    drop=True
                ),
                "source": "Short Turning Forward",
            }
        ),
        pd.DataFrame(
            {
                "headway_minutes": temp["backward_headway_minutes"].reset_index(
                    drop=True
                ),
                "source": "Short Turning Backward",
            }
        ),
        pd.DataFrame(
            {
                "headway_minutes": df_all["headway_minutes"].reset_index(drop=True),
                "source": "All Northbound Departures",
            }
        ),
    ],
    axis=0,
)

# Filter out outliers from combined_headways_df using 3 IQR rule
Q1 = combined_headways_df["headway_minutes"].quantile(0.25)
Q3 = combined_headways_df["headway_minutes"].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 3 * IQR
upper_bound = Q3 + 3 * IQR
combined_headways_df = combined_headways_df[
    (combined_headways_df["headway_minutes"] >= lower_bound)
    & (combined_headways_df["headway_minutes"] <= upper_bound)
]

# %%
fig_combined = px.histogram(
    combined_headways_df,
    x="headway_minutes",
    color="source",
    title="Distribution of Headways",
    labels={"headway_minutes": "Headway (minutes)", "source": "Source"},
    histnorm="percent",
    barmode="group",
    hover_data=combined_headways_df.columns,
    marginal="box",  # Adds a boxplot to the histogram
)
fig_combined.update_layout(
    xaxis_title="Headway (minutes)",
    yaxis_title="Percentage",
)
fig_combined.show(renderer="browser")

# Optionally, save the plot to a file
fig_combined.write_image(f"{OUTPUT_DIRECTORY}/combined_headways_distribution.svg")

# %%
