import csv
import json

from mit_rail_sim.utils import project_root

# Read CSV file and extract unique station names
with open(project_root / "data" / "arrival_rates.csv", "r") as csv_file:
    csv_reader = csv.reader(csv_file)
    next(csv_reader)  # Skip the header
    csv_stations = set(row[2] for row in csv_reader)  # Origin stops
    csv_file.seek(0)  # Reset file pointer to start
    next(csv_reader)  # Skip the header again
    csv_stations.update(row[3] for row in csv_reader)  # Destination stops

# Sort the station names
csv_stations = sorted(list(csv_stations))

# Read JSON file and extract unique station names
with open(project_root / "file.json", "r") as json_file:
    json_data = json.load(json_file)
    json_stations = set(
        item["STATION"]["STATION_NAME"] for item in json_data if "STATION" in item
    )

# Sort the station names
json_stations = sorted(list(json_stations))

# Compare the two lists and mark the differences with '*'
max_length = max(len(csv_stations), len(json_stations))
csv_stations.extend([""] * (max_length - len(csv_stations)))
json_stations.extend([""] * (max_length - len(json_stations)))

# Print the sorted lists
print("CSV Stations:     JSON Stations:")
for csv_station, json_station in zip(csv_stations, json_stations):
    difference_marker = "*" if csv_station != json_station else ""
    print(f"{csv_station:<20} {difference_marker} {json_station}")
