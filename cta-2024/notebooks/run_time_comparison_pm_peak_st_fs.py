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
        event_time AS departure_time_at_uic_halsted_nb
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'wc005t' -- UIC-Halsted NB Departure
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
),
NB_Arrivals_OHare AS (
    SELECT
        run_id,
        event_time AS arrival_time_at_ohare
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'nwc724t' -- O'Hare Arrival
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
),
NB_Arrivals_JeffPark AS (
    SELECT
        run_id,
        event_time AS arrival_time_at_jeffpark
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'nwc322t' -- Jefferson Park Arrival
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
),
SB_Departures AS (
    SELECT
        run_id,
        event_time AS departure_time_at_uic_halsted_sb
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'wd005t' -- UIC-Halsted SB Departure
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
)
SELECT
    NB_Dep.run_id,
    NB_Dep.departure_time_at_uic_halsted_nb,
    NB_Arr_OHare.arrival_time_at_ohare,
    NB_Arr_OHare.arrival_time_at_ohare - NB_Dep.departure_time_at_uic_halsted_nb AS run_time_ohare,
    NB_Arr_JeffPark.arrival_time_at_jeffpark,
    NB_Arr_JeffPark.arrival_time_at_jeffpark - NB_Dep.departure_time_at_uic_halsted_nb AS run_time_jeffpark,
    CASE
        WHEN SB_Dep.run_id IS NOT NULL THEN 'Short Turning'
        ELSE 'Full Service'
    END AS service_type
FROM
    NB_Departures AS NB_Dep
LEFT JOIN
    NB_Arrivals_OHare AS NB_Arr_OHare ON NB_Dep.run_id = NB_Arr_OHare.run_id AND
                                NB_Arr_OHare.arrival_time_at_ohare BETWEEN NB_Dep.departure_time_at_uic_halsted_nb + INTERVAL '40 MINUTES' AND NB_Dep.departure_time_at_uic_halsted_nb + INTERVAL '100 MINUTES'
LEFT JOIN
    NB_Arrivals_JeffPark AS NB_Arr_JeffPark ON NB_Dep.run_id = NB_Arr_JeffPark.run_id AND
                                NB_Arr_JeffPark.arrival_time_at_jeffpark BETWEEN NB_Dep.departure_time_at_uic_halsted_nb + INTERVAL '20 MINUTES' AND NB_Dep.departure_time_at_uic_halsted_nb + INTERVAL '60 MINUTES'
LEFT JOIN
    SB_Departures AS SB_Dep ON NB_Dep.run_id = SB_Dep.run_id AND
                                 SB_Dep.departure_time_at_uic_halsted_sb BETWEEN NB_Dep.departure_time_at_uic_halsted_nb - INTERVAL '30 MINUTES' AND NB_Dep.departure_time_at_uic_halsted_nb
WHERE
    NB_Arr_OHare.arrival_time_at_ohare IS NOT NULL OR NB_Arr_JeffPark.arrival_time_at_jeffpark IS NOT NULL
ORDER BY
    NB_Dep.departure_time_at_uic_halsted_nb;
   """
)

results = engine.execute(query_text, {"start_date": start_date, "end_date": end_date})

df = pd.DataFrame(results.fetchall(), columns=results.keys())

# Convert 'run_time_ohare' and 'run_time_jeffpark' to minutes for easier interpretation
df["run_time_ohare_minutes"] = df["run_time_ohare"].dt.total_seconds() / 60
df["run_time_jeffpark_minutes"] = df["run_time_jeffpark"].dt.total_seconds() / 60

# %%
# Filter data for PM peak period (15:00 to 18:00)
pm_peak_data = df[
    (df["departure_time_at_uic_halsted_nb"].dt.hour >= 15)
    & (df["departure_time_at_uic_halsted_nb"].dt.hour < 18)
]

# %%
# Filter out outliers based on 3 IQR rule for both O'Hare and Jefferson Park run times
for col in ["run_time_ohare_minutes", "run_time_jeffpark_minutes"]:
    Q1 = pm_peak_data[col].quantile(0.25)
    Q3 = pm_peak_data[col].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 3 * IQR
    upper_bound = Q3 + 3 * IQR

    pm_peak_data = pm_peak_data[
        (pm_peak_data[col] >= lower_bound) & (pm_peak_data[col] <= upper_bound)
    ]

# %%
# Plotting the distribution of run times for short turning and full service trains to O'Hare
fig_ohare = px.histogram(
    pm_peak_data,
    x="run_time_ohare_minutes",
    color="service_type",
    title="Distribution of Run Times for Short Turning and Full Service Trains to O'Hare",
    labels={
        "run_time_ohare_minutes": "Run Time (minutes)",
        "service_type": "Service Type",
    },
    histnorm="percent",
    barmode="group",
    hover_data=pm_peak_data.columns,
    marginal="box",  # Adds a boxplot to the histogram
)
fig_ohare.update_layout(
    xaxis_title="Run Time (minutes)",
    yaxis_title="Percentage",
    width=800,
    height=500,
)
fig_ohare.show(renderer="browser")

# Optionally, save the plot to a file
fig_ohare.write_image(
    f"{OUTPUT_DIRECTORY}/run_time_distribution_comparison_UIC_OHare.svg"
)

# %%
# Plotting the distribution of run times for short turning and full service trains to Jefferson Park
fig_jeffpark = px.histogram(
    pm_peak_data,
    x="run_time_jeffpark_minutes",
    color="service_type",
    title="Distribution of Run Times for Short Turning and Full Service Trains to Jefferson Park",
    labels={
        "run_time_jeffpark_minutes": "Run Time (minutes)",
        "service_type": "Service Type",
    },
    histnorm="percent",
    barmode="group",
    hover_data=pm_peak_data.columns,
    marginal="box",  # Adds a boxplot to the histogram
)
fig_jeffpark.update_layout(
    xaxis_title="Run Time (minutes)",
    yaxis_title="Percentage",
    width=800,
    height=500,
)
fig_jeffpark.show(renderer="browser")

# Optionally, save the plot to a file
fig_jeffpark.write_image(
    f"{OUTPUT_DIRECTORY}/run_time_distribution_comparison_UIC_JeffPark.svg"
)

# %%
import pandas as pd

# Calculate summary statistics for each group for O'Hare run times
summary_stats_ohare = pm_peak_data.groupby("service_type")[
    "run_time_ohare_minutes"
].agg(
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

# Reset the index to make "service_type" a regular column
summary_stats_ohare.reset_index(inplace=True)

# Rename the columns for better readability
summary_stats_ohare.columns = [
    "Service Type",
    "Count",
    "Mean",
    "Standard Deviation",
    "Minimum",
    "25th Percentile",
    "Median",
    "75th Percentile",
    "Maximum",
]

# Transpose the DataFrame to have service types as columns and summary statistics as rows
summary_stats_ohare_transposed = summary_stats_ohare.set_index("Service Type").T

# Round the values to one decimal place
summary_stats_ohare_transposed = summary_stats_ohare_transposed.round(1)

summary_stats_ohare_transposed.to_clipboard()

print("Summary Statistics for O'Hare Run Times:")
print(summary_stats_ohare_transposed)

# Calculate summary statistics for each group for Jefferson Park run times
summary_stats_jeffpark = pm_peak_data.groupby("service_type")[
    "run_time_jeffpark_minutes"
].agg(
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

# Reset the index to make "service_type" a regular column
summary_stats_jeffpark.reset_index(inplace=True)

# Rename the columns for better readability
summary_stats_jeffpark.columns = [
    "Service Type",
    "Count",
    "Mean",
    "Standard Deviation",
    "Minimum",
    "25th Percentile",
    "Median",
    "75th Percentile",
    "Maximum",
]

# Transpose the DataFrame to have service types as columns and summary statistics as rows
summary_stats_jeffpark_transposed = summary_stats_jeffpark.set_index("Service Type").T

# Round the values to one decimal place
summary_stats_jeffpark_transposed = summary_stats_jeffpark_transposed.round(1)

summary_stats_jeffpark_transposed.to_clipboard()

print("\nSummary Statistics for Jefferson Park Run Times:")
print(summary_stats_jeffpark_transposed)

# %%
