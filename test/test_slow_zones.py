import json
import unittest
from typing import List

from mit_rail_sim.simulation_engine.infrastructure import SlowZone


def write_slow_zones_to_json(slow_zones: List[SlowZone], file_path: str) -> None:
    with open(file_path, "w") as file:
        json.dump([zone.to_dict() for zone in slow_zones], file)


def read_slow_zones_from_json(file_path: str) -> List[SlowZone]:
    with open(file_path, "r") as file:
        slow_zones_data = json.load(file)
    return [SlowZone.from_dict(data) for data in slow_zones_data]


class TestSlowZoneFunctions(unittest.TestCase):
    def setUp(self):
        self.slow_zones = [
            SlowZone("WC-444", 25),
            SlowZone("WC-448", 25),
            SlowZone("WC-452", 25),
            SlowZone("WC-422", 25),
            SlowZone("WC-417", 25),
            SlowZone("WC-411", 25),
            SlowZone("WC-401", 25),
            SlowZone("WC-395", 35),
            SlowZone("WC-387", 35),
            SlowZone("WC-381", 35),
            SlowZone("WC-374", 35),
            SlowZone("661", 35),
            SlowZone("WC-366", 25),
            SlowZone("WC-361", 25),
            SlowZone("WC-355", 25),
            SlowZone("WC-350", 25),
            SlowZone("WC-339", 25),
            SlowZone("WC-333", 25),
            SlowZone("WC-323", 25),
            SlowZone("WC-314", 25),
            SlowZone("WC-302", 15),
            SlowZone("WC-293", 15),
            SlowZone("651", 25),
            SlowZone("WC-283", 25),
            SlowZone("WC-279", 25),
            SlowZone("WC-273", 15),
            SlowZone("WC-266", 15),
            SlowZone("WC-259", 15),
            SlowZone("WC-253", 25),
            SlowZone("WC-244", 25),
            SlowZone("WC-239", 25),
            SlowZone("WC-232", 25),
            SlowZone("WC-225", 15),
            SlowZone("WC-219", 15),
            SlowZone("641", 15),
            SlowZone("WC-212", 15),
            SlowZone("WC-206", 15),
            SlowZone("WC-199", 15),
            SlowZone("WC-192", 15),
            SlowZone("WC-186", 15),
            SlowZone("WC-178", 15),
            SlowZone("WC-172", 15),
            SlowZone("WC-166", 15),
            SlowZone("631", 25),
            SlowZone("WC-158", 35),
            SlowZone("WC-151", 35),
            SlowZone("WC-138", 35),
            SlowZone("WC-130", 35),
            SlowZone("WC-125", 25),
            SlowZone("WC-117", 25),
            SlowZone("WC-111", 25),
            SlowZone("621", 25),
            SlowZone("WC-104", 25),
            # SlowZone("WC-98", 35),
            SlowZone("WC-92", 35),
            SlowZone("WC-88", 35),
            SlowZone("WC-79", 25),
            SlowZone("WC-75", 15),
            SlowZone("WC-69", 15),
            SlowZone("WC-63", 15),
            SlowZone("WC-54", 25),
            # SlowZone("WC-48", 25),
            SlowZone("WC-32", 35),
            SlowZone("321", 35),
            SlowZone("311", 15),
            SlowZone("WC-16", 15),
            SlowZone("WC-11", 15),
            SlowZone("WC-8", 15),
            SlowZone("WC-5", 15),
            SlowZone("WC-3", 15),
            SlowZone("C1", 15),
            SlowZone("NWC-590", 15),
            SlowZone("75", 15),
            SlowZone("NWC-599", 15),
            SlowZone("NWC-606", 15),
            SlowZone("35", 15),
            SlowZone("NWC-284", 25),
            SlowZone("NWC-208", 15),
            # 213
            # 215
            # 218
            # 221
            # 225
            # 229
            # 235
            # 244
            # 247
            # 251
            SlowZone("NWC-213", 15),
            SlowZone("NWC-215", 15),
            SlowZone("NWC-218", 15),
            SlowZone("NWC-221", 15),
            SlowZone("NWC-225", 15),
            SlowZone("NWC-229", 15),
            SlowZone("NWC-235", 15),
            SlowZone("NWC-244", 15),
            SlowZone("NWC-247", 15),
            SlowZone("NWC-251", 15),
            # 122
            # 128
            # 133
            # 136
            # 141
            # 143
            # 146
            # 149
            # 154
            # 158
            # SlowZone("NWC-122", 15),
            SlowZone("NWC-128", 25),
            SlowZone("NWC-133", 15),
            SlowZone("NWC-136", 15),
            SlowZone("233", 15),
            SlowZone("NWC-141", 15),
            SlowZone("NWC-143", 15),
            SlowZone("NWC-146", 15),
            SlowZone("NWC-149", 15),
            SlowZone("NWC-154", 25),
            SlowZone("NWC-88", 35),
            SlowZone("NWC-93", 35),
            SlowZone("NWC-97", 25),
            SlowZone("LN1-225", 15),
            SlowZone("273", 15),
            SlowZone("LN1-231", 15),
        ]

    def test_slow_zone_to_dict(self):
        for zone in self.slow_zones:
            zone_dict = zone.to_dict()
            self.assertEqual(zone.block_id, zone_dict["block_id"])
            self.assertEqual(zone.reduced_speed_limit, zone_dict["reduced_speed_limit"])

    def test_slow_zone_from_dict(self):
        for zone in self.slow_zones:
            zone_dict = zone.to_dict()
            reconstructed_zone = SlowZone.from_dict(zone_dict)
            self.assertEqual(reconstructed_zone.block_id, zone.block_id)
            self.assertEqual(
                reconstructed_zone.reduced_speed_limit, zone.reduced_speed_limit
            )

    def test_write_read_slow_zones_to_from_json(self):
        file_path = "test_slow_zones.json"
        write_slow_zones_to_json(self.slow_zones, file_path)

        read_zones = read_slow_zones_from_json(file_path)
        for original_zone, read_zone in zip(self.slow_zones, read_zones):
            self.assertEqual(original_zone.block_id, read_zone.block_id)
            self.assertEqual(
                original_zone.reduced_speed_limit, read_zone.reduced_speed_limit
            )


if __name__ == "__main__":
    unittest.main()
