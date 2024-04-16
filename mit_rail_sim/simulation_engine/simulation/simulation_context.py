# from __future__ import annotations

# from typing import TYPE_CHECKING

# if TYPE_CHECKING:
#     from mit_rail_sim.simulation_engine.simulation.simulation import Simulation

# from mit_rail_sim.simulation_engine.infrastructure import Station
# from mit_rail_sim.simulation_engine.train import Train
# from mit_rail_sim.simulation_engine.passenger import Passenger


# class SimulationContext:
#     def __init__(self, simulation: Simulation):
#         self.simulation = simulation

#     def __enter__(self):
#         Train.simulation = self.simulation
#         Passenger.simulation = self.simulation
#         Station.simulation = self.simulation

#     def __exit__(self, exc_type, exc_value, traceback):
#         Train.simulation = None
#         Passenger.simulation = None
#         Station.simulation = None
