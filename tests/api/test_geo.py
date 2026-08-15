def test_get_units_geojson_structure(client):
    response = client.get("/api/geo/units.geojson")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "ETag" in response.headers


def test_get_units_geojson_etag_304(client):
    # Первый запрос — получаем ETag
    response1 = client.get("/api/geo/units.geojson")
    assert response1.status_code == 200
    etag = response1.headers.get("ETag")
    assert etag is not None

    # Второй запрос — передаем If-None-Match
    response2 = client.get("/api/geo/units.geojson", headers={"If-None-Match": etag})
    assert response2.status_code == 304
