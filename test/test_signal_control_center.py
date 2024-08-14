from test.base_test_case import BaseTestCase

from mit_rail_sim.simulation_engine.infrastructure import Block, SignalControlCenter


class TestSignalControlCenter(BaseTestCase):
    def setUp(self):
        self.block1 = Block(
            block_id="Block_001",
            visible_distance=100,
            length=500,
            default_speed_code=50,
            communicated_speed_codes={
                "Block_002": 10,
            },
        )
        self.block2 = Block(
            block_id="Block_002",
            visible_distance=100,
            length=3000,
            default_speed_code=30,
            communicated_speed_codes={
                "Block_001": 20,
            },
        )
        self.block3 = Block(
            block_id="Block_003",
            visible_distance=200,
            length=1000,
            default_speed_code=60,
            communicated_speed_codes={
                "Block_001": 15,
                "Block_002": 25,
            },
        )
        self.signal_control_center = SignalControlCenter(
            [self.block1, self.block2, self.block3]
        )

    def test_initial_speed_codes(self):
        self.assertEqual(self.block1.current_speed_code, 50)
        self.assertEqual(self.block2.current_speed_code, 30)
        self.assertEqual(self.block3.current_speed_code, 60)

    def test_block_activation(self):
        self.block1.activate()
        self.assertEqual(
            self.block2.current_speed_code, 30
        )  # The speed code from Block_001 should be communicated
        self.block1.deactivate()
        self.assertEqual(
            self.block2.current_speed_code, self.block2.default_speed_code
        )  # The speed code should be restored to its initial value

    def test_block_deactivation(self):
        self.block3.activate()
        self.assertEqual(self.block1.current_speed_code, 30)  # No change expected
        self.assertEqual(self.block2.current_speed_code, 10)
        self.block3.deactivate()
        self.assertEqual(self.block1.current_speed_code, 50)  # No change expected
        self.assertEqual(self.block2.current_speed_code, 30)
