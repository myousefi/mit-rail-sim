import json


from mit_rail_sim.utils import project_root

# Step 1: Create a list of all blocks associated with stations and the blocks that come immediately after them
with open(project_root / "alt_file_northbound_updated.json", "r") as f:
    data = json.load(f)
    block_dict = []

    for i, block in enumerate(data[:-1]):
        block_dict.append({"block_id": block["BLOCK"], "reduced_speed_limit": 0})

# save the block_dict to a json file
with open("calibrated_slow_zones.json", "w") as f:
    json.dump(block_dict, f, indent=4)
