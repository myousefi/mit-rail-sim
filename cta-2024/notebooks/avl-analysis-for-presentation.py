# %%
import pandas as pd
from sqlalchemy import text

from mit_rail_sim.utils.db_con import engine

OUTPUT_DIRECTORY = "/Users/moji/Library/CloudStorage/OneDrive-NortheasternUniversity/Presentations/CTA-Dry-Run-May-2024/artifacts/"

# Define the time periods
time_periods = {
    "Spring 2024": {"start_date": "2024-04-07", "end_date": "2024-05-31"},
    "Winter 2023": {"start_date": "2023-11-13", "end_date": "2024-02-07"},
    "Spring 2023": {"start_date": "2023-03-26", "end_date": "2023-07-23"},
}

# Query to get departures from Forest Park
departures_query = text("""
    SELECT run_id, event_time AS forest_park_departure_time
    FROM avas_spectrum.qt2_trainevent
    WHERE qt2_trackid = :forest_park_trackid
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND EXTRACT(HOUR FROM event_time) BETWEEN 5 AND 11
    ORDER by event_time ASC
""")

# Query to get arrivals at O'Hare
arrivals_query = text("""
    SELECT run_id, event_time AS ohare_arrival_time
    FROM avas_spectrum.qt2_trainevent
    WHERE qt2_trackid = :ohare_trackid
        AND event_time::date BETWEEN :start_date AND :end_date
        AND EXTRACT(DOW FROM event_time) BETWEEN 1 AND 5
        AND EXTRACT(HOUR FROM event_time) BETWEEN 5 AND 11
    ORDER by event_time ASC
""")

# Create a dictionary to store the results for each period and direction
results = {}

# Execute the queries for each time period and direction
for period, dates in time_periods.items():
    results[period] = {}
    for direction in ["Northbound", "Southbound"]:
        if direction == "Northbound":
            departures_result = engine.execute(
                departures_query,
                forest_park_trackid=11020,
                start_date=dates["start_date"],
                end_date=dates["end_date"],
            )
            arrivals_result = engine.execute(
                arrivals_query,
                ohare_trackid=11700,
                start_date=dates["start_date"],
                end_date=dates["end_date"],
            )
        else:
            departures_result = engine.execute(
                departures_query,
                forest_park_trackid=15700,
                start_date=dates["start_date"],
                end_date=dates["end_date"],
            )
            arrivals_result = engine.execute(
                arrivals_query,
                ohare_trackid=15020,
                start_date=dates["start_date"],
                end_date=dates["end_date"],
            )

        departures_df = pd.DataFrame(
            departures_result.fetchall(), columns=departures_result.keys()
        )
        arrivals_df = pd.DataFrame(
            arrivals_result.fetchall(), columns=arrivals_result.keys()
        )

        # Perform merge_asof to match departures with closest arrivals
        merged_df = pd.merge_asof(
            departures_df,
            arrivals_df,
            by="run_id",
            left_on="forest_park_departure_time",
            right_on="ohare_arrival_time",
            direction="forward" if direction == "Northbound" else "backward",
            tolerance=pd.Timedelta("2.5 hours"),
        )

        # Calculate run time in minutes
        merged_df["run_time"] = (
            abs(
                merged_df["ohare_arrival_time"]
                - merged_df["forest_park_departure_time"]
            )
        ).dt.total_seconds() / 60

        # Store the merged DataFrame in the results dictionary
        results[period][direction] = merged_df

# Print the results for each period and direction
for period, period_results in results.items():
    for direction, df in period_results.items():
        print(f"{direction} Run Times for {period}:")
        print(df.head())
        print("\n")

# %%
import plotly.express as px
import plotly.io as pio
import pandas as pd

pio.templates.default = "simple_white"

# Combine all DataFrames into a single DataFrame
combined_df = pd.concat(
    [df for period_results in results.values() for df in period_results.values()],
    keys=[
        f"{period} - {direction}"
        for period in results.keys()
        for direction in results[period].keys()
    ],
    names=["Period - Direction"],
).reset_index()

combined_df[["period", "direction"]] = combined_df["Period - Direction"].str.split(
    " - ", expand=True
)

combined_df.drop(columns=["Period - Direction", "level_1"], inplace=True)

combined_df = combined_df.reset_index(level=0)

combined_df.dropna(inplace=True)
# %%
# Calculate the IQR for run_time
Q1 = combined_df["run_time"].quantile(0.25)
Q3 = combined_df["run_time"].quantile(0.75)
IQR = Q3 - Q1

# Filter out outliers based on IQR
lower_bound = Q1 - 3 * IQR
upper_bound = Q3 + 3 * IQR
combined_df = combined_df[
    (combined_df["run_time"] >= lower_bound) & (combined_df["run_time"] <= upper_bound)
]
# %%
# Create separate plots for each direction
for direction in combined_df["direction"].unique():
    fig = px.histogram(
        combined_df[combined_df["direction"] == direction],
        x="run_time",
        color="period",
        histnorm="percent",
        barmode="group",
        marginal="box",
        nbins=50,
        hover_data=combined_df.columns,
        title=f"Distribution of Run Times ({direction})",
        labels={
            "run_time": "Run Time (minutes)",
            "dataset": "Period",
            "period": "Period",
        },
    )

    fig.update_xaxes(title_text="Run Time (minutes)")
    fig.update_yaxes(title_text="Percentage")

    fig.update_layout({"autosize": True, "width": 600, "height": 600})

    fig.show(renderer="browser")

    fig.write_image(f"{OUTPUT_DIRECTORY}/run_times_{direction.lower()}.svg")


# %%
