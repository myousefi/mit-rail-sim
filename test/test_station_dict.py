import unittest
import json


def calculate_absolute_distance(rail_data_json):
    # with open(filename, 'r') as f:
    #     data = json.load(f)

    distance = 0
    stations = {}
    for segment in rail_data_json:
        if "STATION" in segment:
            stations[segment["STATION"]["STATION_NAME"]] = (
                distance
                + int(segment["STATION"]["END_OF_PLATFORM_MILEPOST"])
                - int(segment["STARTSTN"])
            )
        distance += int(segment["DISTANCE"])

    return stations


class TestStationDict(unittest.TestCase):
    def setUp(self):
        infrastructure_file_path = "file.json"
        with open(infrastructure_file_path, "r") as f:
            rail_data_json = json.load(f)

        self.stations_dict = calculate_absolute_distance(rail_data_json)

    def test_print_station_dict(self):
        print(self.stations_dict)
