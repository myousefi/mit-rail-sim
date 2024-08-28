# %%
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


pio.templates.default = "simple_white"

# %%
# Read the station file
station_file_path = "/Users/moji/Projects/mit_rail_sim/cta-2024/outputs/2024-05-06/05-48-07/station_test.csv"
df = pd.read_csv(station_file_path)

# Filter the data for Harlem (Forest Park) station
harlem_data_sim = df[df["station_name"] == "Harlem (Forest Park Branch)"]

harlem_data_sim["headway"] = harlem_data_sim["headway"] / 60

# %%
# Create a histogram of headways at Harlem (Forest Park)
fig = go.Figure()

fig.add_trace(
    go.Histogram(
        x=harlem_data_sim["headway"],
        histnorm="percent",
        nbinsx=50,
        name="Harlem (Forest Park Branch) - Simulation",
        marker=dict(color="blue"),
    )
)

fig.update_layout(
    title_text="Histogram of Headways at Harlem (Forest Park Branch)",
    xaxis_title="Headway (minutes)",
    yaxis_title="Percent",
    bargap=0.1,
    bargroupgap=0.2,
    legend=dict(
        x=1,
        y=1,
        xanchor="auto",
        yanchor="auto",
        orientation="h",
        bgcolor="rgba(0,0,0,0)",
        bordercolor="Black",
        borderwidth=2,
    ),
)

# %%

from transit_lab_simmetro.utils.db_con import text, engine

# Query to fetch headway data for Harlem (Forest Park Branch)
query_text = text(
    """
    SELECT headway
    FROM avas_spectrum.qt2_trainevent
    WHERE
        scada = 'wc437t' -- Leaving Harlem NB
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND event_time::time BETWEEN '15:30' AND '18:00'
        AND run_id LIKE 'B%'
    """
)

result = engine.execute(query_text, start_date="2024-04-07", end_date="2024-05-15")
harlem_data_avl = pd.DataFrame(result.fetchall(), columns=result.keys())

# %%

# Add a new trace for harlem_data_avl
fig.add_trace(
    go.Histogram(
        x=harlem_data_avl["headway"],
        histnorm="percent",
        nbinsx=50,
        name="Harlem (Forest Park Branch) - AVL",
        marker=dict(color="red"),
    )
)

fig.show(renderer="browser")
# %%
