import bisect
import json
import random
from copy import deepcopy
from typing import List, Tuple

import scipy.stats as st

from mit_rail_sim.utils import project_root


class Schedule:
    # TODO work on the schedule representation
    def __init__(
        self,
        num_trains: int,
        headway: float,
        random_range: Tuple[float, float],
    ):
        self.num_trains = num_trains
        self.headway = headway
        self.random_range = random_range
        self.alternate_start_block_index = alternate_start_block_index
        self.generate_random_dispatch_info()

    def generate_random_dispatch_info(self) -> List[Tuple[float, int, str]]:
        dispatch_info = []

        starting_block_index = 0
        for i in range(1, self.num_trains):
            random_offset = random.uniform(*self.random_range)
            dispatch_info.append(
                (self.headway * i + random_offset, starting_block_index, "Northbound")
            )

        for i in range(1, self.num_trains):
            random_offset = random.uniform(*self.random_range)
            dispatch_info.append(
                (self.headway * i + random_offset, starting_block_index, "Southbound")
            )

        self.dispatch_info = sorted(dispatch_info, key=lambda x: x[0])

        return dispatch_info

    def copy(self):
        return deepcopy(self)


class GammaSchedule:
    def __init__(
        self,
        num_trains: int,
        mean: float,
        cv: float,
    ):
        self.num_trains = num_trains
        self.mean = mean
        self.coeff_var = cv

        self.generate_random_dispatch_info()

    def get_gamma_params(self, mean, coeff_var):
        shape = (1 / coeff_var) ** 2
        scale = mean / shape
        return shape, scale

    def remove_all_northbound_trains(self):
        raise NotImplementedError

    def generate_random_dispatch_info(self) -> List[Tuple[float, int]]:
        dispatch_info = []
        if self.coeff_var == 0:  # special case where CV = 0
            samples = [self.mean for _ in range(self.num_trains)]
        else:
            shape, scale = self.get_gamma_params(self.mean, self.coeff_var)
            samples = st.gamma.rvs(shape, scale=scale, size=self.num_trains)
        current_time = 0.0
        starting_block_index = 0
        for headway in samples:
            current_time += headway
            dispatch_info.append((current_time, starting_block_index))
        self.dispatch_info = dispatch_info
        return dispatch_info


class GammaScheduleWithShortTurningTwoTerminals(GammaSchedule):
    forest_park_departures = [
        10800,
        12000,
        13200,
        14400,
        15300,
        16200,
        17100,
        18000,
        18900,
        19800,
        20520,
        21240,
        21960,
        22680,
        23400,
        24000,
        24600,
        25200,
        25800,
        26400,
        27000,
        27600,
        28200,
        28800,
        29400,
        30000,
        30600,
        31200,
        31800,
        32400,
        33000,
        33600,
        34200,
        34920,
        35640,
        36360,
        37080,
        37800,
        38520,
        39240,
        39960,
        40680,
        41400,
        42120,
        42840,
        43560,
        44280,
        45000,
        45720,
        46440,
        47160,
        47880,
        48600,
        49200,
        49800,
        50400,
        51000,
        51540,
        51900,
        52500,
        53100,
        53700,
        54300,
        55140,
        55800,
        56400,
        57000,
        57360,
        58080,
        58440,
        59160,
        59520,
        60240,
        60600,
        61080,
        61500,
        62100,
        62700,
        63300,
        63900,
        64500,
        65100,
        65700,
        66300,
        66900,
        67500,
        68100,
        68700,
        69300,
        69900,
        70500,
        71100,
        71700,
        72300,
        72900,
        73500,
        74100,
        74700,
        75300,
        75900,
        76500,
        77100,
        77700,
        78300,
        78900,
        79500,
        80100,
        80700,
        81300,
        81900,
        82800,
        83700,
        84600,
        85500,
        86400,
        87600,
        88800,
        90000,
        91800,
        93600,
        95400,
    ]

    def __init__(
        self,
        total_period: int,
        sb_mean: float,
        sb_cv: float,
        nb_mean: float,
        nb_cv: float,
        short_turning_rate: int,
        start_hour_of_day: int = 14,
    ):
        self.total_period = total_period
        self.sb_mean = sb_mean * 60
        self.sb_coeff_var = sb_cv
        self.nb_mean = nb_mean * 60
        self.nb_coeff_var = nb_cv
        self.short_turning_rate = short_turning_rate
        self.start_hour_of_day = start_hour_of_day

        self.generate_random_dispatch_info()

    def adjust_next_departure(self, arrival_time, direction, path, dispatch_margin=120):
        if direction == "Northbound":
            insertion_point = bisect.bisect_right(
                GammaScheduleWithShortTurningTwoTerminals.forest_park_departures,
                arrival_time,
            )

            next_departure_based_on_schedule = (
                GammaScheduleWithShortTurningTwoTerminals[insertion_point]
            )

            next_departure_based_on_arrival = arrival_time + dispatch_margin
            next_departure = max(
                next_departure_based_on_schedule, next_departure_based_on_arrival
            )
            dispatch = (next_departure, 0, "Northbound")
            bisect.insort(self.dispatch_info, dispatch, key=lambda x: x[0])

    def get_gamma_params(self, mean, coeff_var):
        shape = (1 / coeff_var) ** 2
        scale = mean / shape
        return shape, scale

    def gen_random_dispatch_info_sb(self) -> List[Tuple[float, int, str]]:
        dispatch_info = []
        if self.sb_coeff_var == 0:
            samples = [self.sb_mean for _ in range(self.total_period // self.sb_mean)]
        else:
            shape, scale = self.get_gamma_params(self.sb_mean, self.sb_coeff_var)
            samples = st.gamma.rvs(shape, scale=scale, size=1000)

        current_time = 0.0
        for headway in samples:
            current_time += headway
            dispatch_info.append((current_time, 0, "Southbound"))
            if current_time >= self.total_period:
                break

        if self.short_turning_rate != 0:
            for i, (time, number, direction) in enumerate(dispatch_info):
                if direction == "Southbound" and (i % self.short_turning_rate == 0):
                    dispatch_info[i] = (time, number, "ShortTurning")

        return dispatch_info

    def gen_random_dispatch_info_nb(self) -> List[Tuple[float, int, str]]:
        dispatch_info = []
        if self.nb_coeff_var == 0:
            samples = [self.nb_mean for _ in range(self.total_period // self.nb_mean)]
        else:
            shape, scale = self.get_gamma_params(self.nb_mean, self.nb_coeff_var)
            samples = st.gamma.rvs(shape, scale=scale, size=1000)

        current_time = 0.0
        for headway in samples:
            current_time += headway
            dispatch_info.append((current_time, 0, "Northbound"))
            if current_time >= self.total_period:
                break

        return dispatch_info

    def generate_random_dispatch_info(self) -> None:
        dispatch_info = []
        dispatch_info += self.gen_random_dispatch_info_sb()
        dispatch_info += self.gen_random_dispatch_info_nb()

        dispatch_info.sort(key=lambda x: x[0])

        dispatch_info = [
            (dispatch_time + self.start_hour_of_day * 3600, block_index, direction)
            for dispatch_time, block_index, direction in dispatch_info
        ]

        self.dispatch_info = dispatch_info


class GammaScheduleWithShortTurningTwoTerminalsPMPeak(
    GammaScheduleWithShortTurningTwoTerminals
):
    # ...

    def __init__(
        self,
        total_period: int,
        nb_mean: float,
        nb_cv: float,
        short_turning_rate: int,
        start_hour_of_day: int = 14,
    ):
        self.total_period = total_period
        self.path_to_params = project_root / "inputs" / "pm_peak_gamma_parameters.json"

        with open(self.path_to_params, "r") as file:
            self.params = json.load(file)

        self.nb_mean = nb_mean
        self.nb_coeff_var = nb_cv
        self.short_turning_rate = short_turning_rate
        self.start_hour_of_day = start_hour_of_day
        self.generate_random_dispatch_info()

    def remove_all_northbound_trains(self):
        self.dispatch_info = [t for t in self.dispatch_info if t[2] == "Southbound"]

    def gen_random_dispatch_info_sb(self) -> List[Tuple[float, int, str]]:
        dispatch_info = []

        samples_5 = list(
            st.gamma.rvs(
                self.params["hdw_5"]["shape"],
                loc=self.params["hdw_5"]["loc"],
                scale=self.params["hdw_5"]["scale"],
                size=1000,
            )
            * 60
        )
        samples_10 = list(
            st.gamma.rvs(
                self.params["hdw_10"]["shape"],
                loc=self.params["hdw_10"]["loc"],
                scale=self.params["hdw_10"]["scale"],
                size=1000,
            )
            * 60
        )

        current_time = 0.0

        while current_time < self.total_period:
            headway = samples_5.pop()
            current_time += headway

            dispatch_info.append((current_time, 0, "ShortTurning"))

            headway = samples_5.pop()
            current_time += headway

            dispatch_info.append((current_time, 0, "Southbound"))

            headway = samples_10.pop()
            current_time += headway

            dispatch_info.append((current_time, 0, "Southbound"))

        return dispatch_info

    def gen_random_dispatch_info_nb(self) -> List[Tuple[float, int, str]]:
        dispatch_info = []
        if self.nb_coeff_var == 0:
            samples = [self.nb_mean for _ in range(self.total_period // self.nb_mean)]
        else:
            shape, scale = self.get_gamma_params(self.nb_mean, self.nb_coeff_var)
            samples = st.gamma.rvs(shape, scale=scale, size=1000)

        current_time = 0.0
        for headway in samples:
            current_time += headway
            dispatch_info.append((current_time, 0, "Northbound"))
            if current_time >= self.total_period:
                break

        return dispatch_info


class GammaScheduleWithShortTurning(GammaSchedule):
    def __init__(
        self,
        total_period: int,
        mean: float,
        cv: float,
        short_turning_rate: int,
    ):
        self.total_period = total_period
        self.mean = mean
        self.coeff_var = cv
        self.short_turning_rate = short_turning_rate

        self.generate_random_dispatch_info()

    def get_gamma_params(self, mean, coeff_var):
        shape = (1 / coeff_var) ** 2
        scale = mean / shape
        return shape, scale

    def generate_random_dispatch_info(self) -> List[Tuple[float, int]]:
        dispatch_info = []
        if self.coeff_var == 0:  # special case where CV = 0
            samples = [self.mean for _ in range(self.total_period // self.mean)]
        else:
            shape, scale = self.get_gamma_params(self.mean, self.coeff_var)
            samples = st.gamma.rvs(shape, scale=scale, size=1000)

        for direction in ["Northbound", "Southbound"]:
            current_time = 0.0
            for headway in samples:
                current_time += headway
                dispatch_info.append((current_time, 0, direction))
                if current_time >= self.total_period:
                    break

        if self.short_turning_rate != 0:
            for i, (time, number, direction) in enumerate(dispatch_info):
                if direction == "Southbound" and (i % self.short_turning_rate == 0):
                    dispatch_info[i] = (time, number, "ShortTurning")

        dispatch_info.sort(key=lambda x: x[0])
        self.dispatch_info = dispatch_info
        return dispatch_info


class WeibullSchedule:
    def __init__(
        self,
        num_trains: int,
        path_to_params_json_file: str,
    ):
        self.num_trains = num_trains
        self.path_to_params_json_file = path_to_params_json_file

        # read parameters from a file
        with open(self.path_to_params_json_file, "r") as f:
            self.params = json.load(f)

        self.generate_random_dispatch_info()

    def generate_random_dispatch_info(self) -> List[Tuple[float, int]]:
        dispatch_info = []
        samples = st.weibull_min.rvs(*self.params, size=self.num_trains)
        current_time = 0.0
        for _, headway in enumerate(samples):
            current_time += headway * 60
            starting_block_index = 0
            dispatch_info.append((current_time, starting_block_index))
        self.dispatch_info = dispatch_info
        return dispatch_info

    def copy(self):
        return deepcopy(self)


from typing import List, Tuple

import pandas as pd


class OHareEmpiricalSchedule:
    def __init__(
        self,
        file_path: str,
        start_time_of_day: int,
        end_time_of_day: int,
        cta_day_type: str,
    ):
        # self.file_path = file_path
        self.start_time_of_day = start_time_of_day
        self.end_time_of_day = end_time_of_day

        self.data = pd.read_csv(file_path)

        self.data["event_time"] = pd.to_datetime(self.data["event_time"])

        self.grouped_data = self.filter_data(cta_day_type)

        self.generate_random_dispatch_info()

        print("OHareEmpiricalSchedule initialized")

    def filter_data(self, cta_day_type: str):
        if cta_day_type == "Weekday":
            self.data = self.data[self.data["event_time"].dt.dayofweek < 5]
        elif cta_day_type == "Saturday":
            self.data = self.data[self.data["event_time"].dt.dayofweek == 5]
        elif cta_day_type == "Sunday":
            self.data = self.data[self.data["event_time"].dt.dayofweek == 6]
        else:
            raise ValueError(
                "Invalid CTA day type. Must be one of 'Weekday', 'Saturday', 'Sunday'"
            )

        self.data = self.data[
            (
                (self.data["event_time"].dt.hour >= self.start_time_of_day)
                & (self.data["event_time"].dt.hour < self.end_time_of_day)
            )
        ]

        headway_quantiles = self.data["headway"].quantile([0.10, 0.95])

        self.data = self.data[self.data["headway"].between(*headway_quantiles)]

        self.data["interval"] = self.data["event_time"].dt.floor("15min")
        self.data["interval"] = (
            self.data["interval"] - self.data["interval"].dt.normalize()
        )

        grouped_data = self.data.groupby(["interval", "qt2_trackid"])

        return grouped_data

    def generate_random_dispatch_info_ohare(self) -> List[Tuple[int, int, str]]:
        offset = pd.Timedelta(0, unit="h")
        current_time = pd.Timedelta(self.start_time_of_day, unit="h")
        end_time = pd.Timedelta(self.end_time_of_day, unit="h")
        dispatch_info = []

        while current_time < end_time:
            try:
                current_group = self.grouped_data.get_group(
                    (current_time.floor("15min"), 15020)
                )

            except KeyError:
                current_time += pd.Timedelta(minutes=15)
                continue

            if not current_group.empty:
                headway = pd.Timedelta(
                    current_group["headway"].sample(1).iloc[0], unit="m"
                )
                current_time += headway
                departure_time = (current_time).total_seconds()
                dispatch_info.append((departure_time, 0, "Southbound"))

        return dispatch_info

    def generate_random_dispatch_info_fp(self):
        offset = pd.Timedelta(0, unit="h")
        current_time = pd.Timedelta(self.start_time_of_day, unit="h")
        end_time = pd.Timedelta(self.end_time_of_day, unit="h")
        dispatch_info = []

        while current_time < end_time:
            try:
                current_group = self.grouped_data.get_group(
                    (current_time.floor("15min"), 11020)
                )

            except KeyError:
                current_time += pd.Timedelta(minutes=15)
                continue

            if not current_group.empty:
                headway = pd.Timedelta(
                    current_group["headway"].sample(1).iloc[0], unit="m"
                )
                current_time += headway
                departure_time = (current_time).total_seconds()
                dispatch_info.append((departure_time, 0, "Northbound"))

        return dispatch_info

    def generate_random_dispatch_info(self) -> List[Tuple[int, int, str]]:
        ohare = self.generate_random_dispatch_info_ohare()

        short_turning_count = 0
        max_short_turning_count = 6

        for i, (time, number, direction) in enumerate(ohare):
            if (
                6.5 * 3600 <= time
                and (i % 3 == 2)
                and short_turning_count < max_short_turning_count
            ):
                short_turning_count += 1
                ohare[i] = (time, number, "ShortTurning")

        fp = self.generate_random_dispatch_info_fp()

        dispatch_info = ohare + fp
        dispatch_info.sort(key=lambda x: x[0])

        dispatch_info = [
            (time - self.start_time_of_day * 3600, _, __)
            for time, _, __ in dispatch_info
        ]

        self.dispatch_info = dispatch_info

        return dispatch_info


class EmpiricalSchedule:
    def __init__(
        self, cleaned_data_filepath: str, start_time_of_day: int, end_time_of_day: int
    ):
        # TODO Try inverse transform sampling from the empricial cumulative distribution function or fit a theoretical distribution
        self.cleaned_data_filepath = cleaned_data_filepath
        self.start_time_of_day = pd.to_timedelta(f"{start_time_of_day}:00:00")
        self.end_time_of_day = pd.to_timedelta(f"{end_time_of_day}:00:00")

        # Load data
        self.data = pd.read_csv(cleaned_data_filepath)
        # Convert event_time to datetime, extract the time portion and convert it to timedelta
        self.data["event_time"] = pd.to_timedelta(
            pd.to_datetime(self.data["event_time"]).dt.strftime("%H:%M:%S")
        )

        # self.

        # Define departure times for UIC-Halsted
        departure_times = [
            "08:17",
            "08:40",
            "08:55",
            "09:10",
            "09:25",
            "09:40",
            "09:55",
            "10:10",
            "10:25",
            "10:40",
            "10:55",
            "11:10",
            "11:25",
            "11:40",
            "11:55",
            "12:10",
            "12:25",
            "12:40",
            "12:55",
            "13:10",
            "13:25",
            "13:40",
            "13:55",
            "14:10",
            "14:25",
            "14:40",
            "14:55",
            "15:10",
            "15:25",
            "15:40",
            "15:55",
            "16:10",
            "16:29",
            "16:41",
            "17:11",
            "17:41",
            "18:14",
            "18:44",
            "18:59",
            "19:10",
            "19:30",
            "19:50",
            "20:10",
            "20:30",
            "20:50",
            "21:10",
            "21:30",
            "21:50",
            "22:10",
            "22:30",
            "22:50",
            "23:10",
            "23:36",
            "23:56",
        ]
        # Ensure each timestamp has 'hh:mm:ss' format
        departure_times = [
            time if len(time.split(":")) == 3 else time + ":00"
            for time in departure_times
        ]

        self.uic_halsted_departure_times = [
            pd.to_timedelta(time) for time in departure_times
        ]

        self.dispatch_info = self.generate_random_dispatch_info()

    def filter_and_group_data(self, station: str):
        mask = (
            (self.data["event_time"] >= self.start_time_of_day)
            & (self.data["event_time"] <= self.end_time_of_day)
            & (self.data["station"] == station)
        )

        filtered_data = self.data[mask]

        if station == "UIC-Halsted":
            # Keep only short turning trips
            filtered_data = filtered_data[filtered_data["is_short_turning"] == 1.0]

        # Group by station and 15-minute intervals
        filtered_data["interval"] = filtered_data["event_time"].dt.floor("15min")

        headway_quantiles = filtered_data["headway"].quantile([0.05, 0.95])
        filtered_data = filtered_data[
            filtered_data["headway"].between(*headway_quantiles)
        ]

        grouped_data = filtered_data.groupby(["station", "interval"])

        # # Filter based on deviation and headway
        # def filter_outliers(group):
        #     # deviation_quantiles = group["deviation"].quantile([0.1, 0.9])
        #     headway_quantiles = group["headway"].quantile([0.05, 0.95])
        #     return group[
        #         # (group["deviation"].between(*deviation_quantiles))
        #         # &
        #         (group["headway"].between(*headway_quantiles))
        #     ]

        # filtered_data = grouped_data.apply(filter_outliers).reset_index(drop=True)

        return grouped_data

    # .groupby(["station", "interval"])

    def generate_forest_park_dispatch_info(self) -> List[Tuple[float, int]]:
        grouped_data = self.filter_and_group_data("LV Forest Park")

        offset = pd.Timedelta(0, unit="h")
        dispatch_info = []

        while self.start_time_of_day + offset < self.end_time_of_day:
            current_time = self.start_time_of_day + offset

            try:
                current_group = grouped_data.get_group(
                    ("LV Forest Park", current_time.floor("15min"))
                )
            except KeyError:
                offset += pd.Timedelta(minutes=15)
                continue

            if not current_group.empty:
                headway = pd.Timedelta(
                    current_group["headway"].sample(1).iloc[0], unit="m"
                )
                departure_time = (offset + headway).total_seconds()
                dispatch_info.append(
                    (departure_time, 0, "Northbound")
                )  # 0 for Forest Park block index
                offset += headway

        return dispatch_info

    def generate_uic_halsted_dispatch_info(self) -> List[Tuple[float, int]]:
        # grouped_data = self.filter_and_group_data("UIC-Halsted")
        uic_data = self.data[self.data["station"] == "UIC-Halsted"]
        uic_data = uic_data[uic_data["is_short_turning"] == 1.0]

        dispatch_info = []

        for departure_time in self.uic_halsted_departure_times:
            if (
                departure_time < self.start_time_of_day
                or departure_time > self.end_time_of_day
            ):
                continue

            # Find entries within 10 minutes proximity of time from departure time
            lower_bound = departure_time - pd.Timedelta(minutes=10)
            upper_bound = departure_time + pd.Timedelta(minutes=10)

            # Filter the grouped_data based on proximity to departure time
            current_group = uic_data[
                (uic_data["event_time"] >= lower_bound)
                & (uic_data["event_time"] <= upper_bound)
            ]

            if not current_group.empty:
                sampled_row = current_group.sample(1)
                deviation = pd.to_timedelta(sampled_row["deviation"].iloc[0], unit="m")
            else:
                deviation = pd.Timedelta(0, unit="m")

            modified_departure_time = (
                departure_time + deviation - self.start_time_of_day
            )
            dt_seconds = modified_departure_time.total_seconds()
            dispatch_info.append(
                (dt_seconds, 79, "Northbound")
            )  # 1 for UIC-Halsted block index

        return dispatch_info

    def generate_random_dispatch_info(self) -> List[Tuple[float, int]]:
        forest_park_dispatch_info = self.generate_forest_park_dispatch_info()
        uic_halsted_dispatch_info = self.generate_uic_halsted_dispatch_info()

        combined_dispatch_info = forest_park_dispatch_info + uic_halsted_dispatch_info
        combined_dispatch_info.sort(key=lambda x: x[0])  # sort by departure time

        self.dispatch_info = combined_dispatch_info
        return combined_dispatch_info
