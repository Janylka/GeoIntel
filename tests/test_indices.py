import pytest

from geointel.domain.indices import compute_tci, compute_vci, compute_vhi


def test_compute_vci():
    assert compute_vci(0.5, 0.2, 0.8) == pytest.approx(50.0)
    assert compute_vci(0.2, 0.2, 0.8) == 0.0
    assert compute_vci(0.8, 0.2, 0.8) == 100.0

    # Boundary checks
    assert compute_vci(0.9, 0.2, 0.8) == 100.0  # Cap at 100
    assert compute_vci(0.1, 0.2, 0.8) == 0.0  # Cap at 0

    # Zero variation
    assert compute_vci(0.5, 0.5, 0.5) == 50.0


def test_compute_tci():
    assert compute_tci(30.0, 20.0, 40.0) == 50.0
    assert compute_tci(20.0, 20.0, 40.0) == 100.0  # Coldest is best
    assert compute_tci(40.0, 20.0, 40.0) == 0.0  # Hottest is worst

    # Boundary checks
    assert compute_tci(10.0, 20.0, 40.0) == 100.0  # Cap at 100
    assert compute_tci(50.0, 20.0, 40.0) == 0.0  # Cap at 0

    # Zero variation
    assert compute_tci(30.0, 30.0, 30.0) == 50.0


def test_compute_vhi():
    assert compute_vhi(50.0, 50.0) == 50.0
    assert compute_vhi(100.0, 0.0) == 50.0
    assert compute_vhi(100.0, 100.0) == 100.0
    assert compute_vhi(100.0, 0.0, alpha=0.8) == 80.0
