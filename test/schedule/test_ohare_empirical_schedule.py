import pytest
from unittest.mock import Mock, patch

from mit_rail_sim.simulation_engine.schedule_refactored.ohare_empirical_schedule import (
    OHareEmpiricalSchedule,
    OHareEmpiricalDispatchStrategy,
)

from mit_rail_sim.utils.root_path import project_root

FILE_PATH = project_root / "inputs" / "schedules" / "empirical_schedule_81.json"
START_TIME_OF_DAY = 36000  # 10:00 AM in seconds
END_TIME_OF_DAY = 64800  # 6:00 PM in seconds

PARAMS = {
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


def test_ohare_empirical_schedule_initialization():
    schedule = OHareEmpiricalSchedule(FILE_PATH, START_TIME_OF_DAY, END_TIME_OF_DAY)
    assert schedule.start_time_of_day == START_TIME_OF_DAY
    assert schedule.end_time_of_day == END_TIME_OF_DAY
    assert isinstance(schedule.dispatch_strategy, OHareEmpiricalDispatchStrategy)
