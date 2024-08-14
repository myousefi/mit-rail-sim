import csv
import tempfile
import unittest
from pathlib import Path as PPath
from test.base_test_case import BaseTestCase

from mit_rail_sim.simulation_engine.utils import TrainLogger


class TestTrainLogger(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create a temporary file for logging during testing
        self.temp_log_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.temp_log_file_path = self.temp_log_file.name
        self.log_interval = 10

        # Set up the train logger with the train from the BaseTestCase
        self.train_logger = TrainLogger(
            self.train, self.temp_log_file_path, self.log_interval
        )
        self.train.train_logger = self.train_logger

    def tearDown(self):
        # Close and remove the temporary log file
        self.temp_log_file.close()
        PPath(self.temp_log_file_path).unlink()

    def test_header_written(self):
        # Check if the header has been written correctly
        with open(self.temp_log_file_path, mode="r", newline="") as log_file:
            csv_reader = csv.reader(log_file)
            header = next(csv_reader)

        expected_header = [
            "time_step",
            "train_id",
            "speed",
            "acceleration",
            "total_travelled_distance",
            "current_block_index",
            "distance_travelled_in_current_block",
            "is_at_station",
            # TODO Number of passengers on board
        ]

        self.assertEqual(header, expected_header)

    def test_logging(self):
        # Update the train for a fixed number of time steps
        time_step = 1
        steps_to_log = self.log_interval * 5

        for _ in range(steps_to_log):
            self.train.update(time_step)

        # Check if the logged data is correct
        with open(self.temp_log_file_path, mode="r", newline="") as log_file:
            csv_reader = csv.reader(log_file)
            next(csv_reader)  # Skip the header row

            for row in csv_reader:
                time_step_logged = int(row[0])
                self.assertTrue(time_step_logged % self.log_interval == 0)

                train_id_logged = row[1]
                self.assertEqual(train_id_logged, self.train.train_id)

                # Check if the rest of the logged data matches the train's state
                self.assertEqual(float(row[2]), self.train.speed)
                self.assertEqual(float(row[3]), self.train.acceleration)
                self.assertEqual(float(row[4]), self.train.total_travelled_distance)
                self.assertEqual(int(row[5]), self.train.current_block_index)
                self.assertEqual(
                    float(row[6]), self.train.distance_travelled_in_current_block
                )
                self.assertEqual(row[7].lower() == "true", self.train.is_at_station())


if __name__ == "__main__":
    unittest.main()
