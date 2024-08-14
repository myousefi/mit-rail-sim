import json

from mit_rail_sim.utils import project_root

# Load first file
with open(
    project_root
    / "data"
    / "cta_blue_line_infra"
    / "northbound_signal_blocks_and_tracks.json",
    "r",
) as f:
    data1 = json.load(f)

# Load second file
with open(project_root / "Before_speed_code_checks.json", "r") as f:
    data2 = json.load(f)

# Create a dictionary mapping OBJECTID to STATION in the second file
objectid_to_station = {d["OBJECTID"]: d["STATION"] for d in data2 if "STATION" in d}

# Loop through the first file's data
for d in data1:
    # Remove the existing STATION field
    if "STATION" in d:
        del d["STATION"]

    # Add the STATION field from the second file, if it exists
    if d["OBJECTID"] in objectid_to_station:
        d["STATION"] = objectid_to_station[d["OBJECTID"]]

# Save the result back to the first file (or another file if desired)
with open(
    project_root
    / "data"
    / "cta_blue_line_infra"
    / "northbound_signal_blocks_and_tracks_corrected_stations.json",
    "w",
) as f:
    json.dump(data1, f, indent=4)
