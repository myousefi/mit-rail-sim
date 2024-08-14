from __future__ import annotations

from typing import TYPE_CHECKING

import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

if TYPE_CHECKING:
    from mit_rail_sim.dash_app.helpers import HeadwayAnalysis, PlotCreator


def parse_results_dir(results_dir):
    parts = results_dir.split("/")
    signal_system_type = parts[1]
    slow_zones_accounted = parts[2]
    dispatching_headway = parts[3]
    cleaned_results_dir = "|".join(
        parts[4:]
    )  # removes the 'trb_experiments' part from the directory string

    return dbc.Alert(
        [
            html.P(
                [html.Strong("Signal System Type: "), html.Span(signal_system_type)]
            ),
            html.P(
                [html.Strong("Slow Zones Accounted: "), html.Span(slow_zones_accounted)]
            ),
            html.P(
                [html.Strong("Dispatching Headway: "), html.Span(dispatching_headway)]
            ),
            html.P(
                [html.Span(cleaned_results_dir)],
            ),  # use a smaller font
        ],
        color="info",
        className="floating-badge",
    )


def generate_layout(
    plot_creator: PlotCreator, analysis: HeadwayAnalysis, results_dir: str
):
    layout = dbc.Container(
        [
            # parse_results_dir(results_dir),
            dbc.Card(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    # html.Div(id="replication_id", style={"display": "none"}),
                                    dcc.Store(id="replication_id"),
                                    dbc.Label(
                                        [
                                            "Replication ID",
                                            # dbc.Badge("New", color="secondary", className="ml-1"),
                                        ],
                                        className="h5 font-weight-bold",
                                        id="replication-label",
                                    ),
                                    dbc.Tooltip(
                                        "Select a replication ID",
                                        target="replication-label",
                                        placement="bottom",
                                    ),
                                    dbc.Select(
                                        id="replication_id_dropdown",
                                        options=[
                                            {"label": rep_id, "value": rep_id}
                                            for rep_id in plot_creator.replication_ids
                                        ],
                                        value=plot_creator.replication_ids[0],
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Train ID", className="h5 font-weight-bold"
                                    ),
                                    dbc.Select(
                                        id="train_id_dropdown",
                                        options=[
                                            {"label": train_id, "value": train_id}
                                            for train_id in sorted(
                                                plot_creator.replication_station_data[
                                                    "train_id"
                                                ].unique()
                                            )
                                        ],
                                        value="train_0",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Profile", className="h5 font-weight-bold"
                                    ),
                                    dbc.Select(
                                        id="profile_dropdown",
                                        options=[
                                            {"label": "Speed", "value": "speed"},
                                            {
                                                "label": "Acceleration",
                                                "value": "acceleration",
                                            },
                                            {
                                                "label": "Distance",
                                                "value": "total_travelled_distance",
                                            },
                                        ],
                                        value="speed",
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                        className="mb-4",  # Add some bottom margin
                    ),
                ],
                body=False,
                color="light",  # Change the color of the Card
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5("Time Profile", className="font-weight-bold")
                    ),
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="loading-profile-graph",
                                type="cube",
                                children=dcc.Graph(
                                    id="profile_graph", style={"height": "80vh"}
                                ),
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5("Distance Profile", className="font-weight-bold")
                    ),
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="loading-distance-profile-graph",
                                type="cube",
                                children=dcc.Graph(
                                    id="distance_profile_graph",
                                    style={"height": "80vh"},
                                ),
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5(
                            "Distances Traveled Since Start",
                            className="font-weight-bold",
                        )
                    ),
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="loading-distances-graph",
                                type="cube",
                                children=dcc.Graph(
                                    id="distances_graph", style={"height": "100vh"}
                                ),
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5(
                            "Forest Park Departure Headway Analysis",
                            className="font-weight-bold",
                        )
                    ),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dcc.Loading(
                                            id="loading-forest-park-graph",
                                            type="cube",
                                            children=[
                                                dcc.Graph(
                                                    id="forest_park_graph",
                                                    figure=analysis.plot_histogram(
                                                        analysis.real_headway_fp,
                                                        analysis.sim_headway_forest_park,
                                                        "Forest Park",
                                                    ),
                                                ),
                                            ],
                                        ),
                                        width=8,
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            [
                                                dbc.CardHeader(
                                                    "Statistics",
                                                    className="text-center",
                                                ),
                                                dbc.CardBody(
                                                    [
                                                        html.Div(
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        html.P(
                                                                            "Mean (minutes):",
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 0, 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.mean('SIM', 'Forest Park'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(255, 0, 0,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.mean('REAL', 'Forest Park'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 255,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                ],
                                                            ),
                                                            style={"height": "25%"},
                                                        ),
                                                        html.Div(
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                "Standard deviation"
                                                                                " (minutes):"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 0, 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.std('SIM', 'Forest Park'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(255, 0, 0,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.std('REAL', 'Forest Park'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 255,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                ],
                                                            ),
                                                            style={"height": "25%"},
                                                        ),
                                                        html.Div(
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                "Coefficient of"
                                                                                " variation:"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 0, 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.coef_var('SIM', 'Forest Park'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(255, 0, 0,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.coef_var('REAL', 'Forest Park'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 255,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                ],
                                                            ),
                                                            style={"height": "25%"},
                                                        ),
                                                    ]
                                                ),
                                            ]
                                        ),
                                        width=3,
                                        # className="d-flex align-items-center",
                                        className="w-auto",
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5(
                            "UIC-Halsted Departure Headway Analysis",
                            className="font-weight-bold",
                        )
                    ),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dcc.Loading(
                                            id="loading-uic-halsted-graph",
                                            type="cube",
                                            children=[
                                                dcc.Graph(
                                                    id="uic_halsted_graph",
                                                    figure=analysis.plot_histogram(
                                                        analysis.real_headway_uic_halsted,
                                                        analysis.sim_headway_uic_halsted,
                                                        "UIC-Halsted",
                                                    ),
                                                ),
                                            ],
                                        ),
                                        width=8,
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            [
                                                dbc.CardHeader(
                                                    "Statistics",
                                                    className="text-center",
                                                ),
                                                dbc.CardBody(
                                                    [
                                                        html.Div(
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        html.P(
                                                                            "Mean (minutes):",
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 0, 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.mean('SIM', 'UIC-Halsted'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(255, 0, 0,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.mean('REAL', 'UIC-Halsted'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 255,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                ],
                                                            ),
                                                            style={"height": "25%"},
                                                        ),
                                                        html.Div(
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                "Standard deviation"
                                                                                " (minutes):"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 0, 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.std('SIM', 'UIC-Halsted'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(255, 0, 0,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.std('REAL', 'UIC-Halsted'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 255,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                ],
                                                            ),
                                                            style={"height": "25%"},
                                                        ),
                                                        html.Div(
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                "Coefficient of"
                                                                                " variation:"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 0, 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.coef_var('SIM', 'UIC-Halsted'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(255, 0, 0,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                    dbc.Col(
                                                                        html.P(
                                                                            (
                                                                                f"{analysis.coef_var('REAL', 'UIC-Halsted'):.2f}"
                                                                            ),
                                                                            className="text-center",
                                                                        ),
                                                                        style={
                                                                            "backgroundColor": (
                                                                                "rgba(0, 0, 255,"
                                                                                " 0.6)"
                                                                            ),
                                                                            "color": "white",
                                                                        },
                                                                        className=(
                                                                            "d-flex"
                                                                            " align-items-center"
                                                                            " justify-content-center"
                                                                        ),
                                                                    ),
                                                                ],
                                                            ),
                                                            style={"height": "25%"},
                                                        ),
                                                    ]
                                                ),
                                            ]
                                        ),
                                        width=3,
                                        # className="d-flex align-items-center",
                                        className="w-auto",
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Station", className="h5 font-weight-bold"
                                    ),
                                    dbc.Select(
                                        id="station_dropdown",
                                        options=[
                                            {
                                                "label": station_name,
                                                "value": station_name,
                                            }
                                            for station_name in plot_creator.station_names
                                        ],
                                        value=plot_creator.station_names[0],
                                    ),
                                ],
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Direction", className="h5 font-weight-bold"
                                    ),
                                    dbc.Select(
                                        id="direction_dropdown",
                                        options=[
                                            {
                                                "label": "Northbound",
                                                "value": "Northbound",
                                            },
                                            {
                                                "label": "Southbound",
                                                "value": "Southbound",
                                            },
                                        ],
                                        value="Northbound",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4",  # Add some bottom margin
                    ),
                ],
                body=False,
                color="light",
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5("Headway Histogram", className="font-weight-bold")
                    ),
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="loading-headway-graphs",
                                type="cube",
                                children=[
                                    # dcc.Graph(id="headway_scatter_graph"),
                                    dcc.Graph(id="headway_histogram_graph"),
                                ],
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5("Arrival Rates Heatmap", className="font-weight-bold")
                    ),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dcc.Store(id="hour-range"),
                                            dbc.Label(
                                                [
                                                    "Time Range",
                                                ],
                                                className="h5 font-weight-bold",
                                                id="time-range-label",
                                            ),
                                            dbc.Tooltip(
                                                "Select a time range",
                                                target="time-range-label",
                                                placement="bottom",
                                            ),
                                            dcc.RangeSlider(
                                                id="hour-range-slider",
                                                min=0,
                                                max=24,
                                                step=0.25,
                                                value=[0, 1],
                                                marks={
                                                    i: f"{i:02d}:00" for i in range(25)
                                                },
                                            ),
                                        ],
                                        className="mb-3",
                                        width=10,
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.Store(id="weekday-checkbox-data"),
                                            dbc.Label(
                                                [
                                                    "Weekday",
                                                ],
                                                className="h5 font-weight-bold",
                                                id="weekday-label",
                                            ),
                                            dbc.Tooltip(
                                                "Select weekday or weekend",
                                                target="weekday-label",
                                                placement="bottom",
                                            ),
                                            dcc.RadioItems(
                                                id="weekday-checkbox",
                                                options=[
                                                    {"label": "Weekday", "value": True},
                                                    {
                                                        "label": "Weekend",
                                                        "value": False,
                                                    },
                                                ],
                                                value=True,
                                                inline=True,
                                            ),
                                        ],
                                        width=2,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dcc.Graph(
                                                id="heatmap",
                                                style={"height": "75vh"},
                                            ),
                                        ],
                                        style={
                                            "height": "80vh"
                                        },  # to make the heatmap full height
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                className="mb-4 w-100",  # to make the card full width
                style={"height": "100vh"},  # to make the card full height
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5("Average Waiting Time", className="font-weight-bold")
                    ),
                    dbc.CardBody(
                        [
                            dbc.Spinner(
                                dcc.Graph(
                                    id="average_waiting_time_graph",
                                    figure=plot_creator.create_average_waiting_time_figure(),
                                ),
                                color="primary",
                                type="grow",
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # dbc.Card(
            #     [
            #         dbc.CardHeader(
            #             html.H5("Reliability Buffer Time Heatmap", className="font-weight-bold")
            #         ),
            #         dbc.CardBody(
            #             [
            #                 dbc.Spinner(
            #                     dcc.Graph(
            #                         id="reliability_buffer_time_heatmap",
            #                         style={"height": "75vh"},
            #                         figure=plot_creator.create_reliability_buffer_time_figure(),
            #                     ),
            #                     color="primary",
            #                     type="grow",
            #                 ),
            #             ]
            #         ),
            #     ],
            #     className="mb-4",
            # ),
            dbc.Card(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Origin Station",
                                        className="h5 font-weight-bold",
                                    ),
                                    dbc.Select(
                                        id="origin_dropdown",
                                        options=[
                                            {
                                                "label": station_name,
                                                "value": station_name,
                                            }
                                            for station_name in plot_creator.station_names
                                        ],
                                        value=plot_creator.station_names[0],
                                    ),
                                ]
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Destination Station",
                                        className="h5 font-weight-bold",
                                    ),
                                    dbc.Select(
                                        id="destination_dropdown",
                                        options=[
                                            {
                                                "label": station_name,
                                                "value": station_name,
                                            }
                                            for station_name in plot_creator.station_names
                                        ],
                                        value=plot_creator.station_names[1],
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4",  # Add some bottom margin
                    ),
                ],
                body=False,
                color="light",
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H5("Travel Time Histogram", className="font-weight-bold")
                    ),
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="loading-travel-time-histogram",
                                type="cube",
                                children=dcc.Graph(id="travel_time_histogram"),
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
        ],
        fluid=True,
    )
    return layout
