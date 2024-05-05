from abc import ABC, abstractmethod


class DispatchStrategy(ABC):
    @abstractmethod
    def generate_dispatch_info(self):
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
    def generate_dispatch_info(self, *args, **kwargs):
        # TODO: Implement empirical dispatch info generation
        pass
