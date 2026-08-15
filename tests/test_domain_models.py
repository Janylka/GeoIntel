import pytest

from geointel.domain.indices import compute_spi
from geointel.domain.water_balance import compute_crop_evapotranspiration, update_soil_water_balance
from geointel.domain.yield_model import predict_yield


def test_compute_spi():
    assert compute_spi(100.0, 50.0, 25.0) == 2.0
    assert compute_spi(50.0, 50.0, 25.0) == 0.0
    assert compute_spi(25.0, 50.0, 25.0) == -1.0
    # Zero std should return 0
    assert compute_spi(10.0, 10.0, 0.0) == 0.0


def test_compute_crop_evapotranspiration():
    assert compute_crop_evapotranspiration(5.0, 0.8) == 4.0
    assert compute_crop_evapotranspiration(0.0, 0.8) == 0.0


def test_update_soil_water_balance():
    # SW_t = SW_{t-1} + P - ETc - RO - DP
    assert update_soil_water_balance(100.0, 20.0, 5.0) == 115.0
    # Should not go below 0
    assert update_soil_water_balance(10.0, 0.0, 20.0) == 0.0


def test_predict_yield():
    # Baseline
    assert predict_yield(10.0, 50.0, 0.0) == pytest.approx(10.0)
    # Good VHI
    assert predict_yield(10.0, 100.0, 0.0, alpha=0.2) == pytest.approx(12.0)
    # Bad SPI
    assert predict_yield(10.0, 50.0, -1.0, beta=0.1) == pytest.approx(9.0)
    # Combined
    assert predict_yield(10.0, 75.0, 1.0, alpha=0.2, beta=0.1) == pytest.approx(12.0)
