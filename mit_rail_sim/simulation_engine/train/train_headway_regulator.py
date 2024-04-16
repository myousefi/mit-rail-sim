from __future__ import annotations

from typing import TYPE_CHECKING

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
        time_to_following_train = following_train.current_block.headway - time_to_leading_train

        if time_to_following_train < time_to_leading_train / 2:
            time_to_leading_train = -time_to_following_train

            following_train = following_train.path.get_previous_train(
                following_train.current_block_index
            )
            time_to_following_train = following_train.current_block.headway - time_to_leading_train

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
        time_to_leading_train = (
            train.simulation.current_time - train.next_block.last_train_visit_time
        )
        following_train = train.path.get_previous_train(train.current_block_index)
        time_to_following_train = following_train.current_block.headway - time_to_leading_train

        print(
            f"for Train: {train.train_id} Time to leading train: {time_to_leading_train}, time to following train: {time_to_following_train}"
        )

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
