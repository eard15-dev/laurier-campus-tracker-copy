import pytest


def post(client, body):
    return client.post("/api/reports", json=body)


def test_submit_valid_report(client):
    response = post(client, {"location_id": 1, "noise_level": 2, "busyness_level": 4})
    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "Report submitted successfully"
    assert data["report_id"] == 1
    saved = client.get("/api/reports").get_json()
    assert saved["count"] == 1
    assert saved["reports"][0]["noise_level"] == 2


@pytest.mark.parametrize("noise,busy", [(0, 3), (6, 3), (3, 0), (3, 6), ("3", 3), (3, 2.5), (True, 3), (None, 3)])
def test_reject_invalid_ratings(client, noise, busy):
    response = post(client, {"location_id": 1, "noise_level": noise, "busyness_level": busy})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_reject_missing_fields(client):
    assert post(client, {"location_id": 1}).status_code == 400
    assert post(client, {"noise_level": 3, "busyness_level": 3}).status_code == 400


def test_reject_nonexistent_location(client):
    response = post(client, {"location_id": 999, "noise_level": 3, "busyness_level": 3})
    assert response.status_code == 404


def test_reject_empty_or_malformed_json(client):
    assert client.post("/api/reports").status_code == 400
    assert post(client, {}).status_code == 400
    bad = client.post("/api/reports", data="{not json", content_type="application/json")
    assert bad.status_code == 400
    assert client.post("/api/reports", json=[1, 2]).status_code == 400


def test_list_reports_with_filters(client, add_report):
    add_report(1, 1, 1)
    add_report(2, 3, 5)
    add_report(3, 3, 2)
    assert client.get("/api/reports").get_json()["count"] == 3
    assert client.get("/api/reports?location_id=2").get_json()["count"] == 1
    assert client.get("/api/reports?noise_level=3").get_json()["count"] == 2
    assert client.get("/api/reports?building=North Hall").get_json()["count"] == 2
    assert client.get("/api/reports?noise_level=3&busyness_level=5").get_json()["count"] == 1
    assert client.get("/api/reports?limit=1").get_json()["count"] == 1


def test_list_reports_invalid_filter(client):
    assert client.get("/api/reports?noise_level=9").status_code == 400
    assert client.get("/api/reports?location_id=abc").status_code == 400


def test_unknown_route_is_json_404(client):
    response = client.get("/api/nothing")
    assert response.status_code == 404
    assert response.get_json()["error"]


def test_submitted_reports_feed_status(client):
    for _ in range(3):
        post(client, {"location_id": 3, "noise_level": 5, "busyness_level": 5})
    status = client.get("/api/locations/3/status").get_json()
    assert status["noise_label"] == "loud"


def test_database_enforces_foreign_keys(app):
    import sqlite3
    from database import connect
    conn = connect(app.config["DATABASE"])
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO reports (location_id, noise_level, busyness_level, created_at) VALUES (999, 3, 3, 'x')"
        )


def test_unexpected_error_returns_json_500(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/api/boom")
    def boom():
        raise RuntimeError("test crash")

    response = app.test_client().get("/api/boom")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
