import json
from datetime import datetime

from mit_rail_sim.utils.db_con import engine, text
from mit_rail_sim.utils.root_path import project_root

start_date = "2023-11-13"  # Replace with your desired start date
end_date = "2024-02-04"  # Replace with your desired end date
version = 81  # Replace with your desired version

# Read the SQL queries from files
with open(
    project_root / "mit_rail_sim" / "cta-data-queries" / "empirical-schedule.sql", "r"
) as file:
    empirical_schedule_query = text(file.read())

with open(
    project_root / "mit_rail_sim" / "cta-data-queries" / "blue-line-schedule.sql", "r"
) as file:
    blue_line_schedule_query = text(file.read())

# Execute the empirical schedule query
empirical_schedule_results = engine.execute(
    empirical_schedule_query,
    start_date=start_date,
    end_date=end_date,
).fetchall()

# Execute the blue line schedule query
blue_line_schedule_results = engine.execute(
    blue_line_schedule_query,
    version=version,
).fetchall()

# Convert the results to dictionaries
empirical_schedule_data = [
    {
        "event_time": row[0].isoformat(),
        "time_in_sec": int(row[1]),
        "runid": row[2],
        "headway": row[3],
        "deviation": row[4],
        "direction": row[5],
    }
    for row in empirical_schedule_results
]


blue_line_schedule_data = [
    {
        "runid": row[0],
        "time_in_sec": int(row[1]),
        "terminal": row[2],
        "short_turned": row[3],
    }
    for row in blue_line_schedule_results
]

# Create a dictionary to store the results
output_data = {
    "empirical_schedule": empirical_schedule_data,
    "blue_line_schedule": blue_line_schedule_data,
}

# Generate the output file name with the current version
# output_file = f"empirical_schedule_{version}.json"
output_file = (
    project_root / "inputs" / "schedules" / f"empirical_schedule_{version}.json"
)

# Save the results to a JSON file
with open(output_file, "w") as file:
    json.dump(output_data, file, indent=2)

print(f"Results saved to {output_file}")
