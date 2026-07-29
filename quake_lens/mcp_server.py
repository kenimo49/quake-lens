"""stdio MCP サーバ。

mcp_tools の4関数を tool として登録し、`main()` で stdio 経由に
起動する。mcp SDK は optional dependency (`quake-lens[mcp]`) として
提供し、base install の stdlib-only 方針を保つ。

mcp SDK 2.0 で FastMCP は `MCPServer` に改称された (`mcp.server.fastmcp`
モジュールは削除)。デコレータ・run() のAPIは同型なので、import だけ
両対応にする。詳細は docs/mcp.md を参照。
"""

from __future__ import annotations

from typing import Any

try:  # mcp >= 2.0
    from mcp.server import MCPServer
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

from quake_lens import mcp_tools

mcp = MCPServer("quake-lens")


@mcp.tool()
def get_recent(
    src: str = "p2p",
    limit: int = 10,
    min_scale: int | None = None,
) -> list[dict[str, Any]]:
    """直近の地震イベントを取得する (src: 'p2p' または 'jma')。"""
    return mcp_tools.get_recent(src=src, limit=limit, min_scale=min_scale)


@mcp.tool()
def get_catalog(
    start: str | None = None,
    end: str | None = None,
    min_mag: float | None = None,
    bbox: str = mcp_tools.DEFAULT_BBOX,
) -> list[dict[str, Any]]:
    """USGSカタログを取得する。bbox は 'minlat,minlon,maxlat,maxlon'。"""
    return mcp_tools.get_catalog(start=start, end=end, min_mag=min_mag, bbox=bbox)


@mcp.tool()
def estimate_bvalue(
    mc: float,
    start: str | None = None,
    end: str | None = None,
    min_mag: float | None = None,
    bbox: str = mcp_tools.DEFAULT_BBOX,
) -> dict[str, Any]:
    """USGSカタログを取得し、Gutenberg-Richter b値を Aki MLE で推定する。"""
    return mcp_tools.estimate_bvalue(
        mc=mc, start=start, end=end, min_mag=min_mag, bbox=bbox
    )


@mcp.tool()
def fit_omori(
    mainshock: str,
    start: str | None = None,
    end: str | None = None,
    min_mag: float | None = None,
    bbox: str = mcp_tools.DEFAULT_BBOX,
) -> dict[str, Any]:
    """USGSカタログを取得し、本震以降の余震系列に修正大森則をフィットする。"""
    return mcp_tools.fit_omori(
        mainshock=mainshock, start=start, end=end, min_mag=min_mag, bbox=bbox
    )


def main() -> None:
    """MCPサーバをstdioで起動する (entry point: `quake-lens-mcp`)。"""
    mcp.run()


if __name__ == "__main__":
    main()
