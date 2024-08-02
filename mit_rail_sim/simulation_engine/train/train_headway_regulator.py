from __future__ import annotations

from calendar import c
from json import load
import math
from turtle import st
from typing import TYPE_CHECKING

from mit_rail_sim.simulation_engine.infrastructure import station
from mit_rail_sim.simulation_engine.passenger import arrival_rate

if TYPE_CHECKING:
    from mit_rail_sim.simulation_engine.infrastructure import Path
    from mit_rail_sim.simulation_engine.train import Train


class TrainHeadwayRegulator:
    def __init__(self):
        pass
        # self.max_holding = self.max_holding

    def suggested_holding(self, train: Train) -> float:
        time_to_leading_train = (
            train.simulation.current_time - train.next_block.last_train_visit_time
        )
        following_train = train.path.get_previous_train(train.current_block_index)
        time_to_following_train = (
            following_train.current_block.headway - time_to_leading_train
        )

        if time_to_following_train < time_to_leading_train / 2:
            time_to_leading_train = -time_to_following_train

            following_train = following_train.path.get_previous_train(
                following_train.current_block_index
            )
            time_to_following_train = (
                following_train.current_block.headway - time_to_leading_train
            )

        print(
            f"for Train: {train.train_id} Time to leading train: {time_to_leading_train}, time to following train: {time_to_following_train}"
        )

        if time_to_leading_train > time_to_following_train:
            return 0
        else:
            return (time_to_following_train - time_to_leading_train) / 2


class TrainHeadwayRegulatorAtStation:
    def __init__(self, max_holding=120, min_holding=30):
        self.max_holding = max_holding
        self.min_holding = min_holding

    def suggested_holding(self, train: Train) -> float:
        leading_train_id = train.next_block.id_of_last_train
        time_to_leading_train = (
            train.simulation.current_time - train.next_block.last_train_visit_time
            # train.next_block.headway
        )
        try:
            following_train = train.path.get_previous_train(train.current_block_index)
            if following_train.next_block.id_of_last_train == train.train_id:
                time_to_following_train = (
                    train.simulation.current_time
                    - following_train.next_block.last_train_visit_time
                )

            elif following_train.next_block.id_of_last_train == leading_train_id:
                time_to_following_train = (
                    train.simulation.current_time
                    - following_train.next_block.last_train_visit_time
                    - time_to_leading_train
                )
            else:
                Warning(
                    f"Train seuqence error for train {train.train_id} at block {train.next_block.block_alt_name} at time {train.simulation.current_time}"
                )
                return 0

            print(
                f"for Train: {train.train_id} Time to leading train: {time_to_leading_train}, time to following train: {time_to_following_train}"
            )
        except AttributeError as e:
            print(e)
            return 0

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


class TrainHeadwayRegulatorAtStationInformedByCrowding(TrainHeadwayRegulatorAtStation):
    def __init__(self, max_holding=120, min_holding=30):
        super().__init__(max_holding, min_holding)

    def suggested_holding(self, train: Train) -> float:
        suggested_holding = super().suggested_holding(train)

        stops = train.get_all_stops_ahead()

        denied_boardings = sum(len(stop.sorted_passenger_queue) for stop in stops)

        print(
            [
                f"There are {len(stop.sorted_passenger_queue)} passengers waiting at stop {stop.name} {stop.direction}"
                for stop in stops
                if stop.sorted_passenger_queue
            ]
        )

        if denied_boardings == 0:
            return suggested_holding
        else:
            return 0


class TrainHeadwayRegulatorWithLoadBalancingAndExactKnowledge(
    TrainHeadwayRegulatorAtStation
):
    def __init__(self, critical_station_name: str, max_holding=120, min_holding=30):
        super().__init__(max_holding, min_holding)
        self.critical_station_name = critical_station_name

    def suggested_holding(self, train: Train) -> float:
        current_station = train.current_block.station
        direction = train.path.direction
        current_hour = train.simulation.get_current_hour()
        current_weekday = train.simulation.is_weekday()

        arrival_rate = train.current_block.station.passenger_generator.arrival_rate

        weighted_avg_arrival_rate = arrival_rate.get_lambda_bar(
            current_hour,
            current_weekday,
            current_station.name,
            self.critical_station_name,
            direction,
        )

        weighted_avg_arrival_rate = (
            weighted_avg_arrival_rate / 3600
        )  # convert to per second

        passenger_retention_rate = arrival_rate.get_a_i(
            current_hour,
            current_weekday,
            current_station.name,
            self.critical_station_name,
            direction,
        )

        leading_train_id = train.next_block.id_of_last_train
        current_headway = (
            train.simulation.current_time - train.next_block.last_train_visit_time
        )

        following_train = train.path.get_previous_train(train.current_block_index)

        if following_train:
            if following_train.next_block.id_of_last_train == train.train_id:
                following_headway = (
                    train.simulation.current_time
                    - following_train.next_block.last_train_visit_time
                )
                load_picking_headway = following_headway
            elif following_train.next_block.id_of_last_train == leading_train_id:
                following_headway = (
                    train.simulation.current_time
                    - following_train.next_block.last_train_visit_time
                    - current_headway
                )
                load_picking_headway = following_headway + current_headway
            else:
                print(
                    f"Train sequence error for train {train.train_id} at block {train.next_block.block_alt_name} at time {train.simulation.current_time}"
                )
                return 0
        else:
            print(
                f"Follwing train not found for train {train.train_id} at block {train.next_block.block_alt_name} at time {train.simulation.current_time} holding time set to max: {self.max_holding}"
            )
            return self.max_holding

        sum_headways = current_headway + following_headway

        current_train_load = train.passenger_manager.total_passengers
        following_train_load = (
            following_train.passenger_manager.total_passengers if following_train else 0
        )

        stations_ahead_of_following_train = following_train.get_all_stops_ahead()

        for station in stations_ahead_of_following_train:
            if station == current_station:
                break
            following_train_load += (
                arrival_rate.get_lambda_for_station(
                    current_hour=current_hour,
                    current_weekday=current_weekday,
                    station=station.name,
                    direction=direction,
                )
                # * following_headway
                * load_picking_headway  # Note that the headway experienced at stations before UIC-Halsted is the load_picking_headway
                // 3600
            )

        target_headway = (
            passenger_retention_rate * (following_train_load - current_train_load)
        ) / (2 * weighted_avg_arrival_rate) + sum_headways / 2

        if target_headway <= current_headway or math.isnan(target_headway):
            return 0  # Dispatch immediately
        else:
            holding_time = min(target_headway - current_headway, self.max_holding)
            if holding_time < self.min_holding:
                return 0
            return holding_time


class TrainHeadwayRegulatorWithEstimatedLoads(TrainHeadwayRegulatorAtStation):
    def __init__(self, critical_station_name: str, max_holding=120, min_holding=30):
        super().__init__(max_holding, min_holding)
        self.critical_station_name = critical_station_name

    def suggested_holding(self, train: Train) -> float:
        current_station = train.current_block.station
        direction = train.path.direction
        current_hour = train.simulation.get_current_hour()
        current_weekday = train.simulation.is_weekday()

        arrival_rate = train.current_block.station.passenger_generator.arrival_rate

        weighted_avg_arrival_rate = arrival_rate.get_lambda_bar(
            current_hour,
            current_weekday,
            current_station.name,
            self.critical_station_name,
            direction,
        )

        weighted_avg_arrival_rate = (
            weighted_avg_arrival_rate / 3600
        )  # convert to per second

        passenger_retention_rate = arrival_rate.get_a_i(
            current_hour,
            current_weekday,
            current_station.name,
            self.critical_station_name,
            direction,
        )

        current_headway = (
            train.simulation.current_time - train.next_block.last_train_visit_time
        )

        leading_train_id = train.next_block.id_of_last_train

        following_train = train.path.get_previous_train(train.current_block_index)

        if following_train:
            if following_train.next_block.id_of_last_train == train.train_id:
                following_headway = (
                    train.simulation.current_time
                    - following_train.next_block.last_train_visit_time
                )
                load_picking_headway = following_headway
            elif following_train.next_block.id_of_last_train == leading_train_id:
                following_headway = (
                    train.simulation.current_time
                    - following_train.next_block.last_train_visit_time
                    - current_headway
                )
                load_picking_headway = following_headway + current_headway
            else:
                print(
                    f"Train sequence error for train {train.train_id} at block {train.next_block.block_alt_name} at time {train.simulation.current_time}"
                )
                return 0
        else:
            print(
                f"Follwing train not found for train {train.train_id} at block {train.next_block.block_alt_name} at time {train.simulation.current_time} holding time set to max: {self.max_holding}"
            )
            return self.max_holding

        sum_headways = current_headway + following_headway

        # Assuming current train load at current station is 0 if short-turning otherwise use the estimated load
        if train.has_been_short_turned:
            L_0_n = 0
        else:
            L_0_n = self.estimate_following_train_load(
                train, following_train_headway=current_headway
            )
        L_0_n_plus_1 = self.estimate_following_train_load(
            train, following_train_headway=load_picking_headway
        )

        target_headway = (passenger_retention_rate * (L_0_n_plus_1 - L_0_n)) / (
            2 * weighted_avg_arrival_rate
        ) + sum_headways / 2

        if target_headway <= current_headway or math.isnan(target_headway):
            return 0  # Dispatch immediately
        else:
            holding_time = min(target_headway - current_headway, self.max_holding)
            if holding_time < self.min_holding:
                return 0
            return holding_time

    def calculate_following_headway(
        self, train: Train, following_train: Train
    ) -> float:
        # Implement the logic to calculate the following headway
        pass

    def estimate_following_train_load(
        self, train: Train, following_train_headway: float
    ) -> float:
        current_station = train.current_block.station
        direction = train.path.direction

        arrival_rate = train.current_block.station.passenger_generator.arrival_rate

        stations = arrival_rate.get_all_previous_stops_for_station_and_direction(
            station=current_station.name, direction=direction
        )

        L_0_n_plus_1 = 0

        for station in stations:
            L_0_n_plus_1 += (
                arrival_rate.get_lambda_for_station(
                    current_hour=train.simulation.get_current_hour(),
                    current_weekday=train.simulation.is_weekday(),
                    station=station,
                    direction=direction,
                )
                * following_train_headway
                // 3600
            ) * arrival_rate.get_a_i(
                current_hour=train.simulation.get_current_hour(),
                current_weekday=train.simulation.is_weekday(),
                start_station=station,
                critical_station=current_station.name,
                direction=direction,
            )

        return L_0_n_plus_1
