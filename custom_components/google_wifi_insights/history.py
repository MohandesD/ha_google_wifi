"""Google usage buckets, not invented lifetime or instantaneous counters."""
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

WINDOWS = {
    "minute": (3600, 60, 60),
    "hour": (86400, 3600, 300),
    "day": (604800, 86400, 1800),
    "month": (2592000, 86400, 3600),
}


def instant(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except ValueError:
        return None


def nonnegative_int(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    try:
        number = int(value)
        return number if number >= 0 else None
    except ValueError:
        return None


def request_window(mode, now=None):
    duration, granularity, _ = WINDOWS[mode]
    epoch = int((now or datetime.now(UTC)).timestamp())
    # Complete minute boundaries; hourly/day buckets are rolling UTC intervals.
    end = datetime.fromtimestamp(epoch - epoch % 60, UTC)
    start = end - timedelta(seconds=duration)
    period = {"start": start.isoformat(), "end": end.isoformat(), "granularity_seconds": granularity}
    query = urlencode({"dateRange.startTimestamp": period["start"],
                       "dateRange.endTimestamp": period["end"],
                       "granularity": granularity, "prettyPrint": "false"})
    return period, query


def buckets(rows, period):
    """Observed Google timestamps mark bucket END, as peak records confirm."""
    if not isinstance(rows, list):
        return []
    start, end = instant(period["start"]), instant(period["end"])
    result, ambiguous = {}, set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        at = instant(row.get("timestamp"))
        if at is None or not start < at <= end:
            continue
        if (at-start).total_seconds() % period["granularity_seconds"]:
            continue
        receive = nonnegative_int(row.get("bytesReceived", 0))
        transmit = nonnegative_int(row.get("bytesTransmitted", 0))
        if receive is None or transmit is None:
            continue
        item = {"start": (at-timedelta(seconds=period["granularity_seconds"])).isoformat(),
                "end": at.isoformat(), "download_bytes": receive, "upload_bytes": transmit}
        if at in result and result[at] != item:
            ambiguous.add(at)
        result[at] = item
    return [result[key] for key in sorted(result) if key not in ambiguous]


def normalize_history(payload, period):
    stations = {}
    for row in payload.get("stationUsageRecords", []):
        if isinstance(row, dict) and isinstance(row.get("station"), dict):
            sid = row["station"].get("id")
            if isinstance(sid, str):
                if isinstance(row.get("usageRecords"), list):
                    stations.setdefault(sid, []).extend(row["usageRecords"])
    peaks = []
    for row in payload.get("peakDataRateRecords", []):
        if not isinstance(row, dict) or not instant(row.get("startTimestamp")) or not instant(row.get("endTimestamp")):
            continue
        peaks.append({"start": row["startTimestamp"], "end": row["endTimestamp"],
                      "download_bps": nonnegative_int(row.get("peakReceivedBps", 0)),
                      "upload_bps": nonnegative_int(row.get("peakTransmittedBps", 0))})
    return {"period": period, "retrieved_at": datetime.now(UTC).isoformat(),
            "wan": buckets(payload.get("wanUsageRecords"), period),
            "stations": {sid: buckets(rows, period) for sid, rows in stations.items()}, "peaks": peaks}


def summarize(rows, period):
    expected = int((instant(period["end"])-instant(period["start"])).total_seconds()) // period["granularity_seconds"]
    return {**period, "buckets": len(rows), "expected_buckets": expected,
            "complete": len(rows) == expected,
            "download_bytes": sum(row["download_bytes"] for row in rows) if rows else None,
            "upload_bytes": sum(row["upload_bytes"] for row in rows) if rows else None}


def apply_history(network, histories):
    for kind, items in (("network", {"network": network}), ("client", network["clients"])):
        for sid, item in items.items():
            usage = {}
            for mode, data in histories.items():
                rows = data["wan"] if kind == "network" else data["stations"].get(sid, [])
                usage[mode] = {**summarize(rows, data["period"]), "retrieved_at": data["retrieved_at"]}
            item["usage_windows"] = usage
            for mode, suffix in (("hour", "24h"), ("day", "7d"), ("month", "30d")):
                for direction in ("download", "upload"):
                    summary = usage.get(mode, {})
                    # Missing buckets remain explicitly incomplete, not a false total.
                    item[f"usage_{suffix}_{direction}"] = summary.get(direction+"_bytes") if summary.get("complete") else None
            hour = histories.get("hour", {})
            item["usage_hourly"] = hour.get("wan", []) if kind == "network" else hour.get("stations", {}).get(sid, [])
            if kind == "network":
                peaks = histories.get("minute", {}).get("peaks", [])
                for direction in ("download", "upload"):
                    values = [p[direction+"_bps"] for p in peaks if p[direction+"_bps"] is not None]
                    item["peak_1h_"+direction+"_mbps"] = max(values)/1_000_000 if values else None
