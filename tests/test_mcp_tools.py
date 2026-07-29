import json
import math
import random
from pathlib import Path

import pytest

from quake_lens import mcp_tools

FIX = Path(__file__).parent / "fixtures"


def _http_get_from(path: Path):
    def _get(url: str) -> bytes:
        return path.read_bytes()
    return _get


def test_get_recent_p2p_uses_p2p_source():
    # src引数のルーティング検証: 'p2p' が p2p アダプタに届き、
    # 正規化イベント (source='p2p') が返ること
    events = mcp_tools.get_recent(
        src="p2p", limit=10, http_get=_http_get_from(FIX / "p2p_recent.json")
    )
    assert len(events) == 3
    assert all(e["source"] == "p2p" for e in events)


def test_get_recent_p2p_min_scale_filters():
    # min_scale が p2p アダプタまで伝播してフィルタが効くこと
    # (fixtureでscale>=50は能登M7.6の1件のみ)
    events = mcp_tools.get_recent(
        src="p2p",
        limit=10,
        min_scale=50,
        http_get=_http_get_from(FIX / "p2p_recent.json"),
    )
    assert len(events) == 1
    assert events[0]["mag"] == 7.6


def test_get_recent_jma_uses_jma_source():
    # src引数のルーティング検証: 'jma' が jma アダプタに届くこと
    events = mcp_tools.get_recent(
        src="jma", limit=10, http_get=_http_get_from(FIX / "jma_list.json")
    )
    assert len(events) == 2
    assert all(e["source"] == "jma" for e in events)


def test_get_recent_jma_rejects_min_scale():
    # CLI の `--src jma --min-scale` ガードと同一挙動を tool 層でも
    # 提供する: min_scale はP2Pのscale値前提なので黙殺せず ValueError
    with pytest.raises(ValueError):
        mcp_tools.get_recent(
            src="jma",
            limit=10,
            min_scale=30,
            http_get=_http_get_from(FIX / "jma_list.json"),
        )


def test_get_recent_unknown_src_raises():
    # 未知の src はネットワークに触れる前に ValueError で弾く
    with pytest.raises(ValueError):
        mcp_tools.get_recent(src="bogus", http_get=lambda u: b"")


def test_get_catalog_uses_usgs_source():
    # get_catalog は USGS アダプタ固定であること
    events = mcp_tools.get_catalog(
        http_get=_http_get_from(FIX / "usgs_catalog.json")
    )
    assert len(events) == 3
    assert all(e["source"] == "usgs" for e in events)


def test_get_catalog_invalid_bbox_raises():
    # bbox は 'minlat,minlon,maxlat,maxlon' の4要素文字列。要素数不正は
    # ネットワークに触れる前に ValueError で弾く
    with pytest.raises(ValueError):
        mcp_tools.get_catalog(bbox="1,2,3", http_get=lambda u: b"")


def _synth_usgs_catalog_geojson(mags, base_time_ms=1704110400000):
    """指定マグニチュード列から USGS GeoJSON レスポンスを合成する。"""
    features = []
    for i, m in enumerate(mags):
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "mag": m,
                    "place": "synthetic",
                    "time": base_time_ms + i * 1000,
                    "type": "earthquake",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [140.0, 37.0, 20.0],
                },
                "id": f"syn{i}",
            }
        )
    return {"type": "FeatureCollection", "features": features}


def test_estimate_bvalue_fetches_and_estimates():
    # 中核の設計検証: イベント配列を引数に取らず、tool 内部で取得→推定
    # まで完結すること (巨大配列をLLMコンテキストに往復させない)。
    # b=1.0の指数分布から合成したカタログで推定値が回復し、
    # n (推定使用数) と n_events_fetched (取得総数) が区別されて返ること
    rng = random.Random(42)
    mc = 2.0
    b = 1.0
    beta = b * math.log(10)
    mags = [mc - math.log(1.0 - rng.random()) / beta for _ in range(1000)]
    payload = json.dumps(_synth_usgs_catalog_geojson(mags)).encode()

    def _http_get(url: str) -> bytes:
        return payload

    result = mcp_tools.estimate_bvalue(mc=mc, http_get=_http_get)
    assert abs(result["b"] - 1.0) < 0.2
    assert result["n"] == 1000
    assert result["n_events_fetched"] == 1000
    assert result["mc"] == mc


def _inverse_cdf(u, c, p, T):
    a = c ** (1 - p)
    b = (T + c) ** (1 - p)
    val = a + u * (b - a)
    return val ** (1.0 / (1 - p)) - c


def test_fit_omori_fetches_and_fits():
    # estimate_bvalue と同じ設計検証の omori 版: tool 内部で取得→
    # 本震以降の経過日数変換→フィットまで完結し、真値p=1.1が回復すること
    rng = random.Random(123)
    c_true, p_true, T = 0.01, 1.1, 10.0
    n = 500
    days_after = sorted(_inverse_cdf(rng.random(), c_true, p_true, T) for _ in range(n))
    # 本震時刻を epoch 0 (1970-01-01T00:00:00Z) に置き、余震時刻をそこからの
    # 経過秒に変換して USGS `time` (ms) を組み立てる
    mainshock_iso = "1970-01-01T00:00:00Z"
    mags_placeholder = [3.0] * n
    payload_dict = _synth_usgs_catalog_geojson(mags_placeholder, base_time_ms=0)
    for feat, d in zip(payload_dict["features"], days_after):
        feat["properties"]["time"] = int(d * 86400.0 * 1000.0)
    payload = json.dumps(payload_dict).encode()

    def _http_get(url: str) -> bytes:
        return payload

    result = mcp_tools.fit_omori(mainshock=mainshock_iso, http_get=_http_get)
    assert abs(result["p"] - p_true) < 0.2
    assert result["n"] == n
    assert result["n_events_fetched"] == n
    assert result["c"] > 0
    assert result["K"] > 0


def test_fit_omori_filters_events_before_mainshock():
    # 本震より前のイベントは余震ではないので除外される。fixtureの3件は
    # 全て mainshock (2000年) より前 (1970年) → 余震0件となり、
    # omori.fit の n>=3 検証が ValueError を出すことで除外を確認する
    # 本震より前のイベントは除外される
    payload_dict = _synth_usgs_catalog_geojson([3.0, 3.1, 3.2], base_time_ms=0)
    # base_time_ms=0 (1970-01-01) より後、mainshock=2000-01-01 より前
    payload = json.dumps(payload_dict).encode()

    def _http_get(url: str) -> bytes:
        return payload

    with pytest.raises(ValueError):
        mcp_tools.fit_omori(mainshock="2000-01-01T00:00:00Z", http_get=_http_get)
