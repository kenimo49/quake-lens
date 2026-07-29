"""複数sourceで共有する、正規化された地震イベントのschema定義。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

FIELDS = ("time", "lat", "lon", "depth_km", "mag", "place", "source")
SOURCES = ("usgs", "jma", "p2p")


def make_event(
    *,
    time: str,
    lat: float,
    lon: float,
    depth_km: float,
    mag: float,
    place: str,
    source: str,
) -> dict[str, Any]:
    """正規化イベントdictを組み立てる。sourceは SOURCES のいずれかであること。"""
    if source not in SOURCES:
        raise ValueError(f"unknown source: {source}")
    return {
        "time": time,
        "lat": float(lat),
        "lon": float(lon),
        "depth_km": float(depth_km),
        "mag": float(mag),
        "place": str(place),
        "source": source,
    }


def parse_iso8601_utc(s: str) -> datetime:
    """ISO8601文字列をtz付きのUTC datetimeにparseする。

    末尾の 'Z' も、明示的なoffset表記も受け付ける。
    """
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso8601_utc(dt: datetime) -> str:
    """datetimeをUTCの `YYYY-MM-DDTHH:MM:SSZ` 形式の文字列にする。naiveはUTCとみなす。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_event(obj: dict[str, Any]) -> dict[str, Any]:
    """必須フィールドが揃っているか検証し、揃っていればそのまま返す。"""
    missing = [f for f in FIELDS if f not in obj]
    if missing:
        raise ValueError(f"event missing fields: {missing}")
    return obj
