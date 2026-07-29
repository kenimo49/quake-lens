"""正規化イベントと統計結果を整形するフォーマッタ群。"""

from __future__ import annotations

import json
from typing import Any, Iterable

from .fields import BVALUE_FIELDS, OMORI_FIELDS, FieldSpec, field_value


def format_events(events: list[dict[str, Any]], fmt: str) -> str:
    if fmt == "json":
        return _to_json(events)
    if fmt == "table":
        return _events_table(events)
    raise ValueError(f"unknown format: {fmt}")


def format_bvalue(result: dict[str, Any], fmt: str) -> str:
    return _render_kv(result, BVALUE_FIELDS, fmt)


def format_omori(result: dict[str, Any], fmt: str) -> str:
    return _render_kv(result, OMORI_FIELDS, fmt)


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_kv(
    payload: dict[str, Any],
    fields: Iterable[FieldSpec],
    fmt: str,
) -> str:
    if fmt == "json":
        return _to_json(payload)
    if fmt == "table":
        return "\n".join(
            f"{label:<8}= {format(field_value(payload, source), spec)}"
            for label, source, spec, _ in fields
        )
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
