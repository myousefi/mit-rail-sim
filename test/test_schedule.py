import unittest
from test.test_CTA_blue_line_imaginary import (
    CTABlueLineTestCase,
    TestCTABlueLineTrainMovement,
)
from typing import List, Optional
from unittest.mock import MagicMock

import pandas as pd
import plotly.graph_objects as go

from mit_rail_sim.simulation_engine.infrastructure import Path
from mit_rail_sim.simulation_engine.schedule import Schedule
from mit_rail_sim.simulation_engine.simulation.simulation import Simulation
from mit_rail_sim.simulation_engine.train import Train, TrainSpeedRegulator
from mit_rail_sim.simulation_engine.utils import TrainLogger

# Import Schedule and Simulation classes here


class TestSchedule(unittest.TestCase):
    def test_random_dispatch_times(self):
        num_trains = 5
        min_interval = 1 * 60
        max_interval = 2 * 60
        schedule = Schedule(num_trains, min_interval, max_interval)
        self.assertEqual(len(schedule.dispatch_times), num_trains)

        for i in range(len(schedule.dispatch_times) - 1):
            interval = schedule.dispatch_times[i + 1] - schedule.dispatch_times[i]
            self.assertGreaterEqual(interval, min_interval)
            self.assertLessEqual(interval, max_interval)


class TestSimulation(TestCTABlueLineTrainMovement):
    def test_simulation_initialization(self):
        schedule = Schedule(3, 10, 20)
        train_speed_regulator = TrainSpeedRegulator(
            max_acceleration=4,
            normal_deceleration=2.17,
            emergency_deceleration=4.10,
        )
        train_logger = MagicMock()
        path = MagicMock()
        sim = Simulation(schedule, train_speed_regulator, train_logger, path)

        self.assertEqual(sim.schedule, schedule)
        self.assertEqual(sim.train_speed_regulator, train_speed_regulator)
        self.assertEqual(sim.train_logger, train_logger)
        self.assertEqual(sim.path, path)
        self.assertEqual(sim.trains, [])

    # @unittest.skip("This test is for visualization purposes only.")
    def test_train_dispatch_during_simulation(self):

        try:
            # schedule = Schedule(10, 30, 40)
            schedule = MagicMock()
            schedule.dispatch_times = [0, 30, 300, 1800]
            train_speed_regulator = TrainSpeedRegulator(
                max_acceleration=4,
                normal_deceleration=2.17,
                emergency_deceleration=4.10,
            )
            train_logger = TrainLogger(
                log_file_path="./test/output_files/test.csv", log_interval=10
            )
            passenger_logger = MagicMock()
            path = self.path
            sim = Simulation(
                schedule=schedule,
                train_logger=train_logger,
                passenger_logger=passenger_logger,
                path=path,
                time_step=0.1,
            )

            sim.run(60 * 60)  # Run the simulation for 5 time units
        except Exception as e:
            self.save_seed(self.current_seed)
            raise e

        log_file_path = "./test/output_files/test.csv"
        df = pd.read_csv(log_file_path)

        unique_train_ids = df["train_id"].unique()

        for train_id in unique_train_ids:
            train_df = df[df["train_id"] == train_id]
            (
                times,
                speeds,
                accelerations,
                distances,
                train_speed_regulator_states,
                train_received_speed_codes,
            ) = self.extract_train_data(train_df)

            # Call the visualization functions
            self.visualize_time_profile(
                times,
                speeds,
                f"Speed for {train_id}",
                train_speed_regulator_states,
                train_received_speed_codes=train_received_speed_codes,
            )
            self.visualize_time_profile(
                times,
                accelerations,
                f"Acceleration for {train_id}",
                train_speed_regulator_states,
            )
            self.visualize_distance_profiles(
                distances,
                speeds,
                f"Speed Profile for {train_id}",
                train_speed_regulator_states,
                # train_received_speed_codes=train_received_speed_codes,
                current_speed_codes=train_received_speed_codes,
            )

            self.visualize_time_profile(
                times,
                distances,
                title=f"Distance from Start for {train_id}",
                train_speed_regulator_states=train_speed_regulator_states,
            )

        log_file_path = "./test/output_files/test.csv"
        data = pd.read_csv(log_file_path)

        train_ids = data["train_id"].unique().tolist()  # Get unique train_ids from the data

        # self.visualize_time_profile_from_logs(data, train_ids, "speed", "Speed")

        # self.visualize_time_profile_from_logs(
        #     data, train_ids, "acceleration", "Acceleration"
        # )

        self.visualize_speed_vs_distance_profile_from_logs(data, train_ids, "speed", "Speed")
        self.visualize_time_profile_from_logs(
            data, train_ids, "total_travelled_distance", "Distance"
        )

        # self.assertEqual(len(sim.trains), 3)  # Three trains should be dispatched

    def extract_train_data(self, train_df):
        times = train_df["time_in_seconds"].tolist()
        speeds = train_df["speed"].tolist()
        accelerations = train_df["acceleration"].tolist()
        distances = train_df["total_travelled_distance"].tolist()
        train_speed_regulator_states = train_df["train_speed_regulator_state"].tolist()
        train_received_speed_codes = train_df["train_received_speed_code"].tolist()

        return (
            times,
            speeds,
            accelerations,
            distances,
            train_speed_regulator_states,
            train_received_speed_codes,
        )

    def visualize_time_profile_from_logs(
        self,
        data: pd.DataFrame,
        train_ids: List[str],
        profile_column: str,
        title: str = "",
        train_speed_regulator_states: Optional[List] = None,
    ):
        fig = go.Figure()

        for train_id in train_ids:
            train_data = data[data["train_id"] == train_id]
            times = train_data["time_in_seconds"]
            profile = train_data[profile_column]

            if train_speed_regulator_states is not None:
                state_data = train_data[train_speed_regulator_states]

                # Create a list of unique states
                unique_states = state_data.unique()

                for state, group in train_data.groupby(train_speed_regulator_states):
                    state_index = unique_states.tolist().index(state)

                    fig.add_trace(
                        go.Scatter(
                            x=group["time_in_seconds"],
                            y=group[profile_column],
                            mode="markers",
                            name=f"{train_id}: {state}",
                            marker=dict(color=self.get_color(state_index)),
                            legendgroup=f"{train_id}: {state}",
                        ),
                    )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=times,
                        y=profile,
                        mode="lines",
                        name=f"{train_id}: {title}",
                    ),
                )

        fig.update_layout(title=title, xaxis_title="Time", yaxis_title=title)
        fig.show()

    def visualize_speed_vs_distance_profile_from_logs(
        self,
        data: pd.DataFrame,
        train_ids: List[str],
        profile_column: str,
        title: str = "",
        train_speed_regulator_states: Optional[List] = None,
    ):
        fig = go.Figure()

        for train_id in train_ids:
            train_data = data[data["train_id"] == train_id]
            distances = train_data["total_travelled_distance"]
            profile = train_data[profile_column]

            if train_speed_regulator_states is not None:
                state_data = train_data[train_speed_regulator_states]

                # Create a list of unique states
                unique_states = state_data.unique()

                for state, group in train_data.groupby(train_speed_regulator_states):
                    state_index = unique_states.tolist().index(state)

                    fig.add_trace(
                        go.Scatter(
                            x=group["total_travelled_distance"],
                            y=group[profile_column],
                            mode="markers+line",
                            name=f"{train_id}: {state}",
                            marker=dict(color=self.get_color(state_index)),
                            legendgroup=f"{train_id}: {state}",
                        ),
                    )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=distances,
                        y=profile,
                        mode="markers+lines",
                        name=f"{train_id}: {title}",
                    ),
                )

        fig.update_layout(title=title, xaxis_title="Distance", yaxis_title=title)
        fig.show()


if __name__ == "__main__":
    unittest.main()
