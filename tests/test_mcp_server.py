import pytest

# mcp SDK は optional dependency (`quake-lens[mcp]`)。base install の環境では
# このファイル全体を skip し、mcp_tools 側のテストだけでロジックを担保する
pytest.importorskip("mcp")

from quake_lens import mcp_server  # noqa: E402


def test_fastmcp_instance_exists():
    # @mcp.tool() の登録は import 時に走る。tool のシグネチャが FastMCP で
    # スキーマ化できない場合は import 自体が失敗するので、この smoke テストが
    # 「4 tool の登録が通ること」の検証を兼ねる
    assert mcp_server.mcp is not None


def test_registered_tool_names():
    # 登録漏れ・改名事故の検出。mcp_tools 側の関数を増やしても mcp_server の
    # 登録を忘れると LLM クライアントからは見えないため、名前を明示的にピン留め
    import asyncio

    tool_names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert tool_names == {"get_recent", "get_catalog", "estimate_bvalue", "fit_omori"}


def test_main_is_callable():
    # entry point `quake-lens-mcp` (pyproject [project.scripts]) の実体が
    # 呼び出し可能であることの確認。mcp.run() は stdio を掴むため実行はしない
    assert callable(mcp_server.main)
