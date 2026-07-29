import pytest

pytest.importorskip("mcp")

from quake_lens import mcp_server  # noqa: E402


def test_fastmcp_instance_exists():
    assert mcp_server.mcp is not None


def test_main_is_callable():
    assert callable(mcp_server.main)
