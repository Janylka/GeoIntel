import pytest
from fastapi.testclient import TestClient

from geointel.api.main import app


@pytest.fixture
def client():
    return TestClient(app)
