from pathlib import Path

from quake_lens.sources import jma

FIXTURE = Path(__file__).parent / "fixtures" / "jma_list.json"


def _http_get_fixture(url: str) -> bytes:
    return FIXTURE.read_bytes()


def test_fetch_recent_parses_fixture():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    # fixture: 5件のうち、cod/mag欠落2件と同一eid続報1件はskipされ、残り2件
    assert len(events) == 2
    assert all(e["source"] == "jma" for e in events)


def test_depth_meters_negative_converted_to_km_positive():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    e0 = events[0]
    # cod="+32.6+130.7-10000/" → depth_km = 10.0
    assert e0["lat"] == 32.6
    assert e0["lon"] == 130.7
    assert e0["depth_km"] == 10.0
    assert e0["mag"] == 4.5
    assert e0["place"] == "熊本県熊本地方"
    # 2026-07-29T18:23:00+09:00 -> 09:23 UTC
    assert e0["time"] == "2026-07-29T09:23:00Z"
    assert e0["time"].endswith("Z")


def test_skips_items_missing_cod_or_mag():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    # 震度速報(codなし)と cod=""/mag="" の要素はどちらもskip
    places = [e["place"] for e in events]
    assert "石川県能登地方" not in places
    assert "岩手県沖" not in places


def test_dedupe_by_eid_keeps_first():
    events = jma.fetch_recent(limit=10, http_get=_http_get_fixture)
    # 同一eid "20260729180000" の続報(18:25)は採用されず、18:23の1件だけ
    kumamoto = [e for e in events if e["place"] == "熊本県熊本地方"]
    assert len(kumamoto) == 1
    assert kumamoto[0]["time"] == "2026-07-29T09:23:00Z"


def test_limit_applies_after_filtering():
    events = jma.fetch_recent(limit=1, http_get=_http_get_fixture)
    assert len(events) == 1
    assert events[0]["place"] == "熊本県熊本地方"
