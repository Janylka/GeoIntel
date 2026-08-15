from datetime import date

import pytest

from geointel.domain import decade


@pytest.mark.parametrize(
    "input_date, expected_decade",
    [
        (date(2024, 5, 1), 1),
        (date(2024, 5, 10), 1),
        (date(2024, 5, 11), 2),
        (date(2024, 5, 20), 2),
        (date(2024, 5, 21), 3),
        (date(2024, 5, 31), 3),
    ],
)
def test_decade_of(input_date, expected_decade):
    assert decade.decade_of(input_date) == expected_decade


@pytest.mark.parametrize(
    "input_date, expected_start",
    [
        (date(2024, 5, 9), date(2024, 5, 1)),
        (date(2024, 5, 15), date(2024, 5, 11)),
        (date(2024, 5, 25), date(2024, 5, 21)),
        (date(2024, 2, 29), date(2024, 2, 21)),  # Leap year
    ],
)
def test_decade_start(input_date, expected_start):
    assert decade.decade_start(input_date) == expected_start


@pytest.mark.parametrize(
    "input_date, expected_next",
    [
        (date(2024, 5, 1), date(2024, 5, 11)),
        (date(2024, 5, 11), date(2024, 5, 21)),
        (date(2024, 5, 21), date(2024, 6, 1)),  # Month boundary
        (date(2024, 12, 21), date(2025, 1, 1)),  # Year boundary
    ],
)
def test_next_decade(input_date, expected_next):
    assert decade.next_decade(input_date) == expected_next


@pytest.mark.parametrize(
    "input_date, expected_prev",
    [
        (date(2024, 6, 1), date(2024, 5, 21)),  # Month boundary
        (date(2024, 5, 21), date(2024, 5, 11)),
        (date(2024, 5, 11), date(2024, 5, 1)),
        (date(2025, 1, 1), date(2024, 12, 21)),  # Year boundary
    ],
)
def test_previous_decade(input_date, expected_prev):
    assert decade.previous_decade(input_date) == expected_prev


def test_decade_range():
    start = date(2024, 12, 15)
    end = date(2025, 1, 15)
    result = list(decade.decade_range(start, end))
    assert result == [date(2024, 12, 11), date(2024, 12, 21), date(2025, 1, 1), date(2025, 1, 11)]


def test_same_decade_of_year():
    d = date(2024, 8, 25)  # 3rd decade of August
    result = decade.same_decade_of_year(d, 2020)
    assert result == date(2020, 8, 21)
