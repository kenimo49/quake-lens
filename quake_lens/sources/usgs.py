"""USGS FDSN event API adapter (GeoJSON)."""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Callable

from quake_lens.schema import make_event, to_iso8601_utc
from quake_lens.sources.http_client import http_get as _http_get

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def _default_http_get(url: str) -> bytes:
    return _http_get(url, timeout=60.0)


def build_url(
    start: str | None,
    end: str | None,
    min_mag: float | None,
    bbox: tuple[float, float, float, float] | None,
) -> str:
    q: dict[str, str] = {"format": "geojson"}
    if start:
        q["starttime"] = start
    if end:
        q["endtime"] = end
    if min_mag is not None:
        q["minmagnitude"] = str(min_mag)
    if bbox is not None:
        minlat, minlon, maxlat, maxlon = bbox
        q["minlatitude"] = str(minlat)
        q["minlongitude"] = str(minlon)
        q["maxlatitude"] = str(maxlat)
        q["maxlongitude"] = str(maxlon)
    return f"{BASE_URL}?{urllib.parse.urlencode(q)}"


def fetch_catalog(
    start: str | None = None,
    end: str | None = None,
    min_mag: float | None = None,
    bbox: tuple[float, float, float, float] | None = (24.0, 122.0, 46.0, 146.0),
    http_get: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    getter = http_get or _default_http_get
    raw = getter(build_url(start, end, min_mag, bbox))
    payload = json.loads(raw)
    return parse(payload)


def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for feat in payload.get("features", []):
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 3:
            continue
        lon, lat, depth = coords[0], coords[1], coords[2]
        mag = props.get("mag")
        time_ms = props.get("time")
        if mag is None or time_ms is None:
            continue
        when = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)
        events.append(
            make_event(
                time=to_iso8601_utc(when),
                lat=lat,
                lon=lon,
                depth_km=depth,
                mag=mag,
                place=props.get("place") or "",
                source="usgs",
            )
        )
    return events
