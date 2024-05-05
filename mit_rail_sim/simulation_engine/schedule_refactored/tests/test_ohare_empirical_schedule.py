import pytest
from mit_rail_sim.simulation_engine.schedule_refactored.ohare_empirical_schedule import (
    OHareEmpiricalSchedule,
    OHareEmpiricalDispatchStrategy,
)


def test_ohare_empirical_schedule_initialization():
    params_path = "path/to/params.json"
    start_time_of_day = 36000  # 10:00 AM in seconds
    end_time_of_day = 64800  # 6:00 PM in seconds
    schedule = OHareEmpiricalSchedule(params_path, start_time_of_day, end_time_of_day)
    assert schedule.start_time_of_day == start_time_of_day
    assert schedule.end_time_of_day == end_time_of_day
    assert isinstance(schedule.dispatch_strategy, OHareEmpiricalDispatchStrategy)


def test_ohare_empirical_dispatch_strategy_initialization():
    params = {
        "file_path": "path/to/params.json",
        "empirical_schedule": [
            {
                "time_in_sec": 36000,
                "runid": "1",
                "direction": "North",
                "short_turned": False,
            }
        ],
        "blue_line_schedule": [{"time_in_sec": 36000, "runid": "1"}],
    }
    schedule = OHareEmpiricalSchedule(params, 36000, 64800)
    strategy = OHareEmpiricalDispatchStrategy(schedule)
    assert not strategy.empirical_schedule_data.empty
    assert not strategy.blue_line_schedule_data.empty


def test_generate_dispatch_info():
    params = {
        "file_path": "path/to/params.json",
        "empirical_schedule": [
            {
                "time_in_sec": 36000,
                "runid": "1",
                "direction": "North",
                "short_turned": False,
                "headway": 900,
            },
            {
                "time_in_sec": 36900,
                "runid": "2",
                "direction": "North",
                "short_turned": True,
                "headway": 900,
            },
        ],
        "blue_line_schedule": [
            {"time_in_sec": 36000, "runid": "1"},
            {"time_in_sec": 36900, "runid": "2"},
        ],
    }
    schedule = OHareEmpiricalSchedule(params, 36000, 64800)
    strategy = OHareEmpiricalDispatchStrategy(schedule)
    dispatch_info = strategy.generate_dispatch_info()
    assert len(dispatch_info) == 2
    assert dispatch_info[0][0] == 36000
    assert dispatch_info[0][2] == "North"
    assert dispatch_info[1][2] == "ShortTurning"


def test_validate_params_missing_data():
    params = {
        "file_path": "path/to/params.json",
        "blue_line_schedule": [{"time_in_sec": 36000, "runid": "1"}],
    }
    with pytest.raises(
        ValueError, match="Empirical schedule data not found in params file"
    ):
        schedule = OHareEmpiricalSchedule(params, 36000, 64800)


def test_validate_params_missing_blue_line_schedule():
    params = {
        "file_path": "path/to/params.json",
        "empirical_schedule": [
            {
                "time_in_sec": 36000,
                "runid": "1",
                "direction": "North",
                "short_turned": False,
            }
        ],
    }
    with pytest.raises(
        ValueError, match="Blue line schedule data not found in params file"
    ):
        schedule = OHareEmpiricalSchedule(params, 36000, 64800)
