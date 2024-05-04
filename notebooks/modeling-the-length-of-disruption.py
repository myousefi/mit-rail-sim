# %%
import pandas as pd
import plotly.express as px

from mit_rail_sim.utils.db_con import engine, text

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
    query_text, {"start_date": "2024-04-07", "end_date": "2024-05-01"}
)

df = pd.DataFrame(results.fetchall(), columns=results.keys())

import numpy as np


# %%
results = engine.execute(
    query_text, {"start_date": "2023-12-01", "end_date": "2023-12-30"}
)
old_df = pd.DataFrame(results.fetchall(), columns=results.keys())
# %%
# %%
import plotly.graph_objects as go

fig = go.Figure()

# Plot the new data (df)
fig.add_trace(
    go.Histogram(
        x=df["blocking_time"].dt.total_seconds() / 60,
        histnorm="percent",
        name="2023-12-01 to 2023-12-29",
        opacity=0.75,
    )
)

# Plot the old data (old_df)
fig.add_trace(
    go.Histogram(
        x=old_df["blocking_time"].dt.total_seconds() / 60,
        histnorm="percent",
        name="2024-04-07 to 2024-05-01",
        opacity=0.75,
    )
)

fig.update_layout(
    title_text="Distribution of Inspection Times at UIC-Halsted",
    xaxis_title_text="Inspection Time (minutes)",
    yaxis_title_text="Percentage",
    bargap=0.1,
    bargroupgap=0.1,
)

fig.show(renderer="browser")

# %%
df["period"] = np.where(df["arrival_time_at_uic_halsted_nb"].dt.hour < 12, "AM", "PM")
old_df["period"] = np.where(
    old_df["arrival_time_at_uic_halsted_nb"].dt.hour < 12, "AM", "PM"
)

fig = go.Figure()

# Plot the new data (df) for PM period
fig.add_trace(
    go.Histogram(
        x=df[df["period"] == "PM"]["blocking_time"].dt.total_seconds() / 60,
        histnorm="percent",
        name="2023-12-01 to 2023-12-29 (PM)",
        opacity=0.75,
    )
)
# Plot the new data (df) for AM period
fig.add_trace(
    go.Histogram(
        x=df[df["period"] == "AM"]["blocking_time"].dt.total_seconds() / 60,
        histnorm="percent",
        name="2023-12-01 to 2023-12-29 (AM)",
        opacity=0.75,
    )
)

# Plot the old data (old_df) for AM period
fig.add_trace(
    go.Histogram(
        x=old_df[old_df["period"] == "AM"]["blocking_time"].dt.total_seconds() / 60,
        histnorm="percent",
        name="2024-04-07 to 2024-05-01 (AM)",
        opacity=0.75,
    )
)

# Plot the old data (old_df) for PM period
fig.add_trace(
    go.Histogram(
        x=old_df[old_df["period"] == "PM"]["blocking_time"].dt.total_seconds() / 60,
        histnorm="percent",
        name="2024-04-07 to 2024-05-01 (PM)",
        opacity=0.75,
    )
)

fig.update_layout(
    title_text="Distribution of Inspection Times at UIC-Halsted by AM/PM",
    xaxis_title_text="Inspection Time (minutes)",
    yaxis_title_text="Percentage",
    bargap=0.1,
    bargroupgap=0.1,
)

fig.show(renderer="browser")

# %%
