# %%
import pandas as pd


from transit_lab_simmetro.utils.db_con import engine, text

STATION_BLOCK_SB = {
    "O-Hare": "nwd720t",
    "Rosemont": "nwd612t",
    "Cumberland": "nwd555t",
    "Harlem (O-Hare Branch)": "nwd475t",
    "Jefferson Park": "nwd327t",
    "Montrose": "nwd270t",
    "Irving Park": "nwd217t",
    "Addison": "nwd184t",
    "Belmont": "nwd146t",
    "Logan Square": "nwd111t",
    "California": "ln2306t",
    "Western (O-Hare Branch)": "ln2269t",
    "Damen": "ln2236t",
    "Division": "dd210t",
    "Chicago": "dd169t",
    "Grand": "dd143t",
    "Clark/Lake": "dd092t",
    "Washington": "dd075t",
    "Monroe": "dd066t",
    "Jackson": "dd058t",
    "LaSalle": "dd038t",
    "Clinton": "dd014t",
    "UIC-Halsted": "wd008t",
    "Racine": "wd035t",
    "Illinois Medical District": "wd069t",
    "Western (Forest Park Branch)": "wd111t",
    "Kedzie-Homan": "wd166t",
    "Pulaski": "wd219t",
    "Cicero": "wd273t",
    "Austin": "wd355t",
    "Oak Park": "wd395t",
    "Harlem (Forest Park Branch)": "wd439t",
    "Forest Park": "wd452t",
}
STATION_BLOCK_NB = {
    "Forest Park": "wc461t",
    "Harlem (Forest Park Branch)": "wc444t",
    "Oak Park": "wc401t",
    "Austin": "wc361t",
    "Cicero": "wc279t",
    "Pulaski": "wc225t",
    "Kedzie-Homan": "wc172t",
    "Western (Forest Park Branch)": "wc117t",
    "Illinois Medical District": "wc075t",
    "Racine": "wc035t",
    "UIC-Halsted": "wc008t",
    "Clinton": "dc014t",
    "LaSalle": "dc036t",
    "Jackson": "dc056t",
    "Monroe": "dc066t",
    "Washington": "dc075t",
    "Clark/Lake": "dc088t",
    "Grand": "dc138t",
    "Chicago": "dc164t",
    "Division": "dc210t",
    "Damen": "ln1232t",
    "Western (O-Hare Branch)": "ln1269t",
    "California": "ln1301t",
    "Logan Square": "nwc110t",
    "Belmont": "nwc146t",
    "Addison": "nwc185t",
    "Irving Park": "nwc218t",
    "Montrose": "nwc270t",
    "Jefferson Park": "nwc325t",
    "Harlem (O-Hare Branch)": "nwc468t",
    "Cumberland": "nwc547t",
    "Rosemont": "nwc606t",
    "O-Hare": "nwc724t",
}


# %%

date_start = "2024-04-07"
date_end = "2024-05-07"
time_start = 6
time_end = 9
day_start = 1
day_end = 5
max_run_time_minutes = 45


# SQL Query Template
query_template = text(
    """
WITH Filtered_Trainevents AS (
    SELECT
        run_id,
        event_time,
        scada
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        EXTRACT(HOUR FROM event_time) BETWEEN :time_start AND :time_end
        AND EXTRACT(DOW FROM event_time) BETWEEN :day_start AND :day_end
        AND event_time BETWEEN :date_start AND :date_end
),
Combined_Activations AS (
    SELECT
        s1.run_id,
        s1.event_time AS time_scada_1,
        s2.event_time AS time_scada_2,
        EXTRACT(EPOCH FROM (s2.event_time - s1.event_time)) AS run_time
    FROM
        Filtered_Trainevents s1
    JOIN
        Filtered_Trainevents s2 ON s1.run_id = s2.run_id
    WHERE
        s1.scada = :block
        AND s2.scada = :next_block
        AND s1.run_id LIKE 'B%'
        AND ABS(EXTRACT(EPOCH FROM (s2.event_time - s1.event_time))) / 60 < :max_run_time
)
SELECT
    :station as station,
    run_id,
    time_scada_1,
    time_scada_2,
    run_time
FROM
    Combined_Activations
"""
)

# Fetch and concatenate data
results_nb = []
for (station, block), (_, next_block) in zip(
    list(STATION_BLOCK_NB.items()), list(STATION_BLOCK_NB.items())[1:]
):
    with engine.connect() as conn:
        result = conn.execute(
            query_template,
            {
                "station": station,
                "block": block,
                "next_block": next_block,
                "date_start": date_start,
                "date_end": date_end,
                "time_start": time_start,
                "time_end": time_end,
                "day_start": day_start,
                "day_end": day_end,
                "max_run_time": max_run_time_minutes,
            },
        )
        results_nb.append(pd.DataFrame(result.fetchall(), columns=result.keys()))

results_sb = []
for (station, block), (_, next_block) in zip(
    list(STATION_BLOCK_SB.items()), list(STATION_BLOCK_SB.items())[1:]
):
    with engine.connect() as conn:
        result = conn.execute(
            query_template,
            {
                "station": station,
                "block": block,
                "next_block": next_block,
                "date_start": date_start,
                "date_end": date_end,
                "time_start": time_start,
                "time_end": time_end,
                "day_start": day_start,
                "day_end": day_end,
                "max_run_time": max_run_time_minutes,
            },
        )
        results_sb.append(pd.DataFrame(result.fetchall(), columns=result.keys()))

# TODO find a better way to save these
df_nb = pd.concat(results_nb)
print(df_nb)

df_sb = pd.concat(results_sb)
print(df_sb)

# %%
df_sb.to_csv("data/df_sb.csv", index=False)
df_nb.to_csv("data/df_nb.csv", index=False)

# %%)
