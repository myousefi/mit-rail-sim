import json
from abc import ABC, abstractmethod
from typing import List, Tuple

from scipy.stats import gamma, weibull_min


class BaseSchedule(ABC):
    def __init__(self, params_path):
        self.params = self.read_params(params_path)
        self.dispatch_strategy = self.get_strategy()

    def read_params(self, path):
        try:
            with open(path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {path} was not found.")
        except json.JSONDecodeError:
            raise json.JSONDecodeError(f"Could not decode JSON from the file {path}.")

    @abstractmethod
    def get_strategy(self):
        pass

    @abstractmethod
    def generate_random_dispatch_info(self):
        pass

    # TODO: Implement copy method
    def copy(self):
        pass


class DispatchStrategy(ABC):
    @abstractmethod
    def generate_dispatch_info(self, params):
        pass


class GammaDispatchStrategy(DispatchStrategy):
    def generate_dispatch_info(self, params):
        # TODO: Implement gamma dispatch info generation
        pass


class WeibullDispatchStrategy(DispatchStrategy):
    def generate_dispatch_info(self, params):
        # TODO: Implement Weibull dispatch info generation
        pass


class EmpiricalDispatchStrategy(DispatchStrategy):
    def generate_dispatch_info(self, params):
        # TODO: Implement empirical dispatch info generation
        pass


class GammaSchedule(BaseSchedule):
    def __init__(self, params_path):
        super().__init__(params_path)
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
    def __init__(self, params_path):
        super().__init__(params_path)
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


class OHareEmpiricalSchedule(BaseSchedule):
    def __init__(self, params_path):
        super().__init__(params_path)
        self.validate_params()

    def validate_params(self):
        required_params = [
            "file_path",
            "start_time_of_day",
            "end_time_of_day",
            "cta_day_type",
        ]
        for param in required_params:
            if param not in self.params:
                raise KeyError(f"Missing required parameter: {param}")

    def get_strategy(self):
        return EmpiricalDispatchStrategy()

    def generate_random_dispatch_info(self) -> List[Tuple[int, int, str]]:
        # TODO: Implement O'Hare empirical schedule dispatch info generation
        pass

    def filter_data(self, cta_day_type: str):
        # TODO: Implement data filtering based on CTA day type
        pass


class EmpiricalSchedule(BaseSchedule):
    def __init__(self, params_path):
        super().__init__(params_path)
        self.validate_params()

    def validate_params(self):
        required_params = [
            "cleaned_data_filepath",
            "start_time_of_day",
            "end_time_of_day",
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
