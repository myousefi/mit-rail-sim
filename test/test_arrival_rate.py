import pytest
from mit_rail_sim.simulation_engine.passenger.arrival_rate import ArrivalRate
import os


@pytest.fixture
def sample_arrival_rate():
    temp_file = "temp_test_data.csv"
    with open(temp_file, "w") as f:
        f.write("Origin,Destination,time_bin,weekday,arrival_rate\n")
        f.write("O-Hare,Rosemont,0,True,0.1\n")
        f.write("O-Hare,Rosemont,1,True,0.2\n")
        f.write("Rosemont,O-Hare,0,False,0.05\n")
        f.write("Rosemont,O-Hare,1,False,0.15\n")

    yield ArrivalRate(temp_file)
    os.remove(temp_file)


def test_sort_stations_by_direction(sample_arrival_rate):
    southbound = sample_arrival_rate.sort_stations_by_direction("Southbound")
    northbound = sample_arrival_rate.sort_stations_by_direction("Northbound")

    assert southbound[0] == "O-Hare"
    assert southbound[-1] == "Forest Park"
    assert northbound[0] == "Forest Park"
    assert northbound[-1] == "O-Hare"

    with pytest.raises(ValueError):
        sample_arrival_rate.sort_stations_by_direction("Invalid")


def test_is_southbound_trip(sample_arrival_rate):
    assert sample_arrival_rate.is_southbound_trip("O-Hare", "Rosemont")
    assert not sample_arrival_rate.is_southbound_trip("Rosemont", "O-Hare")


def test_get_smoothed_rate(sample_arrival_rate):
    rate = sample_arrival_rate.get_smoothed_rate(0.5, True, "O-Hare", "Rosemont")
    assert rate == pytest.approx(0.15, abs=0.05)

    rate = sample_arrival_rate.get_smoothed_rate(0, False, "Rosemont", "O-Hare")
    assert rate == 0.05

    rate = sample_arrival_rate.get_smoothed_rate(2, True, "O-Hare", "Rosemont")
    assert rate == 0.2

    rate = sample_arrival_rate.get_smoothed_rate(0, True, "O-Hare", "Forest Park")
    assert rate == 0


import pytest
from mit_rail_sim.utils import project_root


@pytest.fixture
def real_world_arrival_rate():
    real_data_file = (
        project_root
        / "inputs"
        / "demand"
        / "odx_imputed_demand_2024-04-07_2024-05-30.csv"
    )
    return ArrivalRate(filename=str(real_data_file), demand_factor=1.0)


def test_real_world_data(real_world_arrival_rate):
    # Test get_lambda_for_station
    lambda_value = real_world_arrival_rate.get_lambda_for_station(
        15.0, True, "UIC-Halsted", "Southbound"
    )
    assert lambda_value > 0

    # Test get_p_for_station
    p_value = real_world_arrival_rate.get_p_for_station(
        15.0, True, "UIC-Halsted", "Southbound"
    )
    assert 0 <= p_value <= 1

    p_value = real_world_arrival_rate.get_p_for_station(
        15.0, True, "Racine", "Southbound"
    )

    assert 0 <= p_value <= 1


def test_get_all_destination_stops_for_origin(real_world_arrival_rate):
    destinations = real_world_arrival_rate.get_all_destination_stops_for_origin(
        "O-Hare"
    )
    assert len(destinations) > 0
    assert "Forest Park" in destinations


def test_get_all_previous_stops_for_station_and_direction(real_world_arrival_rate):
    previous_stops = (
        real_world_arrival_rate.get_all_previous_stops_for_station_and_direction(
            "UIC-Halsted", "Southbound"
        )
    )
    assert len(previous_stops) > 0
    assert "O-Hare" in previous_stops
    assert "UIC-Halsted" not in previous_stops


def test_get_all_destination_stops_for_origin_and_direction(real_world_arrival_rate):
    destinations = (
        real_world_arrival_rate.get_all_destination_stops_for_origin_and_direction(
            "UIC-Halsted", "Southbound"
        )
    )
    assert len(destinations) > 0
    assert "Forest Park" in destinations
    assert "O-Hare" not in destinations


def test_get_a_i(real_world_arrival_rate):
    a_i = real_world_arrival_rate.get_a_i(
        15.0, True, "UIC-Halsted", "Forest Park", "Southbound"
    )
    assert 0 <= a_i <= 1


def test_get_lambda_bar(real_world_arrival_rate):
    lambda_bar = real_world_arrival_rate.get_lambda_bar(
        15.0, True, "UIC-Halsted", "Grand", "Northbound"
    )
    assert lambda_bar > 0
