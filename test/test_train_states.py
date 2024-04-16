import unittest

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

from mit_rail_sim.simulation_engine.train.train_speed_regulator_state import (
    KeepingTheSpeedUptoCodeState,
    BrakeNormalToStationState,
)

from mit_rail_sim.simulation_engine.train.train_state import (
    DwellingAtStationState,
    MovingBetweenStationsState,
)


class BaseTestCase(unittest.TestCase):
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

        self.signal_control_center = SignalControlCenter([self.block1, self.block2, self.block3])

        self.path = Path([self.block1, self.block2, self.block3])

        self.train_speed_regulator = TrainSpeedRegulator(
            max_acceleration=4,
            normal_deceleration=2.17,
            emergency_deceleration=4.10,
        )

        self.train = Train(
            train_id="Train_001",
            train_logger=TrainLogger(),
            train_speed_regulator=self.train_speed_regulator,
            path=self.path,
        )

    def visualize_distance_profiles(self, distances, values, values_label, title) -> None:
        plt.plot(distances, values)
        plt.xlabel("Distance (m)")
        plt.ylabel(values_label)
        plt.title(title)
        plt.show()


class TestMovingBetweenStationsState(BaseTestCase):
    def test_handle(self):
        initial_speed = self.train.speed
        initial_distance_travelled = self.train.total_travelled_distance
        time_step = 0.5

        self.train.state.handle(time_step)

        expected_speed = initial_speed + self.train.acceleration * time_step
        expected_distance_travelled = initial_distance_travelled + (
            initial_speed * time_step + 0.5 * self.train.acceleration * time_step**2
        )

        self.assertAlmostEqual(self.train.speed, expected_speed)
        self.assertAlmostEqual(self.train.total_travelled_distance, expected_distance_travelled)

    def test_transition_to_dwelling_at_station(self):
        self.train.current_block_index = 1
        self.train.distance_travelled_in_current_block = 300

        self.train.speed = 60

        braking_distance = self.train.train_speed_regulator.braking_distance
        self.train.state.handle(0.5)

        # assert if is the same class as self.train.train_speed_regulator.state is BrakeToNormalState()
        self.assertIsInstance(self.train.train_speed_regulator.state, BrakeNormalToStationState)

    def test_train_at_brake_normal_state(self):
        self.train.current_block_index = 1
        self.train.distance_travelled_in_current_block = 940
        self.train.speed = 10

        self.train.train_speed_regulator.state = KeepingTheSpeedUptoCodeState(
            self.train.train_speed_regulator
        )

        for _ in range(20):
            self.train.update(0.5)


class TestDwellingAtStationState(BaseTestCase):
    def test_handle(self):
        initial_acceleration = self.train.acceleration
        dwell_time = 10.0
        time_step = 0.5

        self.train.state.handle(time_step)

        self.train.state = None

        self.assertAlmostEqual(self.train.state.dwell_elapsed_time, time_step)
        self.assertAlmostEqual(self.train.acceleration, initial_acceleration)
        # self.assertEqual(self.train.state, self.state)
