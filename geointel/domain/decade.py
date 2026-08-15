from collections.abc import Generator
from datetime import date, timedelta


def decade_of(d: date) -> int:
    """Returns the decade number (1, 2, or 3) for a given date."""
    if d.day <= 10:
        return 1
    if d.day <= 20:
        return 2
    return 3


def decade_start(d: date) -> date:
    """Returns the start date of the decade for a given date."""
    if d.day <= 10:
        return d.replace(day=1)
    if d.day <= 20:
        return d.replace(day=11)
    return d.replace(day=21)


def next_decade(d: date) -> date:
    """Returns the start date of the next decade."""
    current_decade_start = decade_start(d)
    if current_decade_start.day == 1:
        return current_decade_start.replace(day=11)
    if current_decade_start.day == 11:
        return current_decade_start.replace(day=21)
    # Last decade of the month
    first_day_of_next_month = (current_decade_start.replace(day=28) + timedelta(days=4)).replace(
        day=1
    )
    return first_day_of_next_month


def previous_decade(d: date) -> date:
    """Returns the start date of the previous decade."""
    current_decade_start = decade_start(d)
    if current_decade_start.day == 21:
        return current_decade_start.replace(day=11)
    if current_decade_start.day == 11:
        return current_decade_start.replace(day=1)
    # First decade of the month
    last_day_of_previous_month = current_decade_start - timedelta(days=1)
    return last_day_of_previous_month.replace(day=21)


def decade_range(start: date, end: date) -> Generator[date, None, None]:
    """Yields start dates of all decades from start date to end date, inclusive."""
    current = decade_start(start)
    while current <= end:
        yield current
        current = next_decade(current)


def same_decade_of_year(d: date, year: int) -> date:
    """Returns the start date of the same decade but in a different year."""
    start = decade_start(d)
    day = start.day
    month = start.month
    return date(year, month, day)
