# %%
# %%
import pandas as pd
import plotly.graph_objects as go

from mit_rail_sim.utils.station_block_constants import (
    NORTHBOUND_DEPARTING_BLOCKS,
    SOUTHBOUND_DEPARTING_BLOCKS,
)
from mit_rail_sim.utils.db_con import engine, text

OUTPUT_DIRECTORY = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"

# Extract the block names from the station block constants
southbound_blocks = [block for _, block in SOUTHBOUND_DEPARTING_BLOCKS]
northbound_blocks = [block for _, block in NORTHBOUND_DEPARTING_BLOCKS]

query = text(
    """
    WITH filtered_events AS (
        SELECT
            scada,
            event_time,
            run_id,
            deviation,
            headway,
            CASE
                WHEN scada IN :southbound_blocks THEN 'Southbound'
                WHEN scada IN :northbound_blocks THEN 'Northbound'
            END AS direction,
            CASE
                WHEN event_time >= '2024-04-07' AND event_time < '2024-05-20' THEN 'Spring 2024'
            END AS season
        FROM
            avas_spectrum.qt2_trainevent
        WHERE
            (
                (scada IN :southbound_blocks AND EXTRACT(HOUR FROM event_time) BETWEEN 7 AND 8)
                OR
                (scada IN :northbound_blocks AND EXTRACT(HOUR FROM event_time) BETWEEN 16 AND 17)
            )
            AND event_time >= '2024-04-07' AND event_time < '2024-05-20'
    )
    SELECT
        *,
        CASE
            WHEN EXTRACT(HOUR FROM event_time) BETWEEN 8 AND 9 THEN 'AM Peak'
            WHEN EXTRACT(HOUR FROM event_time) BETWEEN 16 AND 18 THEN 'PM Peak'
        END AS peak_period
    FROM
        filtered_events
    WHERE
        EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5  -- Filter weekdays (Monday to Friday)
    ORDER BY
        event_time
    """
)

with engine.connect() as connection:
    result = connection.execute(
        query,
        southbound_blocks=tuple(southbound_blocks),
        northbound_blocks=tuple(northbound_blocks),
    )
    rows = result.fetchall()

df = pd.DataFrame(rows, columns=result.keys())

df["station_name"] = df["scada"].map(
    dict(
        (block, station)
        for station, block in SOUTHBOUND_DEPARTING_BLOCKS + NORTHBOUND_DEPARTING_BLOCKS
    )
)

# Convert data types
df["deviation"] = pd.to_numeric(df["deviation"], errors="coerce")
df["headway"] = pd.to_numeric(df["headway"], errors="coerce")
df["event_time"] = pd.to_datetime(df["event_time"])
df["station_name"] = df["station_name"].astype("object")
# %%
# Filter out outliers in headway based on 3 IQR
q1 = df["headway"].quantile(0.25)
q3 = df["headway"].quantile(0.75)
iqr = q3 - q1
lower_bound = max(q1 - (3 * iqr), 0)
upper_bound = q3 + (3 * iqr)
print(f"Headway outlier bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")

df = df[(df["headway"] >= lower_bound) & (df["headway"] <= upper_bound)]

# %%

import pandas as pd

STATION_ORDER_NORTH = [
    "O-Hare",
    "Rosemont",
    "Cumberland",
    "Harlem (O-Hare Branch)",
    "Jefferson Park",
    "Montrose",
    "Irving Park",
    "Addison",
    "Belmont",
    "Logan Square",
    "California",
    "Western (O-Hare Branch)",
    "Damen",
    "Division",
    "Chicago",
    "Grand",
    "Clark/Lake",
    "Washington",
    "Monroe",
    "Jackson",
    "LaSalle",
    "Clinton",
    "UIC-Halsted",
    "Racine",
    "Illinois Medical District",
    "Western (Forest Park Branch)",
    "Kedzie-Homan",
    "Pulaski",
    "Cicero",
    "Austin",
    "Oak Park",
    "Harlem (Forest Park Branch)",
    "Forest Park",
]

STATION_ORDER_SOUTH = STATION_ORDER_NORTH[::-1]

df["station_name"] = pd.Categorical(
    df["station_name"], categories=STATION_ORDER_SOUTH, ordered=True
)


# %%
def calculate_cv(group):
    return group.std() / group.mean() * 100


for direction in ["Northbound", "Southbound"]:
    query = "season == 'Spring 2024' & " "direction == @direction"
    filtered_df = df.query(query)

    cv_by_station = filtered_df.groupby("station_name")["headway"].apply(calculate_cv)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=cv_by_station.index,
                y=cv_by_station,
                mode="lines+markers+text",
                text=[f"{x:.1f}" for x in cv_by_station],
                textposition="top center",
                textfont=dict(size=12),
                line=dict(width=1, dash="dash"),
                marker=dict(size=14, color="red"),
            )
        ],
        layout=go.Layout(
            title=dict(
                text=f"Coefficient of Variation of Headways - {direction}, {'AM' if direction == 'Southbound' else 'PM'} Peak (Spring 2024)",
                font=dict(size=24),
            ),
            yaxis_title=dict(text="Coefficient of Variation (%)", font=dict(size=18)),
            yaxis=dict(
                tickfont=dict(size=14),
                ticksuffix="%",
                gridwidth=5,
                gridcolor="black",
                dtick=5,
                range=[30, 65],
            ),
            xaxis=dict(tickfont=dict(size=14), tickangle=45),
        ),
    )

    fig.show(renderer="browser")

    fig.update_yaxes(range=[30, 65], fixedrange=True, automargin=False)

    fig.write_image(
        str(OUTPUT_DIRECTORY + f"CV_Headways_{direction}_Peak_Spring_2024.svg"),
        width=1600,
        height=600,
        scale=1,
    )

# %%
# %%
import pandas as pd
import plotly.graph_objects as go

from mit_rail_sim.utils.station_block_constants import (
    NORTHBOUND_DEPARTING_BLOCKS,
    SOUTHBOUND_DEPARTING_BLOCKS,
)
from mit_rail_sim.utils.db_con import engine, text

OUTPUT_DIRECTORY = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"

# Extract the block names from the station block constants
southbound_blocks = [block for _, block in SOUTHBOUND_DEPARTING_BLOCKS]
northbound_blocks = [block for _, block in NORTHBOUND_DEPARTING_BLOCKS]

query = text(
    """
    WITH filtered_events AS (
        SELECT
            scada,
            event_time,
            run_id,
            deviation,
            headway,
            CASE
                WHEN scada IN :southbound_blocks THEN 'Southbound'
                WHEN scada IN :northbound_blocks THEN 'Northbound'
            END AS direction,
            CASE
                WHEN event_time >= '2022-04-24' AND event_time < '2022-08-15' THEN 'Spring 2022'
            END AS season
        FROM
            avas_spectrum.qt2_trainevent
        WHERE
            (
                (scada IN :southbound_blocks AND EXTRACT(HOUR FROM event_time) BETWEEN 7 AND 8)
                OR
                (scada IN :northbound_blocks AND EXTRACT(HOUR FROM event_time) BETWEEN 16 AND 17)
            )
            AND event_time >= '2022-04-24' AND event_time < '2022-08-15'
    )
    SELECT
        *,
        CASE
            WHEN EXTRACT(HOUR FROM event_time) BETWEEN 8 AND 9 THEN 'AM Peak'
            WHEN EXTRACT(HOUR FROM event_time) BETWEEN 16 AND 18 THEN 'PM Peak'
        END AS peak_period
    FROM
        filtered_events
    WHERE
        EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5  -- Filter weekdays (Monday to Friday)
    ORDER BY
        event_time
    """
)

with engine.connect() as connection:
    result = connection.execute(
        query,
        southbound_blocks=tuple(southbound_blocks),
        northbound_blocks=tuple(northbound_blocks),
    )
    rows = result.fetchall()

df = pd.DataFrame(rows, columns=result.keys())

df["station_name"] = df["scada"].map(
    dict(
        (block, station)
        for station, block in SOUTHBOUND_DEPARTING_BLOCKS + NORTHBOUND_DEPARTING_BLOCKS
    )
)

# Convert data types
df["deviation"] = pd.to_numeric(df["deviation"], errors="coerce")
df["headway"] = pd.to_numeric(df["headway"], errors="coerce")
df["event_time"] = pd.to_datetime(df["event_time"])
df["station_name"] = df["station_name"].astype("object")

# %%
# Filter out outliers in headway based on 3 IQR
q1 = df["headway"].quantile(0.25)
q3 = df["headway"].quantile(0.75)
iqr = q3 - q1
lower_bound = max(q1 - (3 * iqr), 0)
upper_bound = q3 + (3 * iqr)
print(f"Headway outlier bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")

df = df[(df["headway"] >= lower_bound) & (df["headway"] <= upper_bound)]

# %%
STATION_ORDER_NORTH = [
    "O-Hare",
    "Rosemont",
    "Cumberland",
    "Harlem (O-Hare Branch)",
    "Jefferson Park",
    "Montrose",
    "Irving Park",
    "Addison",
    "Belmont",
    "Logan Square",
    "California",
    "Western (O-Hare Branch)",
    "Damen",
    "Division",
    "Chicago",
    "Grand",
    "Clark/Lake",
    "Washington",
    "Monroe",
    "Jackson",
    "LaSalle",
    "Clinton",
    "UIC-Halsted",
    "Racine",
    "Illinois Medical District",
    "Western (Forest Park Branch)",
    "Kedzie-Homan",
    "Pulaski",
    "Cicero",
    "Austin",
    "Oak Park",
    "Harlem (Forest Park Branch)",
    "Forest Park",
]

STATION_ORDER_SOUTH = STATION_ORDER_NORTH[::-1]

df["station_name"] = pd.Categorical(
    df["station_name"], categories=STATION_ORDER_SOUTH, ordered=True
)


# %%
def calculate_cv(group):
    return group.std() / group.mean() * 100


for direction in ["Southbound"]:
    query = (
        "season == 'Spring 2022' & direction == @direction & peak_period == 'AM Peak'"
    )
    filtered_df = df.query(query)

    cv_by_station = filtered_df.groupby("station_name")["headway"].apply(calculate_cv)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=cv_by_station.index,
                y=cv_by_station,
                mode="lines+markers+text",
                text=[f"{x:.1f}" for x in cv_by_station],
                textposition="top center",
                textfont=dict(size=12),
                line=dict(width=1, dash="dash"),
                marker=dict(size=14, color="red"),
            )
        ],
        layout=go.Layout(
            title=dict(
                text=f"Coefficient of Variation of Headways - {direction}, AM Peak (Spring 2022)",
                font=dict(size=24),
            ),
            yaxis_title=dict(text="Coefficient of Variation (%)", font=dict(size=18)),
            yaxis=dict(
                tickfont=dict(size=14),
                ticksuffix="%",
                gridwidth=5,
                gridcolor="black",
                dtick=5,
                range=[40, 75],
            ),
            xaxis=dict(tickfont=dict(size=14), tickangle=45),
        ),
    )

    fig.show(renderer="browser")

    fig.update_yaxes(range=[40, 75], fixedrange=True, automargin=False)

    fig.write_image(
        str(OUTPUT_DIRECTORY + f"CV_Headways_{direction}_AM_Peak_Spring_2022.svg"),
        width=1600,
        height=600,
        scale=1,
    )

# %%
