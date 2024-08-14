import json


from mit_rail_sim.utils import project_root

# Step 1: Create a list of all blocks associated with stations and the blocks that come immediately after them
with open(project_root / "alt_file_northbound_updated.json", "r") as f:
    data = json.load(f)
    scada_next = {}
    for i, block in enumerate(data[:-1]):
        if "STATION" in block:
            try:
                scada_next[block["STATION"]["STATION_NAME"]] = (
                    block["BLOCK_ALT"],
                    data[i + 2]["BLOCK_ALT"],
                )
            except IndexError:
                continue

print(scada_next)
