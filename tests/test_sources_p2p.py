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


def test_parse_skips_sentinel_hypocenter():
    # P2P APIは震源未確定の電文 (震度速報 ScalePrompt 等) を lat/lon=-200,
    # magnitude=-1 のセンチネル値で返してくるので、None チェックとは別に
    # これを skip する
    payload = [
        {
            "code": 551,
            "earthquake": {
                "time": "2024-06-01 12:00:00.000",
                "hypocenter": {
                    "name": "",
                    "latitude": -200,
                    "longitude": -200,
                    "depth": -1,
                    "magnitude": -1,
                },
                "maxScale": 30,
            },
        }
    ]
    assert p2p.parse(payload) == []


def test_parse_dedupes_by_earthquake_time():
    # 同一地震の複数電文 (ScalePrompt → Destination → DetailScale) は
    # 全て同じ earthquake.time を持つため、最初の1件のみ採用する
    payload = [
        {
            "code": 551,
            "earthquake": {
                "time": "2024-06-01 12:00:00.000",
                "hypocenter": {
                    "name": "詳報",
                    "latitude": 35.0,
                    "longitude": 139.0,
                    "depth": 20,
                    "magnitude": 5.0,
                },
                "maxScale": 40,
            },
        },
        {
            "code": 551,
            "earthquake": {
                "time": "2024-06-01 12:00:00.000",
                "hypocenter": {
                    "name": "続報",
                    "latitude": 35.1,
                    "longitude": 139.1,
                    "depth": 25,
                    "magnitude": 5.1,
                },
                "maxScale": 40,
            },
        },
    ]
    events = p2p.parse(payload)
    assert len(events) == 1
    assert events[0]["place"] == "詳報"


def test_parse_preserves_depth_unknown_sentinel():
    # depth の `-1` は「深さ不明」を意味する正当な値なので除外せず
    # そのまま depth_km=-1.0 として通す (既存挙動を維持)
    payload = [
        {
            "code": 551,
            "earthquake": {
                "time": "2024-06-01 12:00:00.000",
                "hypocenter": {
                    "name": "test",
                    "latitude": 35.0,
                    "longitude": 139.0,
                    "depth": -1,
                    "magnitude": 4.0,
                },
                "maxScale": 20,
            },
        }
    ]
    events = p2p.parse(payload)
    assert len(events) == 1
    assert events[0]["depth_km"] == -1.0
