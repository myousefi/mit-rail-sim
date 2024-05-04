# %%
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import Input, Output, callback, dcc, html
from sqlalchemy import create_engine, text

from mit_rail_sim.utils import find_free_port
from mit_rail_sim.utils.db_con import engine, text

pio.templates.default = "simple_white"

pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 500)

# %%

version = 83
query = text(
    """
        SELECT
    version,
    tripno,
    blockno,
    route,
    patternid,
    starttp,
    endtp,
    car_length,
    triptype,
    revenue,
    ctadaytype,
    ctadaymap,
    schd_tripstart,
    schd_tripend,
    start_daymap,
    end_daymap,
    tripstart,
    tripend,
    nextday,
    tripend_mn,
    laystart,
    layend,
    tripid,
    blockid,
    prev_trip,
    next_trip,
    startpull,
    endpull,
    dhstart,
    dhend
FROM
    schedule_dimension.schd_rail_trips
WHERE
    version = :version
    AND route = 'Blue'
    AND ctadaymap = 1
"""
)

results = engine.execute(query, params={"version": version})
df = pd.DataFrame(results.fetchall())

# %%
MARKER_ABS_DIST = {
    "Y  Fpk": 0,
    "FstPkS": 413,
    "FstPkN": 413,
    "MgnMTN": 45932,
    "MgnMTS": 45932,
    "HsnJtE": 43750,
    "HsnJtW": 43750,
    "Y  54": 15379,
    "54thPE": 15579,
    "54thPW": 15579,
    "FosMTN": 111310,
    "FosMTS": 111310,
    "OHareN": 145290,
    "OHareS": 145290,
    "Y  Rst": 146290,
}
# %%
df["starttp_abs_dist"] = df["starttp"].map(MARKER_ABS_DIST)
df["endtp_abs_dist"] = df["endtp"].map(MARKER_ABS_DIST)


import datetime


def seconds_to_time(seconds):
    return pd.to_datetime(seconds, unit="s")


df["schd_tripstart_time"] = df["schd_tripstart"].apply(seconds_to_time)
df["schd_tripend_time"] = df["schd_tripend"].apply(seconds_to_time)

df.head()
# %%
import plotly.express as px

fig = px.timeline(
    df,
    x_start="schd_tripstart_time",
    x_end="schd_tripend_time",
    y="tripno",
    # hover_name="tripid",
    hover_data=df.columns.to_list(),
)

fig.update_yaxes(autorange="reversed")
fig.show(renderer="browser")


# %%
df_filtered = df[df["endtp"] == "FstPkS"]

df_filtered["lay_diff"] = abs(df_filtered["layend"] - df_filtered["laystart"]) / 60
fig = px.histogram(
    df_filtered,
    x="lay_diff",
    title="Layover Duration Distribution (Trips ending at FstPkS)",
    labels={"lay_diff": "Layover Duration (minutes)"},
    nbins=30,
)

fig.update_layout(
    xaxis_title="Layover Duration (minutes)",
    yaxis_title="Frequency",
)

fig.show(renderer="browser")

fig.write_html(
    "/Users/moji/Library/CloudStorage/GoogleDrive-mojtaba.yousefi2@gmail.com/My Drive/Weekly Meetings with Haris/March 25 2024/layover_duration_distribution_FstPkS.html"
)

# %%
fig = px.scatter(
    df_filtered,
    x="schd_tripend_time",
    y="lay_diff",
    hover_data=df_filtered.columns.to_list(),
    title="Layover Duration vs Trip End Time (Trips ending at FstPkS)",
    labels={
        "lay_diff": "Layover Duration (minutes)",
        "schd_tripend_time": "Trip End Time",
    },
)

fig.update_layout(
    xaxis_title="Trip End Time",
    yaxis_title="Layover Duration (minutes)",
)

fig.show(renderer="browser")

fig.write_html(
    "/Users/moji/Library/CloudStorage/GoogleDrive-mojtaba.yousefi2@gmail.com/My Drive/Weekly Meetings with Haris/March 25 2024/layover_duration_vs_trip_end_time.html"
)


# %%
import numpy as np

# Calculate the 95th percentile of lay_diff
lay_diff_95 = np.percentile(df_filtered["lay_diff"], 95)

# Filter the dataframe for lay_diff greater than or equal to the 95th percentile
df_high_lay_diff = df[df["lay_diff"] >= lay_diff_95]

# Plotting all information for the highest lay_diff (95% and up)
fig = px.scatter(
    df_high_lay_diff,
    x="lay_diff",
    y="tripno",
    size="lay_diff",
    hover_data=[
        "tripno",
        "tripid",
        "blockno",
        "blockid",
        "endpull",
        "starttp",
        "endtp",
        "schd_tripstart_time",
        "schd_tripend_time",
    ],
    title="High Layover Duration (95% and up)",
    labels={"lay_diff": "Layover Duration (minutes)", "tripno": "Trip Number"},
)
fig.update_layout(
    xaxis_title="Layover Duration (minutes)",
    yaxis_title="Trip Number",
    title="High Layover Duration Analysis (95% and up)",
)
fig.show(renderer="browser")

fig.write_html(
    "/Users/moji/Library/CloudStorage/GoogleDrive-mojtaba.yousefi2@gmail.com/My Drive/Weekly Meetings with Haris/March 25 2024/high_layover_duration_analysis.html"
)
# %%
for column in sorted(
    df_high_lay_diff.columns,
    key=lambda x: len(df_high_lay_diff[x].unique()),
    reverse=True,
):
    print(f"{column}:")
    # print(sorted(df_high_lay_diff[column].unique(), reverse=True))
    # print()


# %%
df.head()
# %%
from ydata_profiling import ProfileReport

profile = ProfileReport(df, title="Pandas Profiling Report", explorative=True)

profile.to_file(
    "/Users/moji/Library/CloudStorage/GoogleDrive-mojtaba.yousefi2@gmail.com/My Drive/Weekly Meetings with Haris/March 25 2024/pandas_profiling_report.html"
)

# %%
