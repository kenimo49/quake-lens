"""P2P地震情報 API v2 adapter (codes=551, quake info)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from quake_lens.schema import make_event, to_iso8601_utc

BASE_URL = "https://api.p2pquake.net/v2/history"
_JST = timezone(timedelta(hours=9))


def _default_http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        return resp.read()


def build_url(limit: int) -> str:
    q = urllib.parse.urlencode({"codes": 551, "limit": int(limit)})
    return f"{BASE_URL}?{q}"


def fetch_recent(
    limit: int = 10,
    min_scale: int | None = None,
    http_get: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    getter = http_get or _default_http_get
    raw = getter(build_url(limit))
    payload = json.loads(raw)
    return parse(payload, min_scale=min_scale)


def _parse_jst_time(s: str) -> datetime:
    """P2P returns local (JST) times like '2024-01-01 16:10:00.000' or with '/'."""
    s = s.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"unrecognized P2P time: {s!r}")
    return dt.replace(tzinfo=_JST).astimezone(timezone.utc)


def parse(payload: list[dict[str, Any]], min_scale: int | None = None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for item in payload:
        if item.get("code") != 551:
            continue
        eq = item.get("earthquake") or {}
        hypo = eq.get("hypocenter") or {}
        if min_scale is not None and (eq.get("maxScale") or 0) < min_scale:
            continue
        time_str = eq.get("time")
        if not time_str:
            continue
        try:
            when = _parse_jst_time(time_str)
        except ValueError:
            continue
        lat = hypo.get("latitude")
        lon = hypo.get("longitude")
        depth = hypo.get("depth")
        mag = hypo.get("magnitude")
        if lat is None or lon is None or mag is None:
            continue
        events.append(
            make_event(
                time=to_iso8601_utc(when),
                lat=lat,
                lon=lon,
                depth_km=depth if depth is not None else -1.0,
                mag=mag,
                place=hypo.get("name") or "",
                source="p2p",
            )
        )
    return events
