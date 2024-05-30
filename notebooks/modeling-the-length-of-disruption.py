# %%
import re
import pandas as pd
import plotly.express as px

from mit_rail_sim.utils.db_con import engine, text

import plotly.io as pio

OUTPUT_DIRECTORY = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"

pio.templates.default = "simple_white"

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
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND run_id LIKE 'B%'
),
Blocking_Times AS (
    SELECT
        a.run_id,
        a.arrival_time_at_uic_halsted_nb,
        MAX(CASE WHEN t.scada = 'wd013t' THEN t.event_time END) - MAX(CASE WHEN t.scada = 'wd008t' THEN t.event_time END) AS blocking_time
    FROM
        NB_Arrivals a
        LEFT JOIN avas_spectrum.qt2_trainevent t ON a.run_id = t.run_id
            AND t.scada IN ('wd013t', 'wd008t')
            AND t.event_time <= a.arrival_time_at_uic_halsted_nb
            AND t.event_time >= a.arrival_time_at_uic_halsted_nb - INTERVAL '1 hour'
    GROUP BY
        a.run_id, a.arrival_time_at_uic_halsted_nb
),
Headways AS (
    SELECT
        run_id,
        event_time AS arrival_time_at_station,
        scada,
        headway
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada IN ('nwd739t', 'nwd612t', 'nwd555t', 'nwd475t', 'nwd327t', 'nwd270t', 'nwd217t', 'nwd184t', 'nwd146t', 'nwd111t', 'ln2306t', 'ln2269t', 'ln2236t', 'dd210t', 'dd169t', 'dd143t', 'dd092t', 'dd075t', 'dd066t', 'dd058t', 'dd038t', 'dd014t', 'wd008t')
        AND event_time::date BETWEEN :start_date AND :end_date
)
SELECT
    NB.run_id,
    NB.deviation,
    NB.arrival_time_at_uic_halsted_nb,
    NB.previous_arrival_time,
    NB.next_arrival_time,
    NB.arrival_time_at_uic_halsted_nb - NB.previous_arrival_time AS backward_headway,
    NB.next_arrival_time - NB.arrival_time_at_uic_halsted_nb AS forward_headway,
    SB.event_time AS departure_time_at_uic_halsted_sb,
    BT.blocking_time
FROM
    NB_Arrivals AS NB
JOIN
    avas_spectrum.qt2_trainevent AS SB
ON
    NB.run_id = SB.run_id
    AND SB.scada = 'wd005t' -- UIC-Halsted SB Departure
    AND SB.event_time BETWEEN NB.arrival_time_at_uic_halsted_nb - INTERVAL '45 MINUTES' AND NB.arrival_time_at_uic_halsted_nb
JOIN
    Blocking_Times AS BT
ON
    NB.run_id = BT.run_id
    AND BT.arrival_time_at_uic_halsted_nb BETWEEN NB.arrival_time_at_uic_halsted_nb - INTERVAL '5 MINUTES' AND NB.arrival_time_at_uic_halsted_nb + INTERVAL '5 MINUTES'
ORDER BY
    NB.arrival_time_at_uic_halsted_nb, NB.run_id;
"""
)

results = engine.execute(
    query_text, {"start_date": "2024-04-07", "end_date": "2024-05-30"}
)

df = pd.DataFrame(results.fetchall(), columns=results.keys())

import numpy as np


# %%
results = engine.execute(
    query_text, {"start_date": "2023-12-01", "end_date": "2024-02-07"}
)
old_df = pd.DataFrame(results.fetchall(), columns=results.keys())
# %%
# %%
df["blocking_time_minutes"] = df["blocking_time"].dt.total_seconds() / 60
old_df["blocking_time_minutes"] = old_df["blocking_time"].dt.total_seconds() / 60


df["blocking_time_minutes"] = df["blocking_time"].dt.total_seconds() / 60
old_df["blocking_time_minutes"] = old_df["blocking_time"].dt.total_seconds() / 60

# Determine AM/PM based on arrival_time_at_uic_halsted_nb
df["period"] = pd.to_datetime(df["arrival_time_at_uic_halsted_nb"]).dt.strftime("%p")
old_df["period"] = pd.to_datetime(old_df["arrival_time_at_uic_halsted_nb"]).dt.strftime(
    "%p"
)

# Combine the datasets
combined_df = pd.concat(
    [df.assign(dataset="Spring 2024"), old_df.assign(dataset="Winter 2023")]
)

# Remove rows with negative
combined_df = combined_df[combined_df["blocking_time_minutes"] >= 0]

combined_df = combined_df[combined_df["blocking_time_minutes"] > 1]

# %%
# Create separate plots for AM and PM
for period in ["AM", "PM"]:
    fig = px.histogram(
        combined_df[combined_df["period"] == period],
        x="blocking_time_minutes",
        color="dataset",
        histnorm="percent",
        barmode="group",
        marginal="box",
        hover_data=["run_id", "arrival_time_at_uic_halsted_nb", "deviation"],
        title=f"Distribution of Inspection Times at UIC-Halsted ({period})",
        labels={
            "blocking_time_minutes": "Inspection Time (minutes)",
            "dataset": "Period",
        },
    )

    fig.update_xaxes(title_text="Inspection Time (minutes)")
    fig.update_yaxes(title_text="Percentage")

    fig.update_layout({"autosize": True, "width": 800, "height": 600})

    for i, dataset in enumerate(combined_df["dataset"].unique()):
        stats = combined_df[
            (combined_df["period"] == period) & (combined_df["dataset"] == dataset)
        ]["blocking_time_minutes"].describe()
        fig.add_annotation(
            x=1.25,
            y=0.75 - i * 0.6,
            xref="paper",
            yref="paper",
            text=f"{dataset}<br>"
            f"Min: {stats['min']:.2f}<br>"
            f"Q1: {stats['25%']:.2f}<br>"
            f"Median: {stats['50%']:.2f}<br>"
            f"Q3: {stats['75%']:.2f}<br>"
            f"Max: {stats['max']:.2f}",
            showarrow=False,
            align="right",
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            bgcolor="white",
            opacity=0.8,
            font=dict(size=14),
        )

    fig.show(renderer="browser")

    fig.write_image(
        f"{OUTPUT_DIRECTORY}/inspection_times_uic_halsted_{period.lower()}.svg"
    )


# %%
