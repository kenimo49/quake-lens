"""気象庁 (JMA) 地震リスト list.json のアダプタ。"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from quake_lens.schema import SOURCE_JMA, make_event, parse_iso8601_utc, to_iso8601_utc
from quake_lens.sources.http_client import http_get as _http_get

BASE_URL = "https://www.jma.go.jp/bosai/quake/data/list.json"

# ISO 6709風の符号付き数値を1つずつ切り出す。`+32.6+130.7-10000/` のような
# 連結表記から `+32.6` / `+130.7` / `-10000` を順に取り出すのに使う。
_COD_TOKEN = re.compile(r"[+-]\d+(?:\.\d+)?")


def _default_http_get(url: str) -> bytes:
    return _http_get(url, timeout=30.0)


def fetch_recent(
    limit: int = 10,
    http_get: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    """JMAの地震リストを取得して正規化イベントのリストを返す。http_getはテスト用に注入可能。"""
    getter = http_get or _default_http_get
    raw = getter(BASE_URL)
    payload = json.loads(raw)
    return parse(payload, limit=limit)


def _parse_cod(cod: str) -> tuple[float, float, float] | None:
    """ISO 6709風の`cod`文字列を(lat, lon, depth_km)に変換する。

    第3成分はメートル単位で通常は負値。負のメートル値を正のkm値に変換する
    (例: `-10000` → 10.0)。ごく浅い地震は `+0` (正のゼロ) と表記されるため、
    符号反転で生じる `-0.0` は正のゼロに正規化する。tokenが3つ未満なら
    Noneを返す。
    """
    tokens = _COD_TOKEN.findall(cod)
    if len(tokens) < 3:
        return None
    try:
        lat = float(tokens[0])
        lon = float(tokens[1])
        depth_m = float(tokens[2])
    except ValueError:
        return None
    # + 0.0 は `-0.0` (ごく浅い `+0` 表記の符号反転) を正のゼロにするため
    depth_km = -depth_m / 1000.0 + 0.0
    return lat, lon, depth_km


def _to_event(item: dict[str, Any]) -> dict[str, Any] | None:
    """list.jsonの1要素を正規化イベントに変換する。

    `cod`/`mag`/`at` のいずれかが欠落・空文字・parse不能な要素 (震度速報等、
    震源情報を持たない電文) は None を返す。
    """
    cod = item.get("cod")
    mag_str = item.get("mag")
    at = item.get("at")
    if not cod or not mag_str or not at:
        return None
    parsed = _parse_cod(cod)
    if parsed is None:
        return None
    lat, lon, depth_km = parsed
    try:
        mag = float(mag_str)
    except (TypeError, ValueError):
        return None
    try:
        when = parse_iso8601_utc(at)
    except ValueError:
        return None
    return make_event(
        time=to_iso8601_utc(when),
        lat=lat,
        lon=lon,
        depth_km=depth_km,
        mag=mag,
        place=item.get("anm") or "",
        source=SOURCE_JMA,
    )


def parse(payload: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    """JMAリストレスポンスを正規化イベントに変換する。

    1要素の変換は `_to_event` に委譲し、ここでは全体の制御だけを行う:
    同一 `eid` (同一地震の続報) は最初の1件のみ採用する。list.jsonは
    新しい報が先頭に並ぶ (rdt降順) ため、これは精査済みの最新報を採用する
    意味になる。`limit` が指定されれば先頭からその件数までに切り詰める。
    """
    events: list[dict[str, Any]] = []
    seen_eids: set[str] = set()
    for item in payload:
        eid = item.get("eid")
        if eid and eid in seen_eids:
            continue
        event = _to_event(item)
        if event is None:
            continue
        if eid:
            seen_eids.add(eid)
        events.append(event)
        if limit is not None and len(events) >= limit:
            break
    return events
