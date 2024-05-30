from copy import deepcopy
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from mit_rail_sim.simulation_engine.schedule_refactored.dispatch_strategies import (
    GammaDispatchStrategy,
    WeibullDispatchStrategy,
    EmpiricalDispatchStrategy,
)


class BaseSchedule(ABC):
    def __init__(self, file_path, start_time_of_day: int, end_time_of_day: int):
        self.replication_id = None
        self.file_path = file_path
        self.start_time_of_day = start_time_of_day
        self.end_time_of_day = end_time_of_day

        self.dispatch_info: Optional[List[Tuple[float, int, str, str]]] = None

    @abstractmethod
    def get_strategy(self):
        pass

    @abstractmethod
    def generate_random_dispatch_info(self):
        pass

    def set_replication_id(self, seed_number: int):
        self.replication_id = seed_number

    # TODO: Implement copy method
    def copy(self):
        return deepcopy(self)


class GammaSchedule(BaseSchedule):
    def __init__(self, file_path, start_time_of_day: int, end_time_of_day: int):
        super().__init__(file_path, start_time_of_day, end_time_of_day)
        self.validate_params()

    def validate_params(self):
        required_params = ["num_trains", "mean", "cv"]
        for param in required_params:
            if param not in self.params:
                raise KeyError(f"Missing required parameter: {param}")

    def get_strategy(self):
        return GammaDispatchStrategy()

    def generate_random_dispatch_info(self) -> List[Tuple[float, int]]:
        # TODO: Implement gamma schedule dispatch info generation
        pass

    def adjust_dispatch_info(self, short_turning_rate, start_hour_of_day):
        # TODO: Implement dispatch info adjustment for short turning and start hour
        pass


class WeibullSchedule(BaseSchedule):
    def __init__(self, params_path, start_time_of_day: int, end_time_of_day: int):
        super().__init__(params_path, start_time_of_day, end_time_of_day)
        self.validate_params()

    def validate_params(self):
        required_params = ["num_trains", "shape", "scale"]
        for param in required_params:
            if param not in self.params:
                raise KeyError(f"Missing required parameter: {param}")

    def get_strategy(self):
        return WeibullDispatchStrategy()

    def generate_random_dispatch_info(self) -> List[Tuple[float, int]]:
        # TODO: Implement Weibull schedule dispatch info generation
        pass


class EmpiricalSchedule(BaseSchedule):
    def __init__(self, params_path, start_time_of_day: int, end_time_of_day: int):
        super().__init__(params_path, start_time_of_day, end_time_of_day)
        self.validate_params()

    def validate_params(self):
        required_params = [
            "cleaned_data_filepath",
        ]
        for param in required_params:
            if param not in self.params:
                raise KeyError(f"Missing required parameter: {param}")

    def get_strategy(self):
        return EmpiricalDispatchStrategy()

    def generate_random_dispatch_info(self) -> List[Tuple[float, int]]:
        # TODO: Implement empirical schedule dispatch info generation
        pass

    def filter_and_group_data(self, station: str):
        # TODO: Implement data filtering and grouping based on station
        pass
