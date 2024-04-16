import unittest
from test.base_test_case import TrainMovementVisualizationMixin
from unittest.mock import MagicMock

from matplotlib import pyplot as plt

from mit_rail_sim.simulation_engine.infrastructure import (
    Block,
    Path,
    SignalControlCenter,
    Station,
)
from mit_rail_sim.simulation_engine.train import (
    Train,
    TrainSpeedRegulator,
)

from mit_rail_sim.simulation_engine.utils import TrainLogger


class TestTrainStopatStation(unittest.TestCase, TrainMovementVisualizationMixin):
    def setUp(self):
        self.block1 = Block(
            block_id="Block_001",
            visible_distance=100,
            length=5000,
            default_speed_code=50,
            speed_codes_to_communicate={},
        )
        self.block2 = Block(
            block_id="Block_002",
            visible_distance=100,
            length=3000,
            default_speed_code=30,
            speed_codes_to_communicate={
                "Block_001": 20,
            },
            station=Station("A", 1000),
        )

        self.block3 = Block(
            block_id="Block_003",
            visible_distance=200,
            length=10_000,
            default_speed_code=60,
            speed_codes_to_communicate={
                "Block_001": 30,
                "Block_002": 10,
            },
        )

        self.block4 = Block(
            block_id="Block_004",
            visible_distance=200,
            length=10_000,
            default_speed_code=60,
            speed_codes_to_communicate={
                "Block_003": 0,
                "Block_002": 10,
            },
        )

        self.block5 = Block(
            block_id="Block_005",
            visible_distance=200,
            length=10_000,
            default_speed_code=60,
            speed_codes_to_communicate={
                "Block_004": 0,
                "Block_003": 10,
            },
            station=Station("B", 1000),
        )

        self.block6 = Block(
            block_id="Block_006",
            visible_distance=200,
            length=3_000,
            default_speed_code=45,
            speed_codes_to_communicate={
                "Block_005": 0,
                "Block_004": 20,
            },
        )

        self.block7 = Block(
            block_id="Block_007",
            visible_distance=200,
            length=10_000,
            default_speed_code=60,
            speed_codes_to_communicate={
                "Block_006": 0,
                "Block_005": 10,
            },
        )

        self.signal_control_center = SignalControlCenter(
            [
                self.block1,
                self.block2,
                self.block3,
                self.block4,
                self.block5,
                self.block6,
                self.block7,
            ]
        )

        self.path = Path(
            [
                self.block1,
                self.block2,
                self.block3,
                self.block4,
                self.block5,
                self.block6,
                self.block7,
            ]
        )

        self.train_speed_regulator = TrainSpeedRegulator(
            max_acceleration=4,
            normal_deceleration=2.17,
            emergency_deceleration=4.10,
        )

        self.train = Train(
            train_id="Train_001",
            train_logger=MagicMock(),
            train_speed_regulator=self.train_speed_regulator,
            path=self.path,
            time_step=self.TIMESTEP,
        )

    @unittest.skip("Test is visual")
    def test_train_stop_at_station(self):
        (
            speeds,
            times,
            distances,
            accelerations,
            planned_distances,
            current_speed_codes,
            distance_to_next_station_list,
            train_speed_regulator_states,
        ) = self._collect_train_data(1)

        self.visualize_time_profile(
            times,
            distances,
            "Distance from Start",
            train_speed_regulator_states,
        )
        self.visualize_time_profile(times, speeds, "Speed", train_speed_regulator_states)
        self.visualize_distance_profiles(
            distances,
            distance_to_next_station_list,
            "Distance to Station",
            train_speed_regulator_states=train_speed_regulator_states,
        )
        self.visualize_distance_profiles(
            distances,
            speeds,
            "Speed",
            train_speed_regulator_states,
            current_speed_codes,
        )
        self.visualize_distance_profiles(
            distances,
            accelerations,
            "Acceleration",
            train_speed_regulator_states=train_speed_regulator_states,
        )
        self.visualize_distance_profiles(distances, planned_distances, "Planned Distance")

    def test_distance_in_the_block_with_station_before_the_station(self):
        self.train.current_block_index = 1
        self.train.distance_travelled_in_current_block = 300

        self.assertEqual(self.train.distance_to_next_station, 700)

    def test_distance_in_the_block_with_station_after_the_station(self):
        self.train.current_block_index = 1
        self.train.distance_travelled_in_current_block = 1800

        self.assertEqual(self.train.distance_to_next_station, 22200)

    def test_dwell_time(self):
        dwell_times = [5, 10, 15]  # Dwell times at stations
        # Mock the dwelling time for each station
        self.path.blocks[1].station.get_dwell_time = MagicMock(return_value=dwell_times[0])
        self.path.blocks[4].station.get_dwell_time = MagicMock(return_value=dwell_times[1])

        (
            speeds,
            times,
            distances,
            accelerations,
            planned_distances,
            current_speed_codes,
            distance_to_next_station_list,
        ) = self._collect_train_data()

        station_a_time = 0
        station_b_time = 0
        for i in range(1, len(speeds)):
            if (
                self.path.blocks[1].length
                <= distances[i - 1]
                < self.path.blocks[1].length + self.path.blocks[2].length
                and speeds[i - 1] == 0
                and speeds[i] == 0
            ):
                station_a_time += times[i] - times[i - 1]

            if (
                self.path.blocks[4].length
                <= distances[i - 1]
                < self.path.blocks[4].length + self.path.blocks[5].length
                and speeds[i - 1] == 0
                and speeds[i] == 0
            ):
                station_b_time += times[i] - times[i - 1]

        self.assertAlmostEqual(station_a_time, dwell_times[0], delta=0.1)
        self.assertAlmostEqual(station_b_time, dwell_times[1], delta=0.1)
