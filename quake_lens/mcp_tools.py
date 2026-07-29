"""quake-lens をMCPサーバとして公開するためのtool関数群。

mcp SDK には依存しない純関数として実装する。mcp_server.py が
FastMCP registration の薄いラッパとしてこの関数群を呼ぶ。
`http_get` はテスト用に注入可能で、既存の sources アダプタと
同じシグネチャを踏襲する。
"""

from __future__ import annotations

from typing import Any, Callable

from quake_lens.schema import SOURCE_JMA, SOURCE_P2P, parse_iso8601_utc
from quake_lens.sources import jma, p2p, usgs
from quake_lens.stats import bvalue as bvalue_stats
from quake_lens.stats import omori as omori_stats

DEFAULT_BBOX = "24,122,46,146"


def _parse_bbox(s: str) -> tuple[float, float, float, float]:
    parts = s.split(",")
    if len(parts) != 4:
        raise ValueError("bbox must be 'minlat,minlon,maxlat,maxlon'")
    a, b, c, d = (float(x) for x in parts)
    return (a, b, c, d)


def get_recent(
    src: str = SOURCE_P2P,
    limit: int = 10,
    min_scale: int | None = None,
    http_get: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    """直近の地震イベントを取得する。src は 'p2p' か 'jma' のいずれか。

    src='jma' で min_scale を指定すると `ValueError` を送出する
    (JMA list.json には震度スカラーが載らないため CLI の `--src jma`
    と同じ挙動)。返り値は正規化イベントのリスト。
    """
    if src == SOURCE_JMA:
        if min_scale is not None:
            raise ValueError("min_scale is only supported with src='p2p'")
        return jma.fetch_recent(limit=limit, http_get=http_get)
    if src == SOURCE_P2P:
        return p2p.fetch_recent(limit=limit, min_scale=min_scale, http_get=http_get)
    raise ValueError(f"unknown src: {src!r} (expected 'p2p' or 'jma')")


def get_catalog(
    start: str | None = None,
    end: str | None = None,
    min_mag: float | None = None,
    bbox: str = DEFAULT_BBOX,
    http_get: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    """USGSカタログを取得する。bbox は 'minlat,minlon,maxlat,maxlon' の文字列。"""
    box = _parse_bbox(bbox) if bbox else None
    return usgs.fetch_catalog(
        start=start, end=end, min_mag=min_mag, bbox=box, http_get=http_get
    )


def estimate_bvalue(
    mc: float,
    start: str | None = None,
    end: str | None = None,
    min_mag: float | None = None,
    bbox: str = DEFAULT_BBOX,
    http_get: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """USGSカタログを取得し、Gutenberg-Richter b値を Aki MLE で推定する。

    tool内部でカタログを取得することで、巨大なイベント配列を LLM
    コンテキスト経由で往復させずに済ませる。返り値には統計値と、
    取得したイベント総数 `n_events_fetched` を含める (推定に用いた
    件数は `n`、これは Mc 以上のイベント数)。
    """
    events = get_catalog(
        start=start, end=end, min_mag=min_mag, bbox=bbox, http_get=http_get
    )
    mags = [e["mag"] for e in events if "mag" in e]
    result = bvalue_stats.estimate(mags, mc=mc)
    return {**result, "n_events_fetched": len(events)}


def fit_omori(
    mainshock: str,
    start: str | None = None,
    end: str | None = None,
    min_mag: float | None = None,
    bbox: str = DEFAULT_BBOX,
    http_get: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """USGSカタログを取得し、本震以降の余震系列に修正大森則をフィットする。

    mainshock は ISO8601 の本震時刻。tool内部でカタログを取得し、
    mainshock 以降のイベントだけを経過日数に変換して `omori.fit` に
    渡す。返り値には統計値と、取得したイベント総数 `n_events_fetched`
    を含める (フィットに用いた件数は `n`)。
    """
    mainshock_dt = parse_iso8601_utc(mainshock)
    events = get_catalog(
        start=start, end=end, min_mag=min_mag, bbox=bbox, http_get=http_get
    )
    times: list[float] = []
    for e in events:
        when = parse_iso8601_utc(e["time"])
        dt_days = (when - mainshock_dt).total_seconds() / 86400.0
        if dt_days > 0:
            times.append(dt_days)
    result = omori_stats.fit(times)
    return {**result, "n_events_fetched": len(events)}
