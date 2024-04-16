from mit_rail_sim.utils import project_root
# %%
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from mit_rail_sim.utils.db_con import engine, text

pio.templates.default = "simple_white"

pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 500)

start_date = "2023-11-13"
end_date = "2023-12-13"
# %%
df = pd.read_csv(project_root / "inputs" / "ohare-dispatch-info.csv")

df["event_time"] = df["time"]

# Get the list of run_ids from the DataFrame
run_ids = df["runid"].str.replace("R", "B").unique().tolist()

# Convert the list of run_ids to a string with comma-separated values
run_ids_str = ", ".join(f"'{run_id}'" for run_id in run_ids)

# Write the SQL query
query = text(
    f"""
    SELECT
        run_id, scada, deviation, headway, event_time
    FROM
        avas_spectrum.qt2_trainevent
    WHERE
        run_id IN ({run_ids_str})
        AND scada = 'nwd720t'
        AND EXTRACT(DOW from event_time) BETWEEN 1 AND 5
        AND event_time::date BETWEEN :start_date AND :end_date
    """
)

# Execute the query
result = engine.execute(query, start_date=start_date, end_date=end_date)

# Fetch all the rows from the result
rows = result.fetchall()

# Convert the result to a pandas DataFrame
headways_df = pd.DataFrame(rows, columns=result.keys())

# %%

# Filter the DataFrame based on time of day between 14 to 19
headways_df = headways_df[headways_df["event_time"].dt.hour.between(15, 19)]

df["run_id"] = df["runid"].str.replace("R", "B")

# Convert the time in df to datetime format
df["time"] = pd.to_datetime(df["event_time"])
df["time"] = df["time"] - df["time"].dt.normalize()

headways_df["time"] = headways_df["event_time"] - headways_df["event_time"].dt.normalize()

# Sort the DataFrames by 'event_time' for merge_asof
headways_df = headways_df.sort_values("time")
df = df.sort_values("time")

# Perform the label matching using merge_asof
merged_df = pd.merge_asof(headways_df, df, on="time", by="run_id", direction="nearest")

# ...

# %%
import matplotlib.pyplot as plt

# Filter the DataFrame for hdw == 5
hdw_5_df = merged_df[merged_df["hdw"] == 5]

# Filter the DataFrame for hdw == 10
hdw_10_df = merged_df[merged_df["hdw"] == 10]

# Plot the histogram for hdw == 5
plt.hist(hdw_5_df["headway"], bins=30, alpha=0.5, label="hdw == 5")

# Plot the histogram for hdw == 10
plt.hist(hdw_10_df["headway"], bins=30, alpha=0.5, label="hdw == 10")

plt.xlabel("Headway")
plt.ylabel("Frequency")
plt.title("Distribution of Headway for hdw == 5 and hdw == 10")
plt.legend()

plt.show()

# %%

import json

import numpy as np
import scipy.stats as stats

# Filter the DataFrame for hdw == 5
hdw_5_df = merged_df[merged_df["hdw"] == 5]

# Filter the DataFrame for hdw == 10
hdw_10_df = merged_df[merged_df["hdw"] == 10]

# Fit gamma distributions to hdw == 5 and hdw == 10 data
shape_5, loc_5, scale_5 = stats.gamma.fit(hdw_5_df["headway"])
shape_10, loc_10, scale_10 = stats.gamma.fit(hdw_10_df["headway"])

# Save the parameters to a file
parameters = {
    "hdw_5": {"shape": shape_5, "loc": loc_5, "scale": scale_5},
    "hdw_10": {"shape": shape_10, "loc": loc_10, "scale": scale_10},
}

# Convert the parameters dictionary to JSON format
parameters_json = json.dumps(parameters)

# Specify the file path for saving the JSON file
json_file_path = project_root / "inputs" / "pm_peak_gamma_parameters.json"

# Save the parameters to the JSON file
with open(json_file_path, "w") as json_file:
    json_file.write(parameters_json)


# ...

# %%
