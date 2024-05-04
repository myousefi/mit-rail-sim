import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import Input, Output, callback, dcc, html
from sqlalchemy import create_engine, text

from mit_rail_sim.utils import find_free_port
from mit_rail_sim.utils.db_con import engine, text

pio.templates.default = "simple_white"

pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 500)


# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the layout
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Input(
                            id="version-input-1",
                            type="number",
                            value=81,
                        ),
                        dcc.Graph(id="plot-1-0"),
                        dcc.Graph(id="plot-1-1"),
                        dcc.Graph(id="plot-1-2"),
                    ]
                ),
                dbc.Col(
                    [
                        dcc.Input(
                            id="version-input-2",
                            type="number",
                            value=72,
                        ),
                        dcc.Graph(id="plot-2-0"),
                        dcc.Graph(id="plot-2-1"),
                        dcc.Graph(id="plot-2-2"),
                    ]
                ),
                dbc.Col(
                    [
                        dcc.Input(
                            id="version-input-3",
                            type="number",
                            value=68,
                        ),
                        dcc.Graph(id="plot-3-0"),
                        dcc.Graph(id="plot-3-1"),
                        dcc.Graph(id="plot-3-2"),
                    ]
                ),
            ],
            className="mb-4",
        )
    ],
    fluid=True,
)


def fetch_data(version):
    query = text(
        f"""
        WITH schd AS (
        SELECT *
        FROM schedule_dimension.schd_rail_timepoint_times srtt
        WHERE version = {version}
        AND ctadaymap = 1
    ),
    shortt AS (
        SELECT DISTINCT runid
        FROM schd
        WHERE timepointid SIMILAR TO '%(MgnMTS|FstPk|UICH|OHARE)%'
    )
    SELECT *
    FROM schd
    WHERE runid IN (SELECT runid FROM shortt);
        """
    )
    results = engine.execute(query)
    schd = pd.DataFrame(results.fetchall())

    df = schd
    schd["short_turned"] = False

    mgn_rows = df.loc[df["timepointid"] == "MgnMTS"]

    for _, mgn_row in mgn_rows.iterrows():
        runid = mgn_row["runid"]
        mgn_time = mgn_row["schd_time"]

        # Other rows for same runid
        run_rows = df.loc[(df["runid"] == runid)]

        # Update short_turned if schd_time is within threshold
        thresh = 1.2 * 3600
        df.loc[
            (df["runid"] == runid)
            & (df["schd_time"] >= mgn_time - thresh)
            & (df["schd_time"] <= mgn_time),
            "short_turned",
        ] = True

    fst_rows = df.loc[df["timepointid"] == "FosMTN"]

    for _, fst_row in fst_rows.iterrows():
        runid = fst_row["runid"]
        fst_time = fst_row["schd_time"]

        run_rows = df.loc[(df["runid"] == runid)]

        thresh = 2.7 * 3600
        df.loc[
            (df["runid"] == runid)
            & (df["schd_time"] >= fst_time - thresh)
            & (df["schd_time"] <= fst_time + thresh),
            "short_turned",
        ] = True

    schd["time"] = pd.to_timedelta(schd["schd_time"], unit="s")
    schd["timepoint"] = schd["timepointid"].str.slice(0, -1)

    sorted_stations = [
        "OHareN",
        "OHareS",
        "RosmtN",
        "RosmtS",
        "FosMTN",
        "FosMTS",
        "JffPkN",
        "JffPkS",
        "LogSqN",
        "LogSqS",
        "DivnMN",
        "DivnMS",
        "ClkLkN",
        "ClkLkS",
        "LaSalN",
        "LaSalS",
        "UICHdN",
        "UICHdS",
        "MgnMTN",
        "MgnMTS",
        "RacCnN",
        "RacCnS",
        "CicCnN",
        "CicCnS",
        "FstPkN",
        "FstPkS",
    ]

    sorted_stations = reversed(sorted_stations)

    station_to_category = {
        station: i
        for i, station in enumerate(
            [tp[:-1] for tp in sorted_stations if tp[-1] == "N"]
        )
    }

    # Apply the mapping to the 'timepoint' column to create a new categorical column
    schd["timepoint_category"] = schd["timepoint"].map(station_to_category)

    # Ensure the 'time' column is in the correct format (timedelta or datetime)
    schd["time"] = pd.to_timedelta(schd["schd_time"], unit="s") + pd.Timestamp(
        "1970/01/01"
    )
    schd.sort_values(by=["time"], inplace=True)

    sorted_run_ids = schd["runid"][schd["runid"] != "None"].unique()
    sorted_run_ids = sorted_run_ids[
        pd.Series(sorted_run_ids).str.extract(r"(\d+)")[0].astype(int).argsort()
    ]

    return schd, sorted_run_ids, station_to_category


def generate_plot_1(schd, sorted_run_ids, station_to_category):
    figs = []
    # Create the plot
    fig = px.line(
        schd,
        x="time",
        y="timepoint_category",
        color="runid",
        hover_data=schd.columns,
        labels={"timepoint_category": "Timepoint"},
        title="CTA Blue Line Schedule",
        category_orders={"runid": sorted_run_ids},
    )

    # sort runids in legend
    fig.update_layout(
        legend=dict(
            traceorder="normal",
            title="Run ID",
            title_font_family="Arial",
            font=dict(family="Arial", size=12, color="black"),
        )
    )

    # Update y-axis to show timepoint names instead of categories
    fig.update_yaxes(
        tickvals=list(station_to_category.values()),
        ticktext=list(station_to_category.keys()),
    )

    figs.append(fig)

    t = schd.query("timepointid == 'OHareS'").sort_values(by=["time"])[
        ["time", "runid", "short_turned"]
    ]

    t = t[t["runid"] != "None"]

    t["hdw"] = t["time"].diff().dt.seconds // 60

    # Add trace for short_turned == True
    fig = px.scatter(
        t,
        x="time",
        y="hdw",
        color="short_turned",
        hover_data=t.columns,
        title="Scheduled Headway of O-Hare Departures",
        labels={"hdw": "Headway (min)", "short_turned": "Short Turned"},
    )

    fig.update_xaxes(
        tickformat="%H:%M",
        title_text="Time of Day",
    )

    figs.append(fig)

    t = schd.query("timepointid == 'FstPkN'").sort_values(by=["time"])[
        ["time", "runid", "short_turned"]
    ]

    t = t[t["runid"] != "None"]

    t["hdw"] = t["time"].diff().dt.seconds // 60

    # Add trace for short_turned == True
    fig = px.scatter(
        t,
        x="time",
        y="hdw",
        # color="short_turned",
        hover_data=t.columns,
        title="Scheduled Headway of Forest Park Departures ",
        labels={"hdw": "Headway (min)"},
    )

    fig.update_xaxes(
        tickformat="%H:%M",
        title_text="Time of Day",
    )

    figs.append(fig)

    return figs


def generate_plot_2(schd):
    return


def generate_plot_3(schd):
    return
    # Process data and create plot 3 (similar to the provided code)
    # ...


# Callbacks to update plots
@app.callback(
    [
        Output("plot-1-0", "figure"),
        Output("plot-1-1", "figure"),
        Output("plot-1-2", "figure"),
    ],
    Input("version-input-1", "value"),
)
def update_plot_1(version):
    # schd = fetch_data(version)
    schd, sorted_run_ids, station_to_category = fetch_data(version)
    return generate_plot_1(schd, sorted_run_ids, station_to_category)


@app.callback(
    [
        Output("plot-2-0", "figure"),
        Output("plot-2-1", "figure"),
        Output("plot-2-2", "figure"),
    ],
    Input("version-input-2", "value"),
)
def update_plot_2(version):
    schd, sorted_run_ids, station_to_category = fetch_data(version)
    return generate_plot_1(schd, sorted_run_ids, station_to_category)


@app.callback(
    [
        Output("plot-3-0", "figure"),
        Output("plot-3-1", "figure"),
        Output("plot-3-2", "figure"),
    ],
    Input("version-input-3", "value"),
)
def update_plot_3(version):
    schd, sorted_run_ids, station_to_category = fetch_data(version)
    return generate_plot_1(schd, sorted_run_ids, station_to_category)


# Run the app


if __name__ == "__main__":
    app.run_server(
        debug=True,
        port=find_free_port(),
        host="127.0.0.1",
    )
