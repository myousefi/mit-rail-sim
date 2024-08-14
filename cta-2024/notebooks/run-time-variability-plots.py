# %%
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

pio.templates.default = "simple_white"

STATION_ORDER = [
    "Forest Park",
    "Harlem (Forest Park Branch)",
    "Oak Park",
    "Austin",
    "Cicero",
    "Pulaski",
    "Kedzie-Homan",
    "Western (Forest Park Branch)",
    "Illinois Medical District",
    "Racine",
    "UIC-Halsted",
    "Clinton",
    "LaSalle",
    "Jackson",
    "Monroe",
    "Washington",
    "Clark/Lake",
    "Grand",
    "Chicago",
    "Division",
    "Damen",
    "Western (O-Hare Branch)",
    "California",
    "Logan Square",
    "Belmont",
    "Addison",
    "Irving Park",
    "Montrose",
    "Jefferson Park",
    "Harlem (O-Hare Branch)",
    "Cumberland",
    "Rosemont",
    "O-Hare",
]

df_nb = pd.read_csv("data/df_nb.csv")
df_sb = pd.read_csv("data/df_sb.csv")

# Add a "direction" column to each DataFrame
df_nb["direction"] = "Northbound"
df_sb["direction"] = "Southbound"

# Concatenate the two DataFrames
df = pd.concat([df_nb, df_sb])

# Convert run_time from seconds to minutes
df["run_time"] = df["run_time"] / 60

# Ensure the station names are ordered according to STATION_ORDER
df["station"] = pd.Categorical(df["station"], categories=STATION_ORDER, ordered=True)

# Sort the DataFrame based on the ordered station names
df = df.sort_values("station")


# Function to filter outliers using IQR method
def filter_outliers(group):
    q1 = group["run_time"].quantile(0.25)
    q3 = group["run_time"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return group[
        (group["run_time"] >= lower_bound) & (group["run_time"] <= upper_bound)
    ]


# %%
# Filter outliers for each station and direction
df = df.groupby(["station", "direction"], group_keys=False).apply(filter_outliers)

# Calculate COV for each station and direction
cov = (
    df.groupby(["station", "direction"])["run_time"].std()
    / df.groupby(["station", "direction"])["run_time"].mean()
) * 100
# %%
# Reset the index to convert the MultiIndex to columns
cov = cov.reset_index()
# %%
# Create a single plot with two traces for directions
fig = go.Figure()

for direction in cov["direction"].unique():
    cov_direction = cov[cov["direction"] == direction]
    fig.add_trace(
        go.Bar(
            x=cov_direction["station"],
            y=cov_direction["run_time"],
            # mode="lines+markers",
            name=direction,
        )
    )

fig.update_layout(
    title="Coefficient of Variation (COV) of Run Times",
    xaxis_title="Station",
    yaxis_title="COV",
    legend_title="Direction",
)

# Display the plot
fig.show(renderer="browser")

# %%
