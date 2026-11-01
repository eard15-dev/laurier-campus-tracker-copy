from flask import Blueprint, current_app, jsonify, request

from database import get_db
from services.calculations import (
    BUSYNESS_LABELS, NOISE_LABELS, calculate_status, calculate_trends,
    cutoff_string, get_recent_reports,
)

bp = Blueprint("locations", __name__)


def find_location(location_id):
    return get_db().execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()


@bp.get("/buildings")
def list_buildings():
    rows = get_db().execute("SELECT DISTINCT building FROM locations ORDER BY building").fetchall()
    return jsonify(buildings=[row["building"] for row in rows])


@bp.get("/locations")
def list_locations():
    search = request.args.get("search", "").strip()
    building = request.args.get("building", "").strip()
    noise = request.args.get("noise", "").strip().lower()
    busyness = request.args.get("busyness", "").strip().lower()

    if noise and noise not in NOISE_LABELS:
        return jsonify(error="noise must be one of: " + ", ".join(NOISE_LABELS)), 400
    if busyness and busyness not in BUSYNESS_LABELS:
        return jsonify(error="busyness must be one of: " + ", ".join(BUSYNESS_LABELS)), 400

    db = get_db()
    config = current_app.config

    sql = "SELECT * FROM locations WHERE 1=1"
    params = []
    if building:
        sql += " AND LOWER(building) = LOWER(?)"
        params.append(building)
    if search:
        sql += " AND (instr(LOWER(name), LOWER(?)) > 0 OR instr(LOWER(building), LOWER(?)) > 0)"
        params += [search, search]
    rows = db.execute(sql + " ORDER BY building, name", params).fetchall()

    # group the recent reports by location so we only query once
    reports_by_location = {}
    for report in get_recent_reports(db, config):
        reports_by_location.setdefault(report["location_id"], []).append(report)

    results = []
    for row in rows:
        location = dict(row)
        location["status"] = calculate_status(reports_by_location.get(row["id"], []), config)
        if noise and location["status"]["noise_label"] != noise:
            continue
        if busyness and location["status"]["busyness_label"] != busyness:
            continue
        results.append(location)

    return jsonify(locations=results, count=len(results))


@bp.get("/locations/<int:location_id>")
def get_location(location_id):
    location = find_location(location_id)
    if location is None:
        return jsonify(error="Location not found"), 404
    return jsonify(dict(location))


@bp.get("/locations/<int:location_id>/status")
def get_status(location_id):
    if find_location(location_id) is None:
        return jsonify(error="Location not found"), 404
    config = current_app.config
    reports = get_recent_reports(get_db(), config, location_id)
    return jsonify(location_id=location_id, **calculate_status(reports, config))


@bp.get("/locations/<int:location_id>/reports")
def get_location_reports(location_id):
    if find_location(location_id) is None:
        return jsonify(error="Location not found"), 404
    config = current_app.config
    rows = get_db().execute(
        "SELECT * FROM reports WHERE location_id = ? AND created_at >= ? AND flag_count < ? "
        "ORDER BY created_at DESC, id DESC",
        (location_id, cutoff_string(config["REPORT_WINDOW_MINUTES"]), config["FLAG_THRESHOLD"]),
    ).fetchall()
    return jsonify(reports=[dict(row) for row in rows], count=len(rows))


@bp.get("/locations/<int:location_id>/trends")
def get_trends(location_id):
    if find_location(location_id) is None:
        return jsonify(error="Location not found"), 404
    config = current_app.config
    rows = get_db().execute(
        "SELECT busyness_level, created_at FROM reports WHERE location_id = ? AND flag_count < ?",
        (location_id, config["FLAG_THRESHOLD"]),
    ).fetchall()
    return jsonify(location_id=location_id, **calculate_trends(rows, config))
