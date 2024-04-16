import json
import os

import click
import dash
import dash_bootstrap_components as dbc
import plotly.io as pio

from mit_rail_sim.dash_app.callbacks.callbacks import callbacks
from mit_rail_sim.dash_app.helpers import (
    ArrivalRatePlotCreator,
    HeadwayAnalysis,
    PlotCreator,
)
from mit_rail_sim.dash_app.helpers.data_helpers import load_data
from mit_rail_sim.dash_app.layout import generate_layout
from mit_rail_sim.utils import find_free_port

pio.templates.default = "simple_white"

from pathlib import Path

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    assets_folder=str(Path(__file__).parent / "assets"),
)


def check_files_exist(directory):
    required_files = ["train_test.csv", "station_test.csv", "passenger_test.csv"]
    for filename in required_files:
        if not os.path.exists(os.path.join(directory, filename)):
            raise ValueError(
                f"File {filename} does not exist in the directory {directory}"
            )


@click.command()
@click.option(
    "-r1",
    "--results_dir1",
    type=click.Path(exists=True),
    default="test/test_trb_submission_experiments/results",
    help="Directory of the results",
)
@click.option(
    "-s1",
    "--scenario_name1",
    type=str,
    default="scenario_1",
    help="Name of the scenario",
)
@click.option(
    "-r2",
    "--results_dir2",
    type=click.Path(exists=True),
    default="test/test_trb_submission_experiments/results",
    help="Directory of the results",
)
@click.option(
    "-s2",
    "--scenario_name2",
    type=str,
    default="scenario_2",
    help="Name of the scenario",
)
def main(results_dir):
    check_files_exist(results_dir)

    (
        train_data,
        station_data,
        passenger_data,
        stations_dict,
        travel_times_data,
    ) = load_data(results_dir)

    headway_analysis = HeadwayAnalysis(
        "data/emprical_schedule/cleaned_events.csv",
        f"{results_dir}/train_test.csv",
        f"{results_dir}/station_test.csv",
    )

    plot_creator = PlotCreator(
        train_data, station_data, travel_times_data, passenger_data, stations_dict
    )

    arrival_rate_plot_creator = ArrivalRatePlotCreator(
        "data/arrival_rates.csv", stations_dict
    )

    app.layout = generate_layout(
        plot_creator=plot_creator, analysis=headway_analysis, results_dir=results_dir
    )
    callbacks(
        app,
        plot_creator=plot_creator,
        arrival_rate_plot_creator=arrival_rate_plot_creator,
    )

    port = find_free_port()
    print(
        f"Starting server on port {port}, displaying data from directory {results_dir}"
    )
    app.run_server(debug=True, port=port)


if __name__ == "__main__":
    main()
