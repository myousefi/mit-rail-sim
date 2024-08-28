# %%
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from pandas.tseries.holiday import USFederalHolidayCalendar
from sqlalchemy import text

from transit_lab_simmetro.utils.db_con import engine
from transit_lab_simmetro.utils.root_path import project_root

pio.templates.default = "simple_white"


# %%
def load_data(start_date, end_date):
    # Load stations data
    station_df = pd.read_csv(
        project_root
        / "transit_lab_simmetro"
        / "cta-data-queries"
        / "odx_arrival"
        / "data"
        / "blue_line_stations.csv"
    )

    # Generate query text
    query_text = text(
        """
        SELECT transaction_dtm, boarding_stop, route_sequence, direction_sequence, boarding_platform_sequence, alighting_platform_sequence
        FROM planning_models_spectrum.odx_journeys
        WHERE
            boarding_stop IN :boarding_stops_list AND
            transaction_dtm BETWEEN :start_date AND :end_date
        """
    )
    # Execute the query and fetch the results
    result = engine.execute(
        query_text,
        boarding_stops_list=tuple(station_df["MAP_ID"].unique().tolist()),
        start_date=start_date,
        end_date=end_date,
    ).fetchall()

    # Convert the result to a DataFrame
    result_df = pd.DataFrame(
        result,
        columns=[
            "transaction_dtm",
            "boarding_stop",
            "route_sequence",
            "direction_sequence",
            "boarding_platform_sequence",
            "alighting_platform_sequence",
        ],
    )

    for col in [
        "route_sequence",
        "direction_sequence",
        "boarding_platform_sequence",
        "alighting_platform_sequence",
    ]:
        result_df["first_" + col.replace("_sequence", "")] = (
            result_df[col].str.split("|").str[1]
        )
        result_df.drop(columns=col, inplace=True)
    result_df["Origin"] = (
        result_df["boarding_stop"]
        .astype(str)
        .map(
            dict(
                zip(station_df["MAP_ID"].astype(str), station_df["STATION_NAME_IN_SIM"])
            )
        )
    )

    # Convert transaction_dtm to datetime, extract time component, and determine the day type
    result_df["transaction_dtm"] = pd.to_datetime(result_df["transaction_dtm"])

    result_df["time"] = result_df["transaction_dtm"].dt.hour
    result_df["day_type"] = result_df["transaction_dtm"].dt.dayofweek.apply(
        lambda x: "Weekday" if x < 5 else "Saturday" if x == 5 else "Sunday"
    )

    result_df.sort_values(["transaction_dtm"], inplace=True)

    # Define columns to fill
    fill_columns = [
        "first_route",
        "first_direction",
        "first_boarding_platform",
        "first_alighting_platform",
    ]

    # Function to impute missing data within each group
    def impute_within_group(group):
        non_nan_rows = group.dropna(subset=fill_columns)
        if non_nan_rows.empty:
            # If there are no rows to impute from, return the group as is
            return group

        # For rows with NaN in the current column, fill them with values from a randomly chosen row
        nan_rows = group[fill_columns].isna().any(axis=1)
        group.loc[nan_rows, fill_columns] = (
            non_nan_rows[fill_columns].sample(n=nan_rows.sum(), replace=True).values
        )

        return group

    # Apply the imputation function to each group
    result_df = (
        result_df.groupby(["boarding_stop", "time", "day_type"])
        .apply(impute_within_group)
        .reset_index(drop=True)
    )

    result_df["Destination"] = result_df["first_alighting_platform"].map(
        dict(zip(station_df["STOP_ID"].astype(str), station_df["STATION_NAME_IN_SIM"]))
    )

    # Extract hour and determine if the day is a weekday
    result_df["hour"] = (
        result_df["transaction_dtm"].dt.hour
        + result_df["transaction_dtm"].dt.minute / 60
    )
    result_df["hour"] = result_df["hour"].round(2)  # Round to 2 decimal places
    result_df["weekday"] = (result_df["transaction_dtm"].dt.weekday < 5) & (
        ~result_df["transaction_dtm"].dt.date.isin(
            USFederalHolidayCalendar().holidays()
        )
    )  # True for weekdays (Mon-Fri)

    return result_df


result_df = load_data("2024-04-07", "2024-05-31")
# %%


# %%
def calculate_load_flow(filtered_df, station_order):
    daily_cumulative_load_flow = (
        filtered_df.groupby(filtered_df["transaction_dtm"].dt.date)
        .apply(
            lambda day: (
                day.groupby("origin").size() - day.groupby("destination").size()
            ).cumsum()
        )
        .reindex(columns=station_order)
    )
    return daily_cumulative_load_flow


def generate_plot(daily_cumulative_load_flow, period_name, peak_name, direction):
    stats = daily_cumulative_load_flow.apply(
        lambda x: {
            "5_percentile": x.quantile(0.05),
            "median": x.median(),
            "95_percentile": x.quantile(0.95),
        }
    ).T
    fig = px.line(
        data_frame=stats,
        y=["median"],
        title=f"Daily Load Flow Statistics - {period_name} - {peak_name} - {direction}bound",
        labels={"value": "Cumulative Load Flow", "origin": "Station"},
        color_discrete_sequence=["blue"],
    )
    for percentile in ["95_percentile", "5_percentile"]:
        fig.add_trace(
            go.Scatter(
                x=stats.index,
                y=stats[percentile],
                mode="lines",
                line=dict(width=0),
                fillcolor="rgba(135, 206, 250, 0.4)",
                fill="tonexty",
                showlegend=True,
            )
        )
    fig.update_layout(
        showlegend=False, yaxis_title="Cumulative Load Flow", yaxis_range=[0, 4000]
    )
    return fig


# %%
time_periods = {
    "Spring 2024 Pick": {"start_date": "2024-04-07", "end_date": "2024-05-31"},
    "Fall 2023 Pick": {"start_date": "2023-10-08", "end_date": "2024-04-06"},
}
peak_periods = {
    "AM Peak": {"start_time": 6, "end_time": 9},
    "PM Peak": {"start_time": 15, "end_time": 18},
}
for period_name, period_dates in time_periods.items():
    start_date = period_dates["start_date"]
    end_date = period_dates["end_date"]
    result_df, station_df = load_data(start_date, end_date)
    result_df, blue_line_stations = preprocess_data(result_df, station_df)
    station_order_north = blue_line_stations[blue_line_stations["dir_id"] == "North"][
        "STATION_NAME_IN_SIM"
    ].tolist()
    station_order_south = list(reversed(station_order_north))
    for peak_name, peak_times in peak_periods.items():
        for direction, station_order in [
            ("North", station_order_north),
            ("South", station_order_south),
        ]:
            filtered_df = result_df[
                (result_df["weekday"] == True)
                & (result_df["hour"] >= peak_times["start_time"])
                & (result_df["hour"] < peak_times["end_time"])
                & (result_df["first_direction"] == direction)
            ]
            daily_cumulative_load_flow = calculate_load_flow(filtered_df, station_order)
            fig = generate_plot(
                daily_cumulative_load_flow, period_name, peak_name, direction
            )
            fig.show(renderer="browser")

print("Load flow comparison plots generated.")
# %%
