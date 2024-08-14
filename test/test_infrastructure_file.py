import json
import unittest

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from mit_rail_sim.utils import project_root

FIGURE_WIDTH = 10000
FIGURE_HEIGHT = 1000
MARGIN = dict(l=50, r=50, b=100, t=100, pad=4)


class TestPlotInfrastructure(unittest.TestCase):
    def load_data_from_file(self, file_name):
        try:
            with open(file_name) as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            print(f"File {file_name} not found.")
            return []
        except json.JSONDecodeError:
            print(f"Error decoding JSON from file {file_name}")
            return []

    def add_trace_to_figure(self, fig, x_values, y_values, line_dict, mode="lines"):
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode=mode,
                line=line_dict,
                showlegend=False,
            )
        )

    def test_infrastructure_plot(self):
        rail_data_json = self.load_data_from_file("alt_file_southbound_updated.json")
        # slow_zones_json = self.load_data_from_file("test_slow_zones.json")
        slow_zones_json = []

        # if rail_data_json and slow_zones_json:
        fig, _ = self.plot_blocks_and_stations(rail_data_json, slow_zones_json)
        fig.show()

    def plot_blocks_and_stations(self, rail_data_json, slow_zones_json):
        # stations = self.calculate_absolute_distance(rail_data_json)

        fig = go.Figure()

        distance = 0
        block_to_segment = {}
        block_alt_segment = {}

        for index, segment in enumerate(rail_data_json):
            # start = int(segment["STARTSTN"])
            # end = int(segment["ENDSTN"])
            # speed = int(segment["SPEED"])
            start = distance  # start is now based on the cumulative distance
            end = distance + int(
                segment["DISTANCE"]
            )  # end is now based on distance plus the segment's distance
            speed = int(segment["SPEED"])

            # Plot the speed limit within each block as a horizontal line
            self.add_trace_to_figure(
                fig, [start, end], [speed, speed], dict(color="blue", width=1)
            )

            # Plot the blocks
            fig.add_shape(
                type="line",
                x0=start,
                y0=0,
                x1=start,
                y1=1,
                yref="paper",
                line=dict(color="grey", width=1, dash="dash"),
            )
            fig.add_annotation(
                x=start,
                y=1,
                yref="paper",
                yshift=-10,
                text=f'{segment["BLOCK"]}({index})',
                showarrow=False,
                textangle=-20,
            )

            # Plot the stations
            if "STATION" in segment:
                station_name = segment["STATION"]["STATION_NAME"]
                end_of_platform_milepost = int(
                    segment["STATION"]["END_OF_PLATFORM_MILEPOST"]
                )
                station_pos = distance + abs(
                    end_of_platform_milepost - segment["STARTSTN"]
                )
                fig.add_shape(
                    type="line",
                    x0=station_pos,
                    y0=0,
                    x1=station_pos,
                    y1=1,
                    yref="paper",
                    line=dict(color="red", width=2),
                )
                fig.add_annotation(
                    x=station_pos + 100,
                    y=0.9,
                    yref="paper",
                    yshift=-10,
                    text=station_name,
                    showarrow=False,
                    textangle=-90,
                )

            block_id = segment["BLOCK"]
            block_to_segment[block_id] = (distance, distance + int(segment["DISTANCE"]))

            block_alt_segment[segment["BLOCK_ALT"]] = (
                distance,
                distance + int(segment["DISTANCE"]),
            )

            distance += int(segment["DISTANCE"])

            # Plot the reduced speed limit for each slow zone
        for slow_zone in slow_zones_json:
            block_id = slow_zone["block_id"]
            reduced_speed_limit = slow_zone["reduced_speed_limit"]

            if block_id in block_to_segment:
                start, end = block_to_segment[block_id]

                # Plot the reduced speed limit as a dashed red line
                self.add_trace_to_figure(
                    fig,
                    [start, end],
                    [reduced_speed_limit, reduced_speed_limit],
                    dict(color="red", width=5, dash="dash"),
                )

        fig.update_layout(
            xaxis_title="Distance",
            yaxis_title="Speed Limit",
            title="Infrastructure",
            autosize=False,
            width=FIGURE_WIDTH,
            height=FIGURE_HEIGHT,
            margin=MARGIN,
            showlegend=False,
        )

        return fig, block_alt_segment

    def test_plot(self):
        with open("alt_file_northbound_updated.json") as f:
            rail_data_json = json.load(f)
        with open("test_slow_zones.json") as f:
            slow_zones_json = json.load(f)
        self.plot_blocks_and_stations(rail_data_json, slow_zones_json)

    def test_avl_vs_simulation_speeds(self):
        with open("alt_file_northbound_updated.json") as f:
            rail_data_json = json.load(f)

        with open("calibrated_slow_zones.json") as f:
            # with open(project_root / "temp_scripts" / "slow_zones.json") as f:
            # with open(project_root / "temp_scripts" / "slow_zones.json") as f:
            slow_zones_json = json.load(f)

        fig, block_alt_segment = self.plot_blocks_and_stations(
            rail_data_json=rail_data_json, slow_zones_json=slow_zones_json
        )

        track_speed_dict = pd.read_csv(
            project_root
            / "mit_rail_sim"
            / "validation"
            / "data"
            / "track_events_result.csv"
        )

        for index, row in track_speed_dict.iterrows():
            if row["scada"] in block_alt_segment:
                start, end = block_alt_segment[row["scada"]]
                self.add_trace_to_figure(
                    fig,
                    [start, end],
                    [row["speed"], row["speed"]],
                    dict(color="green", width=3),
                )

        sim_speed_dict = pd.read_csv(
            project_root
            / "mit_rail_sim"
            / "validation"
            / "simulation_results"
            / "block_test_speed.csv"
        )

        for index, row in sim_speed_dict.iterrows():
            if row["scada"] in block_alt_segment:
                start, end = block_alt_segment[row["scada"]]
                self.add_trace_to_figure(
                    fig,
                    [start, end],
                    [row["speed"], row["speed"]],
                    dict(color="purple", width=3),
                )

        fig.show()

    def test_avl_vs_sim_speed_scatter_plot(self):
        sim_speed = pd.read_csv(
            project_root
            / "mit_rail_sim"
            / "validation"
            / "simulation_results"
            / "block_test_speed.csv"
        )

        avl_speed = pd.read_csv(
            project_root
            / "mit_rail_sim"
            / "validation"
            / "data"
            / "track_events_result.csv"
        )

        df = (
            pd.concat([avl_speed, sim_speed], keys=["avl", "sim"])
            .reset_index(level=0)
            .rename(columns={"level_0": "source"})
        )

        fig = px.scatter(df, x="scada", y="speed", color="source")
        fig.show()
        # fig.add_trace(go.Scatter())


if __name__ == "__main__":
    unittest.main()
