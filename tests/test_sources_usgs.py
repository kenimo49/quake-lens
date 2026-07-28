from pathlib import Path

from quake_lens.sources import usgs

FIXTURE = Path(__file__).parent / "fixtures" / "usgs_catalog.json"


def _http_get_fixture(url: str) -> bytes:
    return FIXTURE.read_bytes()


def test_fetch_catalog_parses_fixture():
    events = usgs.fetch_catalog(http_get=_http_get_fixture)
    assert len(events) == 3
    assert all(e["source"] == "usgs" for e in events)
    e0 = events[0]
    assert e0["mag"] == 5.2
    assert e0["lat"] == 37.5
    assert e0["lon"] == 140.9
    assert e0["depth_km"] == 30.0
    assert e0["time"].endswith("Z")


def test_build_url_contains_bbox_and_geojson():
    url = usgs.build_url(
        start="2024-01-01", end="2024-02-01", min_mag=4.0, bbox=(24.0, 122.0, 46.0, 146.0)
    )
    assert "format=geojson" in url
    assert "minlatitude=24" in url
    assert "maxlongitude=146" in url
    assert "minmagnitude=4.0" in url
    assert "starttime=2024-01-01" in url
