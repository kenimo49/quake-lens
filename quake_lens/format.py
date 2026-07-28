"""Output formatters for normalized events and stat results."""

from __future__ import annotations

import json
from typing import Any, Iterable


def format_events(events: list[dict[str, Any]], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(events, ensure_ascii=False, indent=2)
    if fmt == "table":
        return _events_table(events)
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


def format_bvalue(result: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    if fmt == "table":
        return (
            f"b       = {result['b']:.4f}\n"
            f"se      = {result['se']:.4f}\n"
            f"n_used  = {result['n']}\n"
            f"mc      = {result['mc']:.2f}\n"
            f"mean_m  = {result['mean_m']:.3f}"
        )
    raise ValueError(f"unknown format: {fmt}")


def format_omori(result: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    if fmt == "table":
        return (
            f"K       = {result['K']:.4f}\n"
            f"c       = {result['c']:.4f}\n"
            f"p       = {result['p']:.4f}\n"
            f"logL    = {result['logL']:.4f}\n"
            f"n_used  = {result['n']}\n"
            f"window  = [{result['t_start']:.4f}, {result['t_end']:.4f}] days"
        )
    raise ValueError(f"unknown format: {fmt}")
