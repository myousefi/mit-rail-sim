Getting Started
===============

Quick Start
-----------
1. Prepare the input files:

   - Ensure you have the following files in the `inputs` directory:
      - infra.json: Infrastructure data
      - slow_zones.json: Slow zone definitions
      - demand/odx_demand.csv: Passenger demand data
      - schedules/empirical_schedule.json: Train schedule data

2. Configure the simulation:

   - Open the `load-balance/config.yaml` file
   - Adjust the following parameters as needed:
      - simulation.number_of_replications
      - simulation.start_time_of_day
      - simulation.end_time_of_day
      - demand_level
      - station
      - short_turning
      - logger.should_log_trajectories
      - logger.log_interval

3. Run the simulation:

   .. code-block:: bash

      python -m mit_rail_sim.simulation_runner.runner

4. Check the output:

   - Look for the generated log files in the specified log folder (default: `log_folder_path`)
   - You'll find CSV and JSON files with various simulation data

Understanding the Inputs and Config
-----------------------------------
1. Infrastructure (infra.json):

   - Defines blocks, stations, and path information for Northbound and Southbound directions

2. Slow Zones (slow_zones.json):

   - Specifies areas with reduced speed limits

3. Demand Data (odx_demand.csv):

   - Contains passenger arrival rates at 15-minute intervals for weekdays and non-weekdays for each OD pair

4. Schedule Data (empirical_schedule.json):

   - Defines train dispatch times and routes

5. Configuration (config.yaml):

   - simulation: Set replication count, start and end times
   - demand_level: Adjust overall passenger demand. Used as a multiplier to uniformly scale demand.
   - station: Specify holding station (e.g., "O-Hare" or "Clark/Lake")
   - short_turning: Set short turning location ("UIC" or "Western")
   - logger: Configure logging options

By adjusting these inputs and configurations, you can simulate various scenarios and analyze the rail system's performance under different conditions.
