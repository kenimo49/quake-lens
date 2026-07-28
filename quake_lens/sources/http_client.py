"""共通HTTP GETヘルパー。User-Agentヘッダを必ず付与する。

P2Pなど一部のAPIはurllibのデフォルトUA (`Python-urllib/3.x`) を403で拒否するため、
明示的にプロジェクト固有のUAをRequestヘッダに設定する。
"""

from __future__ import annotations

import urllib.request

from quake_lens import __version__

# `製品名/バージョン (+参照URL)` はGooglebot等が使うUA慣習。`+URL` は
# 「このクライアントの詳細・連絡先はここ」をAPI運営者に開示するための表記。
USER_AGENT = f"quake-lens/{__version__} (+https://github.com/kenimo49/quake-lens)"


def build_request(url: str) -> urllib.request.Request:
    """`User-Agent`ヘッダを付与した `Request` を組み立てる。

    ネットワークアクセスはしないので、UAヘッダの内容は戻り値の
    `Request` に対してオフラインでテストできる。
    """
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def http_get(url: str, timeout: float = 30.0) -> bytes:
    """URLをGETしてレスポンスボディを返す。

    必ず `USER_AGENT` を付与する。各sourceの `_default_http_get` は
    素の `urllib.request.urlopen` ではなくこの関数を経由すること。
    """
    req = build_request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()
