import csv
import tempfile
import unittest
from pathlib import Path as PPath
from test.base_test_case import BaseTestCase

# from transit_lab_simmetro import Path, Simulation, TrainLogger, TrainSpeedRegulator


class TestTrainLogger(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create a temporary file for logging during testing
        self.temp_log_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.temp_log_file_path = self.temp_log_file.name
        self.log_interval = 10

        # Set up the train logger with the train from the BaseTestCase
        self.train_logger = TrainLogger(
            self.temp_log_file_path, self.log_interval, [self.train.train_id]
        )

        self.simulation = Simulation(
            [self.train],
            self.train_speed_regulator,
            self.train_logger,
            time_step=1,
        )

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
        ]

        self.assertEqual(header, expected_header)

    def test_logging_for_initial_time_and_first_row(self):
        # Update the train for a fixed number of time steps
        steps_to_log = self.log_interval * 50

        self.simulation.run(steps_to_log)

        # Check if the logged data is correct
        with open(self.temp_log_file_path, mode="r", newline="") as log_file:
            csv_reader = csv.reader(log_file)
            next(csv_reader)  # Skip the header row

            row = next(csv_reader)

            time_logged = int(float(row[0]))
            self.assertTrue(time_logged % self.log_interval == 0)

            train_id_logged = row[1]
            self.assertEqual(train_id_logged, self.train.train_id)

            # Check if the rest of the logged data matches the train's state
            self.assertEqual(float(row[2]), 0)
            self.assertEqual(float(row[3]), 0)
            self.assertEqual(float(row[4]), 0)
            self.assertEqual(int(row[5]), 0)
            self.assertEqual(float(row[6]), 0)
            self.assertEqual(row[7].lower() == "true", False)

    def test_logging_for_the_latest_step(self):
        steps_to_log = self.log_interval * 50

        self.simulation.run(steps_to_log)


if __name__ == "__main__":
    unittest.main()
