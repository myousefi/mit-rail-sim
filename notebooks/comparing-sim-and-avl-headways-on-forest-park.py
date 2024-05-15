# %%
import pandas as pd
import plotly.express as px
import plotly.io as pio

from mit_rail_sim.utils import project_root

pio.templates.default = "simple_white"

from mit_rail_sim.utils.db_con import engine, text

query_text = text(
    """
    SELECT
        run_id,
        deviation,
        headway,
        event_time AS departure_time_from_harlem
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        scada = 'wc437t' -- Leaving Harlem NB
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN  1 AND 5
        AND event_time::time BETWEEN '15:30' AND '18:00'
        AND run_id LIKE 'B%'
"""
)

results = engine.execute(query_text, params={"start_date": "2024-01-01", "end_date": "2024-03-01"})
df = pd.DataFrame(results.fetchall())

# %%
import glob

# Read all block_test.csv files and concatenate them into one DataFrame
path = project_root / "holding-experiments" / "experiments" / "*"
all_files = glob.glob(path + "block_test.csv")

df_list = []
for filename in all_files:
    df_temp = pd.read_csv(filename)
    df_list.append(df_temp)

df_concatenated = (
    pd.concat(df_list, ignore_index=True).query("block_id == 'wc437t'")[["headway"]] / 60
)


# %%

import plotly.express as px

df_concatenated["source"] = "Simulated"
df["source"] = "AVL"

df_combined = pd.concat([df_concatenated[["headway", "source"]], df[["headway", "source"]]])

fig = px.histogram(
    df_combined,
    x="headway",
    color="source",
    histnorm="probability",
    barmode="group",
    marginal="box",
    title="Headway Distribution: Simulated vs AVL",
    labels={"headway": "Headway (minutes)", "source": "Source"},
)

fig.update_layout(
    # xaxis=dict(title="Headway (minutes)", tickmode="linear", tick0=0, dtick=1),
    yaxis=dict(title="Probability"),
    bargap=0.1,
    bargroupgap=0.2,
)

# fig.update_traces(marker_line_width=1, marker_line_color="white", opacity=0.75)

fig.write_html(
    "/Users/moji/Presentations/One-on-One Meetings/03-13-2023/headway_distribution_simulated_vs_avl.html"
)

fig.show()
