from pathlib import Path

from quake_lens.sources import p2p

FIXTURE = Path(__file__).parent / "fixtures" / "p2p_recent.json"


def _http_get_fixture(url: str) -> bytes:
    return FIXTURE.read_bytes()


def test_fetch_recent_parses_fixture():
    events = p2p.fetch_recent(limit=10, http_get=_http_get_fixture)
    assert len(events) == 3
    e0 = events[0]
    assert e0["source"] == "p2p"
    assert e0["mag"] == 7.6
    assert e0["place"] == "石川県能登地方"
    assert e0["time"].endswith("Z")
    # 2024-01-01 16:10 JST -> 07:10 UTC
    assert e0["time"] == "2024-01-01T07:10:00Z"


def test_fetch_recent_min_scale_filter():
    events = p2p.fetch_recent(limit=10, min_scale=50, http_get=_http_get_fixture)
    assert len(events) == 1
    assert events[0]["mag"] == 7.6


def test_build_url_contains_params():
    url = p2p.build_url(limit=5)
    assert "codes=551" in url
    assert "limit=5" in url
