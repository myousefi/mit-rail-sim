from mit_rail_sim.utils import project_root
import json

# Load the JSON data
path = project_root / "data" / "cta_blue_line_infra" / "northbound_signal_blocks_and_tracks_corrected_stations.json"

with open(path, "r") as file:
    data = json.load(file)

# Create a list of speeds to communicate
speeds_to_communicate = [15, 25, 35, 35, 55, 55]

# Iterate over the data backwards
for i in range(len(data) - 1, -1, -1):
    # If the current block does not have "SPEED_CODES_TO_COMMUNICATE", create it
    if "SPEED_CODES_TO_COMMUNICATE" not in data[i]:
        data[i]["SPEED_CODES_TO_COMMUNICATE"] = {}

        # If it's not the first block
        if i > 0:
            # Add the previous block to SPEED_CODES_TO_COMMUNICATE with a speed of 0
            previous_block = data[i - 1]["BLOCK"]
            data[i]["SPEED_CODES_TO_COMMUNICATE"][previous_block] = 0

        # If it's not the last block
        if i < len(data) - 1:
            # Add the next blocks to SPEED_CODES_TO_COMMUNICATE with speeds from speeds_to_communicate list
            previous_blocks = data[i - 5 : i - 1]
            for j, block in enumerate(previous_blocks):
                data[i]["SPEED_CODES_TO_COMMUNICATE"][block["BLOCK"]] = speeds_to_communicate[j]

# Write the updated data back to the file
with open("file.json", "w") as file:
    json.dump(data, file, indent=4)
