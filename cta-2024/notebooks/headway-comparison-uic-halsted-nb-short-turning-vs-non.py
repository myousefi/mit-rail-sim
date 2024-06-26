# %%
from pathlib import Path
import pandas as pd
import plotly.express as px
from mit_rail_sim.utils.db_con import text, engine

OUTPUT_DIRECTORY = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"

start_date = "2024-04-07"
end_date = "2024-05-31"

query_text = text(
    """
WITH NB_Departures AS (
    SELECT
        run_id,
        headway,
        event_time AS departure_time_at_uic_halsted_nb
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'wc005t' -- UIC-Halsted NB Departure
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
)
SELECT
    NB.run_id,
    NB.headway,
    NB.departure_time_at_uic_halsted_nb,
    CASE
        WHEN SB.event_time IS NOT NULL THEN 'Short Turned'
        ELSE 'Full Service'
    END AS train_type
FROM
    NB_Departures AS NB
LEFT JOIN
    avas_spectrum.qt2_trainevent AS SB
ON
    NB.run_id = SB.run_id
    AND SB.scada = 'wd005t' -- UIC-Halsted SB Departure
    AND SB.event_time BETWEEN NB.departure_time_at_uic_halsted_nb - INTERVAL '45 MINUTES' AND NB.departure_time_at_uic_halsted_nb
WHERE
    NB.departure_time_at_uic_halsted_nb::time BETWEEN '15:00' AND '18:00'
ORDER BY
    NB.departure_time_at_uic_halsted_nb;
   """
)

results = engine.execute(query_text, {"start_date": start_date, "end_date": end_date})

df = pd.DataFrame(results.fetchall(), columns=results.keys())

# %%
# Calculate the IQR
Q1 = df["headway"].quantile(0.25)
Q3 = df["headway"].quantile(0.75)
IQR = Q3 - Q1

# Define the lower and upper bounds for outliers
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Filter the DataFrame to remove outliers
df_filtered = df[(df["headway"] >= lower_bound) & (df["headway"] <= upper_bound)]

# %%
# Plotting the histogram of headways
fig = px.histogram(
    df_filtered,
    x="headway",
    color="train_type",
    title="Distribution of Headways for Trains Leaving UIC Halsted Northbound",
    labels={"headway_minutes": "Headway (minutes)", "train_type": "Train Type"},
    histnorm="percent",
    barmode="group",
    hover_data=df.columns,
    marginal="box",  # Adds a boxplot to the histogram
)
fig.update_layout(
    xaxis_title="Headway (minutes)",
    yaxis_title="Percentage",
    width=800,
    height=500,
)
fig.show(renderer="browser")

# Optionally, save the plot to a file
fig.write_image(
    f"{OUTPUT_DIRECTORY}/northbound_departures_headways_distribution_by_train_type.svg"
)
# %%
# %%
# %%
import pandas as pd

# Calculate summary statistics for each group
summary_stats = df_filtered.groupby("train_type")["headway"].agg(
    [
        "count",
        "mean",
        "std",
        "min",
        lambda x: x.quantile(0.25),
        "median",
        lambda x: x.quantile(0.75),
        "max",
    ]
)

# Reset the index to make "train_type" a regular column
summary_stats.reset_index(inplace=True)

# Rename the columns for better readability
summary_stats.columns = [
    "Train Type",
    "Count",
    "Mean",
    "Standard Deviation",
    "Minimum",
    "25th Percentile",
    "Median",
    "75th Percentile",
    "Maximum",
]

# Transpose the DataFrame to have train types as columns and summary statistics as rows
summary_stats_transposed = summary_stats.set_index("Train Type").T

# Round the values to one decimal place
summary_stats_transposed = summary_stats_transposed.round(1)

summary_stats_transposed.to_clipboard()

summary_stats_transposed

# %%
