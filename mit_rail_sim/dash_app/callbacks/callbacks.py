from __future__ import annotations

from typing import TYPE_CHECKING

from dash import Input, Output

if TYPE_CHECKING:
    from dash import Dash

    from mit_rail_sim.dash_app.helpers import ArrivalRatePlotCreator, PlotCreator


def callbacks(
    app: Dash,
    plot_creator: PlotCreator,
    arrival_rate_plot_creator: ArrivalRatePlotCreator,
):
    @app.callback(
        Output(
            "replication_id", "data"
        ),  # Dummy output, won't actually change anything
        [Input("replication_id_dropdown", "value")],
    )
    def update_replication_id(replication_id):
        replication_id = int(replication_id)
        plot_creator._generate_hover_texts(replication_id)
        # print(f"Replication ID: {type(replication_id)} {replication_id}")
        return replication_id

    @app.callback(
        Output("distances_graph", "figure"),
        [
            # Input("dummy_input", component_property="data"),
            Input("replication_id", "data"),
        ],  # Use the dummy_input as a trigger
    )
    def update_distances_graph(replication_id):
        return plot_creator.visualize_trajectories_for_all_trains(replication_id)

    @app.callback(
        Output("profile_graph", "figure"),
        [
            Input("train_id_dropdown", "value"),
            Input("profile_dropdown", "value"),
            Input("replication_id", "data"),
        ],
    )
    def update_graph(train_id, profile, replication_id):
        if profile in ["speed", "acceleration"]:
            title = profile.capitalize()

        elif profile == "total_travelled_distance":
            title = "Distance"
        else:
            raise ValueError("Profile not applicable")

            # plot_creator.set_replication_id(replication_id)
        return plot_creator.visualize_time_profile_from_logs(
            replication_id=replication_id,
            train_ids=[train_id],
            profile_column=profile,
            title=title,
        )

    # @app.callback(
    #     Output("headway_scatter_graph", "figure"),
    #     [
    #         Input("station_dropdown", "value"),
    #         Input("replication_id", "data"),
    #     ],
    # )
    # def update_headway_scatter(station_name, replication_id):
    #     return plot_creator.create_headway_scatter(replication_id, station_name)

    @app.callback(
        Output("headway_histogram_graph", "figure"),
        [Input("station_dropdown", "value")],
        [Input("direction_dropdown", "value")],
    )
    def update_headway_histogram(station_name, direction):
        return plot_creator.create_headway_histogram(station_name, direction)

    @app.callback(
        Output("distance_profile_graph", "figure"),
        [
            Input("train_id_dropdown", "value"),
            Input("profile_dropdown", "value"),
            Input("replication_id", "data"),
        ],
    )
    def update_distance_profile_graph(train_id, profile, replication_id):
        # if profile in ["speed", "acceleration", "total_travelled_distance"]:
        if profile in ["speed", "acceleration"]:
            title = profile.capitalize()

        elif profile == "total_travelled_distance":
            title = "Distance"
        else:
            raise ValueError("Profile not applicable")
            # plot_creator.set_replication_id(replication_id)
        return plot_creator.visualize_distance_profile_from_logs(
            replication_id,
            train_ids=[train_id],
            profile_column=profile,
            title=title,
        )

    @app.callback(
        Output("travel_time_histogram", "figure"),
        [Input("origin_dropdown", "value"), Input("destination_dropdown", "value")],
    )
    def update_travel_time_histogram(origin, destination):
        return plot_creator.create_travel_time_histogram(origin, destination)

    @app.callback(
        Output("heatmap", "figure"),
        [Input("hour-range-slider", "value"), Input("weekday-checkbox", "value")],
    )
    def update_arrival_rates_figure(hour_range, weekday):
        is_weekday = weekday if weekday else False
        return arrival_rate_plot_creator.get_figure(
            hour_range[0], hour_range[1], is_weekday
        )
