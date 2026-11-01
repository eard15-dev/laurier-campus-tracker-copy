from datetime import datetime, timezone

# january: Toronto is UTC-5, so 15:00 UTC = 10:00 local
def utc(hour, day=10):
    return datetime(2026, 1, day, hour, 0, tzinfo=timezone.utc)


def test_search_by_space_or_building(client):
    assert client.get("/api/locations?search=room b").get_json()["count"] == 1
    assert client.get("/api/locations?search=SOUTH").get_json()["count"] == 1
    assert client.get("/api/locations?search=hall").get_json()["count"] == 3
    assert client.get("/api/locations?search=zzz").get_json()["count"] == 0
    assert client.get("/api/locations?search=%25").get_json()["count"] == 0  # '%' is not a wildcard


def test_buildings_list(client):
    assert client.get("/api/buildings").get_json() == {"buildings": ["North Hall", "South Hall"]}


def test_trends(client, add_report):
    for day in (10, 11, 12):
        add_report(1, 3, 1, when=utc(15, day))  # 10:00 local -> morning, quiet
        add_report(1, 3, 5, when=utc(20, day))  # 15:00 local -> afternoon, busy
    add_report(1, 3, 3, when=utc(2))            # only 1 evening report: not enough
    data = client.get("/api/locations/1/trends").get_json()
    by_name = {p["period"]: p for p in data["periods"]}
    assert data["status"] == "ok"
    assert by_name["morning"]["average_busyness"] == 1.0
    assert by_name["afternoon"]["busyness_label"] == "high"
    assert by_name["evening"]["average_busyness"] is None
    assert by_name["evening"]["report_count"] == 1
    assert data["quietest_period"] == "morning"
    assert data["busiest_period"] == "afternoon"


def test_trends_insufficient_data(client):
    data = client.get("/api/locations/1/trends").get_json()
    assert data["status"] == "insufficient_data"
    assert data["busiest_period"] is None
    assert client.get("/api/locations/999/trends").status_code == 404


def test_flagging_hides_report(client, add_report):
    for _ in range(3):
        add_report(1, 3, 3)
    first = client.post("/api/reports/1/flag").get_json()
    assert first["flag_count"] == 1 and first["hidden"] is False
    client.post("/api/reports/1/flag")
    third = client.post("/api/reports/1/flag").get_json()
    assert third["hidden"] is True
    # Hidden report no longer counts: only 2 left, below the minimum of 3.
    status = client.get("/api/locations/1/status").get_json()
    assert status["recent_report_count"] == 2
    assert status["status"] == "insufficient_data"
    assert client.get("/api/locations/1/reports").get_json()["count"] == 2


def test_flag_missing_report(client):
    assert client.post("/api/reports/999/flag").status_code == 404


def test_rate_limit(app):
    app.config["RATE_LIMIT_MINUTES"] = 5
    client = app.test_client()
    body = {"location_id": 1, "noise_level": 3, "busyness_level": 3}
    assert client.post("/api/reports", json=body).status_code == 201
    second = client.post("/api/reports", json=body)
    assert second.status_code == 429
    assert "error" in second.get_json()
    # A different space is still allowed.
    assert client.post("/api/reports", json={**body, "location_id": 2}).status_code == 201
