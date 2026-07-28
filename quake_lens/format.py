"""正規化イベントと統計結果を整形するフォーマッタ群。"""

from __future__ import annotations

import json
from typing import Any, Iterable


def format_events(events: list[dict[str, Any]], fmt: str) -> str:
    if fmt == "json":
        return _to_json(events)
    if fmt == "table":
        return _events_table(events)
    raise ValueError(f"unknown format: {fmt}")


def format_bvalue(result: dict[str, Any], fmt: str) -> str:
    return _render_kv(
        result,
        [
            ("b", result["b"], ".4f"),
            ("se", result["se"], ".4f"),
            ("n_used", result["n"], ""),
            ("mc", result["mc"], ".2f"),
            ("mean_m", result["mean_m"], ".3f"),
        ],
        fmt,
    )


def format_omori(result: dict[str, Any], fmt: str) -> str:
    window = f"[{result['t_start']:.4f}, {result['t_end']:.4f}] days"
    return _render_kv(
        result,
        [
            ("K", result["K"], ".4f"),
            ("c", result["c"], ".4f"),
            ("p", result["p"], ".4f"),
            ("logL", result["logL"], ".4f"),
            ("n_used", result["n"], ""),
            ("window", window, ""),
        ],
        fmt,
    )


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_kv(
    payload: dict[str, Any],
    rows: Iterable[tuple[str, Any, str]],
    fmt: str,
) -> str:
    if fmt == "json":
        return _to_json(payload)
    if fmt == "table":
        return "\n".join(f"{label:<8}= {format(value, spec)}" for label, value, spec in rows)
    raise ValueError(f"unknown format: {fmt}")


def _events_table(events: Iterable[dict[str, Any]]) -> str:
    header = f"{'time':<20}  {'lat':>7}  {'lon':>8}  {'depth':>6}  {'mag':>4}  {'src':<4}  place"
    lines = [header]
    for e in events:
        lines.append(
            f"{e['time']:<20}  {e['lat']:>7.3f}  {e['lon']:>8.3f}  "
            f"{e['depth_km']:>6.1f}  {e['mag']:>4.1f}  {e['source']:<4}  {e['place']}"
        )
    return "\n".join(lines)
