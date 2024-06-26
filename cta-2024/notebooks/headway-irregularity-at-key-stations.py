# %%
import pandas as pd
from mit_rail_sim.utils.db_con import engine, text

query = text(
    """
    WITH filtered_events AS (
        SELECT
            event_time,
            run_id,
            deviation,
            headway,
            CASE
                WHEN scada = 'dd210t' THEN 'Division SB'
                WHEN scada = 'dc138t' THEN 'Grand NB'
            END AS station,
            CASE
                WHEN event_time >= '2023-11-13' AND event_time < '2024-02-07' THEN 'Winter 2023'
                WHEN event_time >= '2024-04-07' AND event_time < '2024-05-20' THEN 'Spring 2024'
            END AS season
        FROM
            avas_spectrum.qt2_trainevent
        WHERE
            scada IN ('dd210t', 'dc138t')
            AND (
                (event_time >= '2023-11-13' AND event_time < '2024-02-07')
                OR (event_time >= '2024-04-07' AND event_time < '2024-05-20')
            )
    )
    SELECT
        *,
        CASE
            WHEN EXTRACT(HOUR FROM event_time) BETWEEN 7 AND 9 THEN 'AM Peak'
            WHEN EXTRACT(HOUR FROM event_time) BETWEEN 16 AND 18 THEN 'PM Peak'
        END AS peak_period
    FROM
        filtered_events
    WHERE
        (station = 'Division SB' AND EXTRACT(HOUR FROM event_time) BETWEEN 7 AND 9)
        OR (station = 'Grand NB' AND EXTRACT(HOUR FROM event_time) BETWEEN 16 AND 18)
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5  -- Filter weekdays (Monday to Friday)
    ORDER BY
        event_time
    """
)


with engine.connect() as connection:
    result = connection.execute(query)
    rows = result.fetchall()

df = pd.DataFrame(rows, columns=result.keys())

# Convert data types
df["deviation"] = pd.to_numeric(df["deviation"], errors="coerce")
df["headway"] = pd.to_numeric(df["headway"], errors="coerce")
df["event_time"] = pd.to_datetime(df["event_time"])
df["station"] = df["station"].astype("object")

# %%
# Filter df using IQR of 3 on headway and deviation
Q1_headway = df["headway"].quantile(0.25)
Q3_headway = df["headway"].quantile(0.75)
IQR_headway = Q3_headway - Q1_headway

Q1_deviation = df["deviation"].quantile(0.25)
Q3_deviation = df["deviation"].quantile(0.75)
IQR_deviation = Q3_deviation - Q1_deviation

df_filtered = df[
    (df["headway"] >= Q1_headway - 3 * IQR_headway)
    & (df["headway"] <= Q3_headway + 3 * IQR_headway)
    & (df["deviation"] >= Q1_deviation - 3 * IQR_deviation)
    & (df["deviation"] <= Q3_deviation + 3 * IQR_deviation)
]

df_filtered = df_filtered[df_filtered["headway"] > 1]

# %%
import plotly.express as px
# import plotly.io as pio

# pio.templates.default = "simple_white"

# Create a separate DataFrame for each station
df_division_sb = df_filtered.query("station == 'Division SB'")
df_grand_nb = df_filtered.query("station == 'Grand NB'")

# %%
from pathlib import Path

# Set the output directory
OUTPUT_DIRECTORY = Path(
    "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"
)

# Calculate CV and mean for each season at Division SB station
cv_division_sb = (
    df_division_sb.groupby("season")["headway"].std()
    / df_division_sb.groupby("season")["headway"].mean()
)
mean_division_sb = df_division_sb.groupby("season")["headway"].mean()

# Create a figure for Division SB station
fig_division_sb = px.histogram(
    df_division_sb,
    x="headway",
    color="season",
    marginal="box",
    opacity=0.7,
    barmode="group",
    histnorm="percent",
    title="Headway Distribution at Division SB (7:00 AM - 8:00 AM)",
    hover_data=df_division_sb.columns,
    category_orders={"season": ["Spring 2024", "Winter 2023"]},
)

# Add annotations for CV and mean for each season at Division SB station
for season, cv, mean in zip(
    cv_division_sb.index, cv_division_sb.values, mean_division_sb.values
):
    fig_division_sb.add_annotation(
        x=1.3,
        y=0.75 - cv_division_sb.index.tolist().index(season) * 0.2,
        xref="paper",
        yref="paper",
        text=f"{season}<br>CV: {cv:.2f}<br>Mean: {mean:.2f}",
        showarrow=False,
        align="right",
        font=dict(size=12),
        bgcolor="rgba(255, 255, 255, 0.8)",
    )

fig_division_sb.update_layout(
    xaxis_title="Headway (minutes)",
    yaxis_title="Percent",
    legend_title="Period",
    boxmode="group",
    width=600,
    height=600,
)

# Save the figure for Division SB station
fig_division_sb.write_image(
    str(OUTPUT_DIRECTORY / "Division_SB_Headway_Distribution.svg"),
    width=600,
    height=600,
    scale=2,
)

# Calculate CV and mean for each season at Grand NB station
cv_grand_nb = (
    df_grand_nb.groupby("season")["headway"].std()
    / df_grand_nb.groupby("season")["headway"].mean()
)
mean_grand_nb = df_grand_nb.groupby("season")["headway"].mean()

# Create a figure for Grand NB station
fig_grand_nb = px.histogram(
    df_grand_nb,
    x="headway",
    color="season",
    marginal="box",
    opacity=0.7,
    barmode="group",
    histnorm="percent",
    title="Headway Distribution at Grand NB (16:00 PM - 17:00 PM)",
    hover_data=df_grand_nb.columns,
    category_orders={"season": ["Spring 2024", "Winter 2023"]},
)

# Add annotations for CV and mean for each season at Grand NB station
for season, cv, mean in zip(
    cv_grand_nb.index, cv_grand_nb.values, mean_grand_nb.values
):
    fig_grand_nb.add_annotation(
        x=1.3,
        y=0.75 - cv_grand_nb.index.tolist().index(season) * 0.2,
        xref="paper",
        yref="paper",
        text=f"{season}<br>CV: {cv:.2f}<br>Mean: {mean:.2f}",
        showarrow=False,
        align="right",
        font=dict(size=12),
        bgcolor="rgba(255, 255, 255, 0.8)",
    )

fig_grand_nb.update_layout(
    xaxis_title="Headway (minutes)",
    yaxis_title="Percent",
    legend_title="Period",
    boxmode="group",
    width=600,
    height=600,
)

# Save the figure for Grand NB station
fig_grand_nb.write_image(
    str(OUTPUT_DIRECTORY / "Grand_NB_Headway_Distribution.svg"),
    width=600,
    height=600,
    scale=2,
)

fig_division_sb.show(renderer="browser")
fig_grand_nb.show(renderer="browser")
# %%
