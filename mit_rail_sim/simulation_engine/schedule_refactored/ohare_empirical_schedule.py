import json
from typing import List, Tuple

import pandas as pd

from mit_rail_sim.simulation_engine.schedule_refactored import BaseSchedule
from mit_rail_sim.simulation_engine.schedule_refactored import EmpiricalDispatchStrategy
from mit_rail_sim.simulation_engine.train import Train


class OHareEmpiricalSchedule(BaseSchedule):
    def __init__(self, file_path, start_time_of_day: int, end_time_of_day: int):
        super().__init__(file_path, start_time_of_day, end_time_of_day)

        with open(self.file_path, "r") as file:
            self.data = json.load(file)

        self.validate_params()

        self.dispatch_strategy = self.get_strategy()

        self.dispatch_info = self.dispatch_strategy.generate_random_dispatch_info()

        print("OHareEmpiricalSchedule initialized")

    def validate_params(self):
        if "empirical_schedule" not in self.data:
            raise ValueError("Empirical schedule data not found in params file")
        if "blue_line_schedule" not in self.data:
            raise ValueError("Blue line schedule data not found in params file")

    def get_strategy(self):
        return OHareEmpiricalDispatchStrategy(self)

    def generate_random_dispatch_info(self):
        self.scheduled_forest_park_departures: List[Tuple[float, int, str, str]] = [
            (
                scheduled_dispatch["time_in_sec"],
                0,
                "Northbound"
                if not scheduled_dispatch["short_turned"]
                else "Notimplemented",
                scheduled_dispatch["runid"],
            )
            for scheduled_dispatch in self.data["blue_line_schedule"]
            if scheduled_dispatch["terminal"] == "Forest Park"
        ]

        self.dispatch_info = self.dispatch_strategy.generate_random_dispatch_info()
        return self.dispatch_info

    def remove_all_northbound_trains(self) -> None:
        """Remove all northbound trains from the schedule."""
        self.dispatch_info = [
            dispatch_info
            for dispatch_info in self.dispatch_info
            if dispatch_info[2] != "Northbound"
        ]

    def adjust_next_departure(
        self,
        arrival_time: int,
        arriving_train: Train,
        arriving_to_dispatch_margin: int = 120,
    ) -> None:
        """Adjust the next departure time based on the arrival time of the arriving train."""
        import bisect

        if arriving_train.path.direction == "Southbound":
            while self.scheduled_forest_park_departures[0][0] < arrival_time:
                self.scheduled_forest_park_departures.pop(0)

            next_scheduled_departure = self.scheduled_forest_park_departures.pop(0)

            departure_time = max(
                arrival_time + arriving_to_dispatch_margin,
                next_scheduled_departure[0],
            )

            bisect.insort(
                self.dispatch_info,
                tuple((departure_time, *next_scheduled_departure[1:])),
                key=lambda x: x[0],
            )


class OHareEmpiricalDispatchStrategy(EmpiricalDispatchStrategy):
    def __init__(self, schedule: OHareEmpiricalSchedule) -> None:
        self.start_time_of_day = schedule.start_time_of_day
        self.end_time_of_day = schedule.end_time_of_day

        self.empirical_schedule_data = pd.DataFrame(schedule.data["empirical_schedule"])
        self.blue_line_schedule_data = pd.DataFrame(schedule.data["blue_line_schedule"])

        merged_data = pd.merge_asof(
            self.empirical_schedule_data,
            self.blue_line_schedule_data,
            on="time_in_sec",
            # by="runid",
            direction="nearest",
        )

        self.empirical_schedule_data["short_turned"] = merged_data["short_turned"]

        self.empirical_schedule_data = self.empirical_schedule_data[
            self.empirical_schedule_data["time_in_sec"].between(
                self.start_time_of_day, self.end_time_of_day
            )
        ]

        self.blue_line_schedule_data = self.blue_line_schedule_data[
            self.blue_line_schedule_data["time_in_sec"].between(
                self.start_time_of_day, self.end_time_of_day
            )
        ]

    def generate_random_dispatch_info(self) -> List[Tuple[int, int, str, str]]:
        dispatch_info = []

        for direction in self.empirical_schedule_data["direction"].unique():
            i = 0
            schedule = self.blue_line_schedule_data[
                self.blue_line_schedule_data["terminal"]
                == ("O-Hare" if direction == "Southbound" else "Forest Park")
            ]
            current_time = self.start_time_of_day
            data = self.empirical_schedule_data[
                self.empirical_schedule_data["direction"] == direction
            ]
            while current_time < self.end_time_of_day:
                # Filter empirical data for the current 15-minute interval
                current_interval_data = data[
                    (data["time_in_sec"] >= current_time)
                    & (
                        data["time_in_sec"] < current_time + 900
                    )  # 900 seconds = 15 minutes
                ]

                # Calculate the IQR for headway in the current interval
                q1 = current_interval_data["headway"].quantile(0.25)
                q3 = current_interval_data["headway"].quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 3.0 * iqr
                upper_bound = q3 + 3.0 * iqr

                # Filter out outliers based on the IQR
                current_interval_data = current_interval_data[
                    (current_interval_data["headway"] >= lower_bound)
                    & (current_interval_data["headway"] <= upper_bound)
                ]

                if not current_interval_data.empty:
                    # Sample a headway from the current interval
                    sample_dispatch = current_interval_data.sample(n=1)

                    current_time += sample_dispatch["headway"].values[0]
                    runid = sample_dispatch["runid"].values[0]
                    short_turned = sample_dispatch["short_turned"].values[0]

                    try:
                        path = (
                            "ShortTurning"
                            if schedule.iloc[i]["short_turned"]
                            else direction
                        )
                        i += 1
                    except IndexError:
                        path = direction

                    dispatch_info.append((current_time, 0, path, runid))
                else:
                    current_time += 900  # Move to the next 15-minute interval

        dispatch_info.sort(key=lambda x: x[0])

        return dispatch_info


import json
from typing import List, Tuple

import pandas as pd

from mit_rail_sim.simulation_engine.schedule_refactored import BaseSchedule
from mit_rail_sim.simulation_engine.schedule_refactored import EmpiricalDispatchStrategy
from mit_rail_sim.simulation_engine.train import Train


class OHareEmpiricalScheduleWithHolding(OHareEmpiricalSchedule):
    def __init__(
        self,
        file_path,
        start_time_of_day: int,
        end_time_of_day: int,
        max_holding=180,
        min_holding=60,
    ):
        super().__init__(file_path, start_time_of_day, end_time_of_day)
        self.max_holding = max_holding
        self.min_holding = min_holding

    def generate_random_dispatch_info(self):
        dispatch_info = super().generate_random_dispatch_info()

        # Apply holding logic to adjust dispatch times for Southbound trains
        adjusted_dispatch_info = []
        southbound_dispatch_info = [
            dispatch
            for dispatch in dispatch_info
            if (dispatch[2] == "Southbound" or dispatch[2] == "ShortTurning")
        ]

        for i in range(len(southbound_dispatch_info)):
            current_dispatch = southbound_dispatch_info[i]
            current_time, block_index, path, runid = current_dispatch

            if i > 0:
                prev_dispatch = southbound_dispatch_info[i - 1]
                prev_time, _, _, _ = prev_dispatch
                time_to_leading_train = current_time - prev_time
            else:
                time_to_leading_train = float("inf")

            if i < len(southbound_dispatch_info) - 1:
                next_dispatch = southbound_dispatch_info[i + 1]
                next_time, _, _, _ = next_dispatch
                time_to_following_train = next_time - current_time
            else:
                time_to_following_train = float("inf")

            holding_time = self.suggested_holding(
                time_to_leading_train, time_to_following_train
            )
            adjusted_time = current_time + holding_time

            self.ohare_terminal_holding_logger.log_terminal_holding(
                self.replication_id,
                current_time,
                adjusted_time,
                holding_time,
                runid,
            )

            adjusted_dispatch_info.append((adjusted_time, block_index, path, runid))

        # Combine adjusted Southbound dispatch info with Northbound dispatch info
        northbound_dispatch_info = [
            dispatch for dispatch in dispatch_info if dispatch[2] == "Northbound"
        ]
        combined_dispatch_info = adjusted_dispatch_info + northbound_dispatch_info
        combined_dispatch_info.sort(key=lambda x: x[0])

        self.dispatch_info = combined_dispatch_info
        return combined_dispatch_info

    def suggested_holding(
        self, time_to_leading_train: float, time_to_following_train: float
    ) -> float:
        if time_to_leading_train > time_to_following_train:
            return 0
        else:
            holding_time = min(
                (time_to_following_train - time_to_leading_train) / 2, self.max_holding
            )
            if holding_time < self.min_holding:
                return 0
            else:
                return holding_time
