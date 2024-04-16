import unittest
from unittest.mock import MagicMock

from mit_rail_sim.simulation_engine.train import Train

from mit_rail_sim.simulation_engine.train.train_speed_regulator import (  # AccelerateToSpeedCodeState,
    TrainSpeedRegulator,
)
from mit_rail_sim.simulation_engine.train.train_speed_regulator_state import (
    TrainSpeedRegulatorState,
    KeepingTheSpeedUptoCodeState,
    DecelerateToSpeedNormalRateForPlanningState,
    BrakeWithMaximumRateState,
    BrakeNormalToStationState,
)


class TestTrainSpeedRegulator(unittest.TestCase):
    def setUp(self):
        self.train = MagicMock()
        self.train.speed = 0
        self.train.current_block.current_speed_code = 0
        self.train.next_block.current_speed_code = 0
        self.train.distance_to_next_block = 0
        self.train.distance_to_next_station = 0
        self.regulator = TrainSpeedRegulator(
            max_acceleration=3,
            normal_deceleration=1,
            emergency_deceleration=2,
        )

        self.regulator.register_train(self.train)

    def test_normal_acceleration(self):
        for speed, expected_accel in [
            (0, 3),
            (10, 3),
            (20, 2.4),
            (30, 2.4),
            (40, 1.8),
            (50, 1.8),
            (60, 1.2),
            (70, 1.2),
        ]:
            self.train.speed = speed
            self.assertAlmostEqual(self.regulator.normal_acceleration, expected_accel)

    def test_planning_distance(self):
        for cur_speed_code, next_speed_code, expected_planning_dist in [
            (60, 40, 1000),
            (60, 60, 0),
            (40, 60, 0),
        ]:
            self.train.current_block.current_speed_code = cur_speed_code
            self.train.next_block.current_speed_code = next_speed_code
            self.assertAlmostEqual(self.regulator.planning_distance, expected_planning_dist)

    def test_braking_distance(self):
        for speed, expected_braking_distance in [
            (0, 0),
            (20, 200),
            (40, 800),
            (60, 1800),
        ]:
            self.train.speed = speed
            self.assertAlmostEqual(self.regulator.braking_distance, expected_braking_distance)

    def test_regulate_acceleration(self):
        self.regulator.state = MagicMock()
        self.regulator.regulate_acceleration()
        self.regulator.state.handle.assert_called_once()


class TestTrainSpeedRegulatorState(unittest.TestCase):
    def test_abstract_methods(self):
        with self.assertRaises(TypeError):
            TrainSpeedRegulatorState()

            class TestState(TrainSpeedRegulatorState):
                def handle_custom_transition(self):
                    pass

                def set_the_acceleration(self):
                    pass

            self.assertIsNotNone(TestState())


class TestKeepingTheSpeedStateUptoCode(unittest.TestCase):
    def setUp(self):
        self.regulator = MagicMock()
        self.state = KeepingTheSpeedUptoCodeState(self.regulator)

    def test_set_the_acceleration(self):
        test_cases = [
            (39, 40, 0),
            (40, 40, 0),
            (41, 40, -1),
        ]
        for speed, speed_code, accel in test_cases:
            self.regulator.train.speed = speed
            self.regulator.train.current_block.current_speed_code = speed_code
            self.regulator.normal_acceleration = 2.4
            self.regulator.normal_deceleration = 1
            self.state.set_the_acceleration()
            self.assertEqual(self.regulator.train.acceleration, accel)

    def test_handle_the_transition_to_next_state(self):
        test_cases = [
            (200, 510, True, False),
            (310, 500, False, True),
            (600, 500, False, True),
        ]
        for (
            dist_to_next_block,
            dist_to_next_station,
            transition1,
            transition2,
        ) in test_cases:
            self.regulator.train.distance_to_next_block = dist_to_next_block
            self.regulator.train.distance_to_next_station = dist_to_next_station
            self.regulator.planning_distance = 300
            self.regulator.braking_distance = 500
            self.state.handle_custom_transition()
            if transition1:
                self.assertIsInstance(
                    self.regulator.state, DecelerateToSpeedNormalRateForPlanningState
                )
            elif transition2:
                self.assertIsInstance(self.regulator.state, BrakeNormalToStationState)


class TestDecelerateToSpeedNormalRateForPlanningState(unittest.TestCase):
    def setUp(self):
        self.regulator = MagicMock()
        self.next_block = MagicMock()
        self.state = DecelerateToSpeedNormalRateForPlanningState(self.regulator, self.next_block)

    def test_set_the_acceleration(self):
        test_cases = [
            (60, 40, 60, -1, 0),
            (60, 60, 40, -1, 0),
            (40, 60, 60, 0, 0),
        ]
        for speed, current_speed_code, next_speed_code, accel, transition in test_cases:
            self.regulator.train.speed = speed
            self.regulator.train.current_block.current_speed_code = current_speed_code
            self.regulator.train.next_block.current_speed_code = next_speed_code
            self.regulator.normal_deceleration = 1
            self.state.set_the_acceleration()
            self.assertEqual(self.regulator.train.acceleration, accel)

    def test_handle_the_transition_to_next_state(self):
        self.regulator.train.current_block = MagicMock()
        self.state.restricting_block = self.regulator.train.current_block
        self.state.handle_custom_transition()
        self.assertIsInstance(self.regulator.state, KeepingTheSpeedUptoCodeState)


class TestBreakWithMaximumRateState(unittest.TestCase):
    def setUp(self):
        self.regulator = MagicMock()
        self.state = BrakeWithMaximumRateState(self.regulator)

    def test_set_the_acceleration(self):
        test_cases = [
            (60, 40, -3, 0),
            (40, 60, 0, 0),
            (80, 80, 0, 0),
        ]
        for speed, speed_code, accel, transition in test_cases:
            self.regulator.train.speed = speed
            self.regulator.train.current_block.current_speed_code = speed_code
            self.regulator.emergency_deceleration = 3
            self.state.set_the_acceleration()
            self.assertEqual(self.regulator.train.acceleration, accel)

    def test_handle_the_transition_to_next_state(self):
        test_cases = [
            (60, 80, False),
            (80, 80, True),
            (100, 80, True),
        ]
        for speed, speed_code, state_change in test_cases:
            self.regulator.train.speed = speed
            self.regulator.train.current_block.current_speed_code = speed_code
            self.state.handle_custom_transition()
            if state_change:
                self.assertIsInstance(self.regulator.state, AccelerateToSpeedCodeState)
