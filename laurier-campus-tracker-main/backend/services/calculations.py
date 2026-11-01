from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

NOISE_LABELS = ("quiet", "moderate", "loud")
BUSYNESS_LABELS = ("low", "medium", "high")
PERIODS = ("morning", "midday", "afternoon", "evening")


def period_for_hour(hour):
    # late night (0-4) counts as evening
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "midday"
    if 14 <= hour < 18:
        return "afternoon"
    return "evening"


def utc_now_string():
    return datetime.now(timezone.utc).strftime(TIME_FORMAT)


def cutoff_string(window_minutes):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    return cutoff.strftime(TIME_FORMAT)


def level_label(average, labels, config):
    if average < config["LOW_MAX"]:
        return labels[0]
    if average < config["MODERATE_MAX"]:
        return labels[1]
    return labels[2]


def calculate_status(reports, config):
    count = len(reports)
    latest = None
    if count > 0:
        latest = max(r["created_at"] for r in reports)

    status = {
        "recent_report_count": count,
        "window_minutes": config["REPORT_WINDOW_MINUTES"],
        "min_reports_required": config["MIN_REPORTS"],
        "latest_report_at": latest,
        "average_noise": None,
        "average_busyness": None,
        "noise_label": None,
        "busyness_label": None,
    }

    if count < config["MIN_REPORTS"]:
        status["status"] = "insufficient_data"
        return status

    avg_noise = sum(r["noise_level"] for r in reports) / count
    avg_busy = sum(r["busyness_level"] for r in reports) / count

    status["status"] = "ok"
    status["average_noise"] = round(avg_noise, 2)
    status["average_busyness"] = round(avg_busy, 2)
    status["noise_label"] = level_label(avg_noise, NOISE_LABELS, config)
    status["busyness_label"] = level_label(avg_busy, BUSYNESS_LABELS, config)
    return status


def calculate_trends(reports, config):
    tz = ZoneInfo(config["TIMEZONE"])
    groups = {name: [] for name in PERIODS}
    for report in reports:
        time = datetime.strptime(report["created_at"], TIME_FORMAT).replace(tzinfo=timezone.utc)
        groups[period_for_hour(time.astimezone(tz).hour)].append(report["busyness_level"])

    periods = []
    for name in PERIODS:
        values = groups[name]
        average = None
        label = None
        if len(values) >= config["MIN_REPORTS"]:
            average = round(sum(values) / len(values), 2)
            label = level_label(average, BUSYNESS_LABELS, config)
        periods.append({
            "period": name,
            "report_count": len(values),
            "average_busyness": average,
            "busyness_label": label,
        })

    result = {
        "timezone": config["TIMEZONE"],
        "min_reports_required": config["MIN_REPORTS"],
        "periods": periods,
        "status": "insufficient_data",
        "quietest_period": None,
        "busiest_period": None,
    }

    with_data = [p for p in periods if p["average_busyness"] is not None]
    if len(with_data) >= 2:
        result["status"] = "ok"
        result["quietest_period"] = min(with_data, key=lambda p: p["average_busyness"])["period"]
        result["busiest_period"] = max(with_data, key=lambda p: p["average_busyness"])["period"]
    return result


def get_recent_reports(db, config, location_id=None):
    sql = ("SELECT id, location_id, noise_level, busyness_level, created_at, flag_count "
           "FROM reports WHERE created_at >= ? AND flag_count < ?")
    params = [cutoff_string(config["REPORT_WINDOW_MINUTES"]), config["FLAG_THRESHOLD"]]
    if location_id is not None:
        sql += " AND location_id = ?"
        params.append(location_id)
    return db.execute(sql, params).fetchall()
