import pytest

from geointel.contracts.metrics import ScopeTooFineError, assert_scope_allowed
from geointel.contracts.plans import Plan, PlanLimitError, assert_field_limit
from geointel.contracts.scope import Scope


def test_assert_scope_allowed_ok():
    """Should not raise when scope is sufficient."""
    assert_scope_allowed("soil_moisture", Scope.DISTRICT)
    assert_scope_allowed("ndvi", Scope.FIELD)
    assert_scope_allowed("ndvi", Scope.DISTRICT) # Coarser is always ok

def test_assert_scope_allowed_raises():
    """Should raise ScopeTooFineError for metrics on a too-fine scope."""
    with pytest.raises(ScopeTooFineError) as excinfo:
        assert_scope_allowed("soil_moisture", Scope.FIELD)

    assert excinfo.value.metric_id == "soil_moisture"
    assert excinfo.value.min_scope == Scope.DISTRICT
    assert excinfo.value.requested == Scope.FIELD

def test_assert_field_limit_ok():
    """Should not raise when limit is not reached."""
    assert_field_limit(Plan.FARMER, 4)
    assert_field_limit(Plan.ORG, 999) # Unlimited

def test_assert_field_limit_raises():
    """Should raise PlanLimitError when limit is reached or exceeded."""
    with pytest.raises(PlanLimitError):
        assert_field_limit(Plan.TRIAL, 1)
    with pytest.raises(PlanLimitError):
        assert_field_limit(Plan.FARMER, 5)
