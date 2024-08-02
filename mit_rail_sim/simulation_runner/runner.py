# import imp
import json
import os
from random import randint
from typing import Dict, List, Tuple

import hydra
from omegaconf import DictConfig

from mit_rail_sim import config_handler
from mit_rail_sim.simulation_engine.infrastructure import (
    Block,
    Path,
    SignalControlCenter,
    SlowZone,
    Station,
)
from mit_rail_sim.simulation_engine.infrastructure.path import (
    ShortTurningAtWestern,
    ShortTurningPath,
)
from mit_rail_sim.simulation_engine.passenger import ArrivalRate
# from mit_rail_sim.simulation_engine.schedule import (
#     GammaScheduleWithShortTurning,
#     GammaScheduleWithShortTurningTwoTerminals,
#     GammaScheduleWithShortTurningTwoTerminalsPMPeak,
#     OHareEmpiricalSchedule,
# )

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


def read_slow_zones_from_json(file_path: str) -> List[SlowZone]:
    with open(file_path, "r") as file:
        slow_zones_data = json.load(file)
    return [SlowZone.from_dict(data) for data in slow_zones_data]


def load_data(data_filename: str):
    with open(data_filename, "r") as file:
        return json.load(file)


def create_path_from_data_with_offscan_symptom(
    data: Dict, slow_zones: List[SlowZone], arrival_rates: ArrivalRate
) -> Tuple[Dict[str, Path], SignalControlCenter]:
    # off_scans = []
    blocks = []
    paths = {}

    cfg = config_handler.get_config()

    for direction in ["Northbound", "Southbound"]:
        path_blocks = []
        for block_data in data[direction]:
            block_id = block_data["BLOCK"]
            block_alt_name = block_data["BLOCK_ALT"]
            visible_distance = randint(50, 1000)
            length = int(block_data["DISTANCE"])
            default_speed_code = min(block_data["SPEED"], 55)
            speed_codes_to_communicate = block_data["SPEED_CODES_TO_COMMUNICATE"]

            if "STATION" in block_data:
                station_data = block_data["STATION"]
                end_of_platform_milepost = int(station_data["END_OF_PLATFORM_MILEPOST"])
                start_stn = block_data["STARTSTN"]

                location_relative_to_block = abs(start_stn - end_of_platform_milepost)

                if location_relative_to_block < 0:
                    print(station_data["STATION_NAME"])

                station = Station(
                    station_name=station_data["STATION_NAME"],
                    location_relative_to_block=location_relative_to_block,
                    direction=direction,
                    arrival_rates=arrival_rates,
                )

            else:
                station = None

            block = Block(
                block_id=block_id,
                block_alt_name=block_alt_name,
                visible_distance=visible_distance,
                length=length,
                default_speed_code=default_speed_code,
                speed_codes_to_communicate=speed_codes_to_communicate,
                station=station,
            )

            blocks.append(block)
            path_blocks.append(block)

        paths[direction] = Path(direction, path_blocks, slow_zones=slow_zones)

    signal_control_center = SignalControlCenter(blocks)

    paths["Northbound"].make_dispatching_block(
        block_id="WC-470", dispatch_margin=0, upstream_blocks=["WC-470"]
    )

    paths["Northbound"].make_dispatching_block(
        block_id="WC-16",
        dispatch_margin=80,
        upstream_blocks=[
            "WC-35",
            "WC-32",
            "321",
            "WC-26",
            "WC-22",
            "311",
            "WC-16",
            # "WC-11",
            # "WC-8",
        ],
    )

    paths["Northbound"].make_dispatching_block(
        block_id="WC-104",
        dispatch_margin=80,
        upstream_blocks=[
            "WC-104",
            "621",
            "WC-111",
            "WC-117",
            "WC-125",
            "WC-130",
            "WC-138",
            "WC-144",
            "WC-151",
            "WC-158",
        ],
    )

    paths["Southbound"].make_dispatching_block(
        block_id="NWD-739", dispatch_margin=0, upstream_blocks=["NWD-739"]
    )

    if cfg.short_turning == "UIC":
        paths["ShortTurning"] = ShortTurningPath(
            nb_path=paths["Northbound"],
            sb_path=paths["Southbound"],
            nb_juncture_block_id="WC-16",
            sb_juncture_block_id="WD-13",
        )
    elif cfg.short_turning == "Western":
        paths["ShortTurning"] = ShortTurningAtWestern(
            nb_path=paths["Northbound"],
            sb_path=paths["Southbound"],
            nb_juncture_block_id="WC-104",
            sb_juncture_block_id="WD-111",
        )

    else:
        raise Exception("Invalid short turning type")

    return paths, signal_control_center


from mit_rail_sim.utils import project_root


@hydra.main(
    config_path=str(project_root / "load-balance"),
    config_name="config",
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

    fixed_arrival_rates_function = partial(
        create_path_from_data_with_offscan_symptom, arrival_rates=arrival_rates
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
