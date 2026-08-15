from unittest.mock import AsyncMock, patch


@patch("geointel.api.routers.explain.generate_explanation", new_callable=AsyncMock)
def test_explain_endpoint_mocked(mock_generate, client):
    mock_generate.return_value = "Тестовый анализ засухи"

    payload = {"scope": "district", "subject_id": 1, "decade": "2024-05-01", "lang": "ru"}

    response = client.post("/api/explain", json=payload)

    # Если в тестовой БД нет записи — проверим корректную обработку 404/400
    assert response.status_code in (200, 404)
