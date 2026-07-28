"""共通HTTP GETヘルパー。User-Agentヘッダを必ず付与する。

P2Pなど一部のAPIはurllibのデフォルトUA (`Python-urllib/3.x`) を403で拒否するため、
明示的にプロジェクト固有のUAをRequestヘッダに設定する。
"""

from __future__ import annotations

import urllib.request

from quake_lens import __version__

USER_AGENT = f"quake-lens/{__version__} (+https://github.com/kenimo49/quake-lens)"


def build_request(url: str) -> urllib.request.Request:
    """`User-Agent`ヘッダを付与した `Request` を組み立てる（ネットワーク非依存）。"""
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def http_get(url: str, timeout: float = 30.0) -> bytes:
    req = build_request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()
