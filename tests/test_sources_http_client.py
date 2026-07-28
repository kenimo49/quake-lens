"""http_client のUA付与をオフラインで検証する（実際の urlopen は呼ばない）。"""

from quake_lens import __version__
from quake_lens.sources import http_client


def test_build_request_sets_user_agent():
    """組み立てた `Request` に `quake-lens/バージョン` のUAが載る（P2P 403対策の本丸）。"""
    req = http_client.build_request("https://example.com/api")
    ua = req.get_header("User-agent")
    assert ua is not None
    assert ua.startswith(f"quake-lens/{__version__}")


def test_user_agent_constant_includes_version():
    """UA文字列にパッケージバージョンが埋め込まれ、リリース時に自動追随する。"""
    assert f"quake-lens/{__version__}" in http_client.USER_AGENT


def test_build_request_preserves_url():
    """`Request` 化でURL（クエリ文字列含む）が変形しない。"""
    url = "https://api.p2pquake.net/v2/history?codes=551&limit=10"
    req = http_client.build_request(url)
    assert req.full_url == url
