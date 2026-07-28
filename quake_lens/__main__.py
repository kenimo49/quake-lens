"""CLIエントリポイント: quake-lens {recent, catalog, bvalue, omori}。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from quake_lens import __version__
from quake_lens.format import format_bvalue, format_events, format_omori
from quake_lens.schema import parse_iso8601_utc
from quake_lens.sources import p2p, usgs
from quake_lens.stats import bvalue as bvalue_stats
from quake_lens.stats import omori as omori_stats


def _add_format_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=["table", "json"], default="table")


def _add_input_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", nargs="?", default="-", help="イベントJSONパス or '-' (stdin)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quake-lens",
        description="公開地震データの取得と統計分析（b値・大森則フィット）",
    )
    parser.add_argument("--version", action="version", version=f"quake-lens {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_recent = sub.add_parser("recent", help="直近の地震リスト (P2P地震情報)")
    p_recent.add_argument("--limit", type=int, default=10, help="件数上限 (default: 10)")
    p_recent.add_argument(
        "--min-scale",
        type=int,
        default=None,
        help="P2Pのscale値で震度フィルタ (例: 30=震度3)",
    )
    _add_format_arg(p_recent)
    p_recent.set_defaults(func=cmd_recent)

    p_catalog = sub.add_parser("catalog", help="USGSカタログ取得")
    p_catalog.add_argument("--start", default=None, help="開始時刻 (ISO8601)")
    p_catalog.add_argument("--end", default=None, help="終了時刻 (ISO8601)")
    p_catalog.add_argument("--min-mag", type=float, default=None)
    p_catalog.add_argument(
        "--bbox",
        default="24,122,46,146",
        help="minlat,minlon,maxlat,maxlon (default: 日本周辺)",
    )
    _add_format_arg(p_catalog)
    p_catalog.set_defaults(func=cmd_catalog)

    p_bvalue = sub.add_parser("bvalue", help="Gutenberg-Richter b値推定 (Aki MLE)")
    _add_input_arg(p_bvalue)
    p_bvalue.add_argument("--mc", type=float, default=None, help="completeness magnitude (必須)")
    _add_format_arg(p_bvalue)
    p_bvalue.set_defaults(func=cmd_bvalue)

    p_omori = sub.add_parser("omori", help="修正大森則フィット (Ogata MLE)")
    _add_input_arg(p_omori)
    p_omori.add_argument("--mainshock", default=None, help="本震時刻 (ISO8601, 必須)")
    _add_format_arg(p_omori)
    p_omori.set_defaults(func=cmd_omori)

    return parser


def _load_events(path: str) -> list[dict[str, Any]]:
    if path == "-":
        data = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
    obj = json.loads(data)
    if not isinstance(obj, list):
        raise ValueError("input JSON must be a list of events")
    return obj


def _parse_bbox(s: str) -> tuple[float, float, float, float]:
    parts = s.split(",")
    if len(parts) != 4:
        raise ValueError("--bbox must be 'minlat,minlon,maxlat,maxlon'")
    a, b, c, d = (float(x) for x in parts)
    return (a, b, c, d)


def cmd_recent(args, http_get=None) -> int:
    events = p2p.fetch_recent(limit=args.limit, min_scale=args.min_scale, http_get=http_get)
    print(format_events(events, args.format))
    return 0


def cmd_catalog(args, http_get=None) -> int:
    bbox = _parse_bbox(args.bbox) if args.bbox else None
    events = usgs.fetch_catalog(
        start=args.start,
        end=args.end,
        min_mag=args.min_mag,
        bbox=bbox,
        http_get=http_get,
    )
    print(format_events(events, args.format))
    return 0


def cmd_bvalue(args) -> int:
    if args.mc is None:
        print("error: --mc is required", file=sys.stderr)
        return 1
    events = _load_events(args.input)
    mags = [e["mag"] for e in events if "mag" in e]
    result = bvalue_stats.estimate(mags, mc=args.mc)
    print(format_bvalue(result, args.format))
    return 0


def cmd_omori(args) -> int:
    if args.mainshock is None:
        print("error: --mainshock is required", file=sys.stderr)
        return 1
    mainshock_dt = parse_iso8601_utc(args.mainshock)
    events = _load_events(args.input)
    times = []
    for e in events:
        when = parse_iso8601_utc(e["time"])
        dt_days = (when - mainshock_dt).total_seconds() / 86400.0
        if dt_days > 0:
            times.append(dt_days)
    result = omori_stats.fit(times)
    print(format_omori(result, args.format))
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    try:
        return func(args)
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
