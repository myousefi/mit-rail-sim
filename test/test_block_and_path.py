import unittest
from unittest.mock import MagicMock

from transit_lab_simmetro.simulation_engine.infrastructure import (
    Block,
    Path,
    SignalControlCenter,
    Station,
)


class TestBlock(unittest.TestCase):
    def test_current_speed_code(self):
        block = Block("1", 10, 5, 50)
        self.assertEqual(block.current_speed_code, 50)

        block.add_communicated_speed_code("2", 40)
        self.assertEqual(block.current_speed_code, 40)

        block.remove_communicated_speed_code("2")
        self.assertEqual(block.current_speed_code, 50)

    def test_activate_deactivate(self):
        block = Block("1", 10, 5, 50)
        self.assertFalse(block.is_occupied)

        mock_train = MagicMock()
        block.activate(entering_train=mock_train)
        self.assertTrue(block.is_occupied)

        block.deactivate(exiting_train=mock_train)
        self.assertFalse(block.is_occupied)

    def test_observer(self):
        class MockObserver(SignalControlCenter):
            def __init__(self):
                self.updated = False

            def update(self, block):
                self.updated = True

        block = Block("1", 10, 5, 50)
        observer = MockObserver()
        block.add_observer(observer)
        self.assertFalse(observer.updated)

        block.notify_observers()
        self.assertTrue(observer.updated)


class TestPath(unittest.TestCase):
    def setUp(self):
        station1 = Station("A", 400, arrival_rates=MagicMock())
        station2 = Station("B", 600, arrival_rates=MagicMock())
        self.blocks = [
            Block("B1", 10, 1_000, 50, station=station1),
            Block("B2", 15, 7_000, 40),
            Block("B3", 20, 8_000, 60, station=station2),
            Block("B4", 25, 500, 30),
        ]
        self.path = Path(self.blocks)

    def test_get_total_length(self):
        self.assertEqual(self.path.get_total_length(), 16500)

    def test_get_distance_to_the_next_station(self):
        self.assertEqual(self.path.get_distance_to_the_next_station(0, 2), 398)
        self.assertEqual(self.path.get_distance_to_the_next_station(0, 5), 395)
        self.assertEqual(self.path.get_distance_to_the_next_station(1, 198), 7402)
        self.assertEqual(
            self.path.get_distance_to_the_next_station(3, 530), float("inf")
        )

    def test_get_distance_to_the_next_station_for_a_train(self):
        self.assertEqual(self.path.get_distance_to_the_next_station(0, 0), 400)
        self.assertEqual(self.path.get_distance_to_the_next_station(1, 0), 7600)


if __name__ == "__main__":
    unittest.main()
