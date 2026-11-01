def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_get_all_locations(client):
    data = client.get("/api/locations").get_json()
    assert data["count"] == 3
    assert data["locations"][0]["status"]["status"] == "insufficient_data"


def test_get_one_location(client):
    response = client.get("/api/locations/1")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Room A"


def test_get_missing_location(client):
    response = client.get("/api/locations/999")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_status_averages(client, add_report):
    for noise, busy in [(1, 2), (2, 3), (3, 4)]:
        add_report(1, noise, busy)
    status = client.get("/api/locations/1/status").get_json()
    assert status["status"] == "ok"
    assert status["average_noise"] == 2.0
    assert status["average_busyness"] == 3.0
    assert status["recent_report_count"] == 3
    assert status["noise_label"] == "quiet"
    assert status["busyness_label"] == "medium"
    assert status["latest_report_at"] is not None


def test_insufficient_data(client, add_report):
    add_report(1, 1, 1)
    add_report(1, 1, 1)
    status = client.get("/api/locations/1/status").get_json()
    assert status["status"] == "insufficient_data"
    assert status["recent_report_count"] == 2
    # Must NOT claim the room is quiet or empty.
    assert status["noise_label"] is None
    assert status["average_noise"] is None


def test_expired_reports_ignored(client, add_report):
    add_report(1, 5, 5, minutes_ago=120)  # too old
    add_report(1, 5, 5, minutes_ago=90)   # too old
    add_report(1, 1, 1)
    add_report(1, 1, 1)
    add_report(1, 1, 1)
    status = client.get("/api/locations/1/status").get_json()
    assert status["recent_report_count"] == 3
    assert status["average_noise"] == 1.0
    reports = client.get("/api/locations/1/reports").get_json()
    assert reports["count"] == 3


def test_status_missing_location(client):
    assert client.get("/api/locations/999/status").status_code == 404
    assert client.get("/api/locations/999/reports").status_code == 404


def test_filter_by_building(client):
    data = client.get("/api/locations?building=north hall").get_json()
    assert data["count"] == 2
    assert client.get("/api/locations?building=Nowhere").get_json()["count"] == 0


def test_filter_by_noise_and_busyness(client, add_report):
    for _ in range(3):
        add_report(1, 1, 1)  # quiet + empty
        add_report(2, 5, 5)  # loud + packed
    quiet = client.get("/api/locations?noise=quiet").get_json()
    assert [l["name"] for l in quiet["locations"]] == ["Room A"]
    packed = client.get("/api/locations?busyness=high").get_json()
    assert [l["name"] for l in packed["locations"]] == ["Room B"]
    both = client.get("/api/locations?building=North Hall&noise=quiet&busyness=low").get_json()
    assert both["count"] == 1


def test_filter_invalid_value(client):
    response = client.get("/api/locations?noise=extreme")
    assert response.status_code == 400
