from fastapi import FastAPI
from fastapi.testclient import TestClient

from geointel.api.errors import register_error_handlers
from geointel.contracts.metrics import assert_scope_allowed
from geointel.contracts.scope import Scope

app = FastAPI()
register_error_handlers(app)


@app.get("/test-scope")
def dummy_endpoint(metric: str, scope: str):
    assert_scope_allowed(metric, Scope(scope))
    return {"status": "ok"}


client = TestClient(app)


def test_scope_rules_success():
    # vci requires DISTRICT. Asking for DISTRICT is OK.
    resp = client.get("/test-scope?metric=vci&scope=district")
    assert resp.status_code == 200


def test_scope_rules_too_fine_422():
    # soil_moisture requires DISTRICT. Asking for FIELD should fail with 422.
    resp = client.get("/test-scope?metric=soil_moisture&scope=field")
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"] == "ScopeTooFineError"
    assert data["min_scope"] == "district"
    assert data["requested_scope"] == "field"
