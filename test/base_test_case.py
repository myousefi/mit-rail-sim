import unittest
from test.test_visualization import VisualizationMixin
from unittest.mock import MagicMock

from transit_lab_simmetro.simulation_engine.infrastructure import (
    Block,
    Path,
    SignalControlCenter,
    Station,
)
from transit_lab_simmetro.simulation_engine.train import Train, TrainSpeedRegulator
from transit_lab_simmetro.simulation_engine.train.train import NextBlockNotFoundError


class TrainMovementVisualizationMixin(VisualizationMixin):
    TIMESTEP = 0.1

    def _collect_train_data(self, sampling_interval=50):
        (
            speeds,
            times,
            distances,
            accelerations,
            planned_distances,
            current_speed_codes,
            distance_to_next_station_list,
            train_speed_regulator_states,
        ) = ([] for _ in range(8))

        distance, time = 0, 0
        sampling_counter = 0

        while True:
            try:
                if sampling_counter % sampling_interval == 0:
                    speed = self.train.speed
                    distance = self.train.total_travelled_distance
                    acceleration = self.train.acceleration
                    planned_distance = self.train_speed_regulator.planning_distance
                    current_speed_code = self.train.current_block.current_speed_code(
                        self.train
                    )
                    distance_to_next_station = self.train.distance_to_next_station
                    train_speed_regulator_state = str(
                        self.train.train_speed_regulator.state
                    )

                    speeds.append(speed)
                    times.append(time)
                    distances.append(distance)
                    accelerations.append(acceleration)
                    planned_distances.append(planned_distance)
                    current_speed_codes.append(current_speed_code)
                    distance_to_next_station_list.append(distance_to_next_station)
                    train_speed_regulator_states.append(train_speed_regulator_state)

                self.train.update()
                time += self.TIMESTEP
                sampling_counter += 1

            except NextBlockNotFoundError:
                break

        return (
            speeds,
            times,
            distances,
            accelerations,
            planned_distances,
            current_speed_codes,
            distance_to_next_station_list,
            train_speed_regulator_states,
        )


class BaseTestCase(unittest.TestCase, TrainMovementVisualizationMixin):
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
            station=Station("A", 4000),
        )
        self.block4 = Block(
            block_id="Block_004",
            visible_distance=1000,
            length=5_000,
            default_speed_code=10,
            speed_codes_to_communicate={
                "Block_002": 15,
                "Block_003": 0,
            },
        )

        self.block5 = Block(
            block_id="Block_005",
            visible_distance=500,
            length=2_000,
            default_speed_code=10,
            speed_codes_to_communicate={
                "Block_003": 30,
                "Block_004": 0,
            },
        )

        self.block6 = Block(
            block_id="Block_006",
            visible_distance=500,
            length=3_000,
            default_speed_code=30,
            speed_codes_to_communicate={
                "Block_004": 30,
                "Block_005": 0,
            },
            # station=Station("B", 1000),
        )

        self.block7 = Block(
            block_id="Block_007",
            visible_distance=500,
            length=4_000,
            default_speed_code=50,
            speed_codes_to_communicate={
                "Block_005": 30,
                "Block_006": 0,
            },
        )

        self.block8 = Block(
            block_id="Block_008",
            visible_distance=500,
            length=5_000,
            default_speed_code=70,
            speed_codes_to_communicate={
                "Block_006": 30,
                "Block_007": 0,
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
                self.block8,
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
                self.block8,
            ]
        )

        self.train_speed_regulator = TrainSpeedRegulator(
            max_acceleration=4,
            normal_deceleration=2.17,
            emergency_deceleration=4.10,
        )

        self.train = Train(
            train_id="Train_001",
            # train_logger=TrainLogger(),
            # TODO add train logger
            train_logger=MagicMock(),
            train_speed_regulator=self.train_speed_regulator,
            path=self.path,
            time_step=self.TIMESTEP,
        )


class RandomizedBaseTestCase(unittest.TestCase, TrainMovementVisualizationMixin):
    def setUp(self):
        import random

        def random_speed_codes(block_ids):
            speed_codes = {}
            for block_id in block_ids:
                speed_codes[block_id] = random.randint(0, 60)
            return speed_codes

        self.block1 = Block(
            block_id="Block_001",
            visible_distance=random.randint(50, 1000),
            length=random.randint(1000, 10000),
            default_speed_code=random.randint(10, 60),
            speed_codes_to_communicate=random_speed_codes(["Block_002"]),
        )
        self.block2 = Block(
            block_id="Block_002",
            visible_distance=random.randint(50, 1000),
            length=random.randint(1000, 10000),
            default_speed_code=random.randint(10, 60),
            speed_codes_to_communicate=random_speed_codes(["Block_001", "Block_003"]),
        )
        self.block3 = Block(
            block_id="Block_003",
            visible_distance=random.randint(50, 1000),
            length=random.randint(1000, 10000),
            default_speed_code=random.randint(10, 60),
            speed_codes_to_communicate=random_speed_codes(
                ["Block_001", "Block_002", "Block_004"]
            ),
            station=Station("A", random.randint(10, 900)),
        )

        self.block4 = Block(
            block_id="Block_004",
            visible_distance=random.randint(50, 1000),
            length=random.randint(1000, 10000),
            default_speed_code=random.randint(10, 60),
            speed_codes_to_communicate=random_speed_codes(
                ["Block_002", "Block_003", "Block_005"]
            ),
        )

        self.block5 = Block(
            block_id="Block_005",
            visible_distance=random.randint(50, 1000),
            length=random.randint(1000, 10000),
            default_speed_code=random.randint(10, 60),
            speed_codes_to_communicate=random_speed_codes(["Block_003", "Block_004"]),
        )

        self.signal_control_center = SignalControlCenter(
            [self.block1, self.block2, self.block3, self.block4, self.block5]
        )

        self.path = Path(
            [self.block1, self.block2, self.block3, self.block4, self.block5]
        )

        self.train_speed_regulator = TrainSpeedRegulator(
            max_acceleration=random.uniform(2, 6),
            normal_deceleration=random.uniform(1, 4),
            emergency_deceleration=random.uniform(3, 8),
        )

        self.train = Train(
            train_id="Train_001",
            train_logger=MagicMock(),
            train_speed_regulator=self.train_speed_regulator,
            path=self.path,
        )
