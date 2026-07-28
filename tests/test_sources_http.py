from quake_lens import __version__
from quake_lens.sources import http


def test_build_request_sets_user_agent():
    req = http.build_request("https://example.com/api")
    ua = req.get_header("User-agent")
    assert ua is not None
    assert ua.startswith(f"quake-lens/{__version__}")


def test_user_agent_constant_includes_version():
    assert f"quake-lens/{__version__}" in http.USER_AGENT


def test_build_request_preserves_url():
    url = "https://api.p2pquake.net/v2/history?codes=551&limit=10"
    req = http.build_request(url)
    assert req.full_url == url
