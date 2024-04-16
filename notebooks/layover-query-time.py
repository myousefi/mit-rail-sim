# %%
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from mit_rail_sim.utils.db_con import engine, text

pio.templates.default = "simple_white"

start_date, end_date = "2023-11-09", "2023-12-09"

# %%
lay_over_query = text(
    """
    SELECT
        run_id,
        event_time,
        deviation
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        qt2_trackid = :qt2_trackid
        AND action = 'MOVE'
        AND run_id like 'B%'
        AND line_id = 1
        AND event_time::date BETWEEN :start_date AND :end_date
"""
)

sb_df = pd.read_sql(
    lay_over_query,
    engine,
    params={"start_date": start_date, "end_date": end_date, "qt2_trackid": 15700},
)
nb_df = pd.read_sql(
    lay_over_query,
    engine,
    params={"start_date": start_date, "end_date": end_date, "qt2_trackid": 11020},
)
sb_df = sb_df.sort_values(by="event_time")
nb_df = nb_df.sort_values(by="event_time")

sb_df["et"] = sb_df["event_time"]
nb_df["et"] = nb_df["event_time"]

# %%
merged_df = pd.merge_asof(
    sb_df,
    nb_df,
    on="et",
    direction="forward",
    suffixes=("_sb", "_nb"),
)
merged_df["layover_time"] = merged_df["event_time_nb"] - merged_df["event_time_sb"]

merged_df["layover_time"] = merged_df["layover_time"].dt.total_seconds() / 60

merged_df.head()

# %%
import plotly.express as px

merged_df["time_of_day"] = (
    merged_df["event_time_sb"].dt.normalize() - merged_df["event_time_sb"]
) + pd.Timestamp("2023-12-08")

fig = px.scatter(merged_df, x="time_of_day", y="layover_time", title="Layover Times by Time of Day")
fig.update_xaxes(title_text="Time of Day")
fig.update_yaxes(title_text="Layover Time (minutes)")
fig.show()

# %%
import plotly.graph_objects as go

# Define AM and PM peak periods
am_peak_start = 7
am_peak_end = 9
pm_peak_start = 16
pm_peak_end = 18

# Filter data for AM and PM peak periods
am_peak_data = merged_df[
    (merged_df["time_of_day"].dt.hour >= am_peak_start)
    & (merged_df["time_of_day"].dt.hour <= am_peak_end)
]
pm_peak_data = merged_df[
    (merged_df["time_of_day"].dt.hour >= pm_peak_start)
    & (merged_df["time_of_day"].dt.hour <= pm_peak_end)
]

# Create histogram traces for AM and PM peak layover times
am_peak_trace = go.Histogram(x=am_peak_data["layover_time"], name="AM Peak")
pm_peak_trace = go.Histogram(x=pm_peak_data["layover_time"], name="PM Peak")

# Create layout for the histogram plot
layout = go.Layout(
    title="Layover Time Histogram - AM vs PM Peak",
    xaxis=dict(title="Layover Time (minutes)"),
    yaxis=dict(title="Count"),
    barmode="group",
)

# Create figure with the traces and layout
fig = go.Figure(data=[am_peak_trace, pm_peak_trace], layout=layout)

# Display the plot
fig.show()


# %%
import numpy as np
from scipy.stats import expon, gamma, kstest, lognorm, norm

# Define the distributions to test
distributions = [
    ("expon", expon),
    ("lognorm", lognorm),
    ("norm", norm),
    ("gamma", gamma),
]

# Fit and test distributions for AM peak data
am_best_dist = None
am_best_params = None
am_best_ks_stat = np.inf
am_best_p_value = 0

for dist_name, dist in distributions:
    params = dist.fit(am_peak_data["layover_time"])
    ks_stat, p_value = kstest(am_peak_data["layover_time"], dist_name, args=params)
    if ks_stat < am_best_ks_stat:
        am_best_dist = dist_name
        am_best_params = params
        am_best_ks_stat = ks_stat
        am_best_p_value = p_value

# Fit and test distributions for PM peak data
pm_best_dist = None
pm_best_params = None
pm_best_ks_stat = np.inf
pm_best_p_value = 0

for dist_name, dist in distributions:
    params = dist.fit(pm_peak_data["layover_time"])
    ks_stat, p_value = kstest(pm_peak_data["layover_time"], dist_name, args=params)
    if ks_stat < pm_best_ks_stat:
        pm_best_dist = dist_name
        pm_best_params = params
        pm_best_ks_stat = ks_stat
        pm_best_p_value = p_value

print(f"AM Peak Best Fitting Distribution: {am_best_dist}")
print(f"Parameters: {am_best_params}")
print(f"KS Statistic: {am_best_ks_stat:.3f}")
print(f"P-value: {am_best_p_value:.3f}")

print(f"\nPM Peak Best Fitting Distribution: {pm_best_dist}")
print(f"Parameters: {pm_best_params}")
print(f"KS Statistic: {pm_best_ks_stat:.3f}")
print(f"P-value: {pm_best_p_value:.3f}")

# %%
# %%
# %%
