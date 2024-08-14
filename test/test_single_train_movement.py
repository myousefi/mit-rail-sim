from test.base_test_case import BaseTestCase, RandomizedBaseTestCase


class TestTrainMovement(BaseTestCase):
    def test_single_train_movement(self):
        (
            speeds,
            times,
            distances,
            accelerations,
            planned_distances,
            current_speed_codes,
            distance_to_next_station_list,
        ) = self._collect_train_data()

        self.visualize_time_profile(times, distances, "Distance from Start")
        self.visualize_time_profile(times, speeds, "Speed")
        self.visualize_distance_profiles(
            distances, distance_to_next_station_list, "Distance to Station"
        )
        self.visualize_distance_profiles(
            distances, speeds, "Speed", current_speed_codes
        )
        self.visualize_distance_profiles(distances, accelerations, "Acceleration")
        self.visualize_distance_profiles(
            distances, planned_distances, "Planned Distance"
        )


class TestTrainMovementRandomBlocks(RandomizedBaseTestCase):
    def test_single_train_movement(self):
        (
            speeds,
            times,
            distances,
            accelerations,
            planned_distances,
            current_speed_codes,
            distance_to_next_station_list,
        ) = self._collect_train_data()

        self.visualize_time_profile(times, speeds, "Speed")
        self.visualize_time_profile(times, distances, "Distance")
        self.visualize_distance_profiles(
            distances, distance_to_next_station_list, "Distance to Station"
        )
        self.visualize_distance_profiles(
            distances, speeds, "Speed", current_speed_codes
        )
        self.visualize_distance_profiles(distances, accelerations, "Acceleration")
        self.visualize_distance_profiles(
            distances, planned_distances, "Planned Distance"
        )
