import math
from pathlib import Path

import pytest

from quake_lens.sources import jma

FIXTURE = Path(__file__).parent / "fixtures" / "jma_list.json"


def _http_get_fixture(url: str) -> bytes:
    return FIXTURE.read_bytes()


def test_fetch_recent_parses_fixture():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    # fixture: 6件のうち、cod/mag欠落2件と同一eidの旧報1件はskipされ、残り3件
    assert len(events) == 3
    assert all(e["source"] == "jma" for e in events)


def test_depth_meters_negative_converted_to_km_positive():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    e0 = events[0]
    # cod="+32.6+130.7-10000/" → depth_km = 10.0
    assert e0["lat"] == 32.6
    assert e0["lon"] == 130.7
    assert e0["depth_km"] == 10.0
    assert e0["mag"] == 4.6
    assert e0["place"] == "熊本県熊本地方"
    # 2026-07-29T18:23:00+09:00 -> 09:23 UTC
    assert e0["time"] == "2026-07-29T09:23:00Z"
    assert e0["time"].endswith("Z")


def test_parse_cod_shallow_plus_zero_normalized():
    # ごく浅い地震は実APIで `+0` (正のゼロ) と表記される。素直に符号反転すると
    # -0.0 になり table 表示が「-0.0」に崩れるため、正のゼロへ正規化する
    parsed = jma._parse_cod("+32.6+130.7+0/")
    assert parsed is not None
    _, _, depth_km = parsed
    assert depth_km == 0.0
    assert math.copysign(1.0, depth_km) == 1.0


def test_sexagesimal_cod_converted_to_decimal_degrees():
    # JMAは精査済み震源で度分表記を混ぜてくる (2026-07-28 熊本 M7.1 が実例)。
    # 度としてそのまま読むと lat=3237.5 / lon=13040.7 という地球外の座標になる
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    m71 = [e for e in events if e["mag"] == 7.1]
    assert len(m71) == 1
    # +3237.5 → 32度37.5分 = 32.625 / +13040.7 → 130度40.7分 = 130.67833...
    assert m71[0]["lat"] == pytest.approx(32.625)
    assert m71[0]["lon"] == pytest.approx(130.6783333, abs=1e-6)
    assert m71[0]["depth_km"] == 16.0


def test_parse_angle_handles_each_iso6709_form():
    # 度 / 度分 / 度分秒。緯度は度部分2桁、経度は3桁
    assert jma._parse_angle("+32.6", 2) == pytest.approx(32.6)
    assert jma._parse_angle("+3237.5", 2) == pytest.approx(32.625)
    assert jma._parse_angle("+323730", 2) == pytest.approx(32.625)
    assert jma._parse_angle("+130.7", 3) == pytest.approx(130.7)
    assert jma._parse_angle("+13040.7", 3) == pytest.approx(130.6783333, abs=1e-6)
    assert jma._parse_angle("+1304040.8", 3) == pytest.approx(130.678, abs=1e-6)


def test_parse_angle_handles_negative_tokens():
    # JMAは国外の地震も返すため南緯・西経が来る (例: 中米 lon=-76.3)。
    # 符号は度分秒に展開する前に切り離す
    assert jma._parse_angle("-32.6", 2) == pytest.approx(-32.6)
    assert jma._parse_angle("-3237.5", 2) == pytest.approx(-32.625)
    assert jma._parse_angle("-76.3", 3) == pytest.approx(-76.3)
    assert jma._parse_angle("-13040.7", 3) == pytest.approx(-130.6783333, abs=1e-6)
    assert jma._parse_angle("-1304040.8", 3) == pytest.approx(-130.678, abs=1e-6)


def test_parse_angle_rejects_malformed_values():
    # 分・秒が60以上、および度分秒より長い整数部は不正
    assert jma._parse_angle("+3270.0", 2) is None
    assert jma._parse_angle("+323770", 2) is None
    assert jma._parse_angle("+12345678", 2) is None


def test_parse_cod_rejects_out_of_range_coordinates():
    # 桁数判定を抜けても地球上に無い座標は通さない
    assert jma._parse_cod("+9137.5+13040.7-10000/") is None
    assert jma._parse_cod("+3237.5+19040.7-10000/") is None


def test_parse_drops_events_with_unparsable_coordinates():
    # 座標が解決できない要素は、壊れた値のままイベント化せずskipする
    # (cod/mag欠落と同じ扱い)。統計側に地球外の震央が流れないようにするため
    payload = [
        {
            "eid": "1",
            "at": "2026-07-28T16:27:00+09:00",
            "anm": "範囲外",
            "mag": "7.1",
            "cod": "+9137.5+13040.7-16000/",
        },
        {
            "eid": "2",
            "at": "2026-07-28T16:28:00+09:00",
            "anm": "分が60以上",
            "mag": "5.0",
            "cod": "+3270.0+13040.7-16000/",
        },
        {
            "eid": "3",
            "at": "2026-07-28T16:29:00+09:00",
            "anm": "正常",
            "mag": "4.0",
            "cod": "+3237.5+13040.7-16000/",
        },
    ]
    events = jma.parse(payload)
    assert [e["place"] for e in events] == ["正常"]


def test_skips_items_missing_cod_or_mag():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    # 震度速報(codなし)と cod=""/mag="" の要素はどちらもskip
    places = [e["place"] for e in events]
    assert "石川県能登地方" not in places
    assert "岩手県沖" not in places


def test_dedupe_by_eid_keeps_first():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    # 実APIのlist.jsonはrdt降順 (新しい報が先頭) なので、同一eidの最初の
    # 1件を採用する = 精査済みの最新報 (ser=2, M4.6) を採用する意味になる。
    # 旧報 (ser=1, M4.5) は捨てられる
    dedupe_target = [e for e in events if e["mag"] in (4.5, 4.6)]
    assert len(dedupe_target) == 1
    assert dedupe_target[0]["mag"] == 4.6


def test_limit_applies_after_filtering():
    events = jma.fetch_recent(limit=1, http_get=_http_get_fixture)
    assert len(events) == 1
    assert events[0]["place"] == "熊本県熊本地方"
