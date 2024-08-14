import os

import hydra
from omegaconf import DictConfig

from mit_rail_sim import config_handler
from mit_rail_sim.simulation_engine.passenger import ArrivalRate

from mit_rail_sim.simulation_engine.schedule_refactored.ohare_empirical_schedule import (
    OHareEmpiricalSchedule,
    OHareEmpiricalScheduleWithHolding,
)

# Import necessary modules from mit_rail_sim
from mit_rail_sim.simulation_engine.simulation import ReplicationManager
from mit_rail_sim.simulation_engine.utils import LoggerContext
from mit_rail_sim.simulation_engine.utils.logger_utils import (
    BlockActivationLogger,
    NullTrainLogger,
    OHareTerminalHoldingLogger,
    PassengerLogger,
    SimulationLogger,
    StationLogger,
    TrainLogger,
)
from mit_rail_sim.simulation_runner.loaders import (
    PathConfigLoader,
    read_slow_zones_from_json,
    load_data,
    create_path_from_data_with_offscan_symptom,
)

from mit_rail_sim.utils import project_root


@hydra.main(
    config_path=str(project_root / "load-balance"),
    config_name="config",
    version_base="1.3",
)
def main(cfg: DictConfig) -> None:
    config_handler.set_config(cfg)

    if cfg.station == "O-Hare":
        cfg.holding = False
        cfg.ohare_holding = True
    elif cfg.station == "Clark-Lake":
        cfg.station = "Clark/Lake"

    log_folder_path = cfg.log_folder_path

    print("Current working directory:", os.getcwd())
    print("Log folder path:", cfg.log_folder_path)

    train_logger = (
        TrainLogger(
            log_file_path=f"{log_folder_path}/train_test.csv",
            log_interval=cfg.logger.log_interval,
        )
        if cfg.logger.should_log_trajectories
        else NullTrainLogger()
    )

    passenger_logger = PassengerLogger(
        log_file_path=f"{log_folder_path}/passenger_test.csv"
    )
    station_logger = StationLogger(log_file_path=f"{log_folder_path}/station_test.csv")
    simulation_logger = SimulationLogger(
        log_file_path=f"{log_folder_path}/simulation_test.json"
    )
    block_logger = BlockActivationLogger(
        log_file_path=f"{log_folder_path}/block_test.csv"
    )

    ohare_terminal_holding_logger = OHareTerminalHoldingLogger(
        log_file_path=f"{log_folder_path}/ohare_terminal_holding_test.csv"
    )

    arrival_rates = ArrivalRate(
        # filename=str(
        #     project_root
        #     / "inputs"
        #     / "demand"
        #     / "odx_imputed_demand_2024-04-07_2024-05-30.csv"
        # ),
        filename=cfg.demand_file,
        demand_factor=cfg.demand_level,
    )

    data = load_data(project_root / "inputs" / "infra.json")

    slow_zones = read_slow_zones_from_json(project_root / "inputs" / "slow_zones.json")
    logger_context = LoggerContext(
        train_logger=train_logger,
        passenger_logger=passenger_logger,
        station_logger=station_logger,
        simulation_logger=simulation_logger,
        block_logger=block_logger,
        ohare_terminal_holding_logger=ohare_terminal_holding_logger,
        warmup_time=3600 * 1.5,
        start_hour_of_day=cfg.simulation.start_time_of_day,
    )

    # schedule = OHareEmpiricalSchedule(
    # file_path=project_root / "inputs" / "schedules" / "empirical_schedule_83.json",
    if cfg.ohare_holding:
        schedule = OHareEmpiricalScheduleWithHolding(
            file_path=cfg.schedule_file,
            start_time_of_day=cfg.simulation.start_time_of_day * 3600,
            end_time_of_day=cfg.simulation.end_time_of_day * 3600,
            max_holding=cfg.max_holding,
            min_holding=cfg.min_holding,
        )
    else:
        schedule = OHareEmpiricalSchedule(
            file_path=cfg.schedule_file,
            start_time_of_day=cfg.simulation.start_time_of_day * 3600,
            end_time_of_day=cfg.simulation.end_time_of_day * 3600,
        )
    # if schd := cfg.schd:
    #     if schd == "PM":
    #         schedule = GammaScheduleWithShortTurningTwoTerminalsPMPeak(
    #             nb_cv=0.35,
    #             nb_mean=11 * 60,
    #             short_turning_rate=2,
    #             total_period=6 * 3600,
    #             start_hour_of_day=cfg.simulation.start_time_of_day,
    #         )
    #     if schd == "Base":
    #         schedule = GammaScheduleWithShortTurningTwoTerminals(
    #             nb_cv=0.2,
    #             nb_mean=9,
    #             sb_cv=0.35,
    #             sb_mean=6,
    #             total_period=6 * 3600,
    #             short_turning_rate=3,
    #         )
    #     if schd == "Alt-H":
    #         schedule = GammaScheduleWithShortTurningTwoTerminals(
    #             nb_cv=0.2,
    #             nb_mean=11,
    #             sb_cv=0.35,
    #             sb_mean=5.5,
    #             total_period=6 * 3600,
    #             short_turning_rate=2,
    #         )
    #     elif schd == "Alt-L":
    #         schedule = GammaScheduleWithShortTurningTwoTerminals(
    #             nb_cv=0.2,
    #             nb_mean=12,
    #             sb_cv=0.35,
    #             sb_mean=6,
    #             total_period=6 * 3600,
    #             short_turning_rate=2,
    #         )

    replication_manager = ReplicationManager(
        number_of_replications=cfg.simulation.number_of_replications,
        logger_context=logger_context,
        train_speed_regulator="CTA",
    )

    from functools import partial

    path_config_laod = PathConfigLoader(
        path_config_file=project_root / "inputs" / "path_config.json"
    )
    fixed_arrival_rates_function = partial(
        create_path_from_data_with_offscan_symptom,
        arrival_rates=arrival_rates,
        path_config_loader=path_config_laod,
    )

    replication_manager.run_replications(
        schedule=schedule,
        path_initializer_function=fixed_arrival_rates_function,
        data=data,
        slow_zones=slow_zones,
        total_time=(cfg.simulation.end_time_of_day - cfg.simulation.start_time_of_day)
        * 3600,
        start_hour=cfg.simulation.start_time_of_day,
    )


if __name__ == "__main__":
    main()
