import quake_lens
from quake_lens.__main__ import main


def test_version_defined():
    assert quake_lens.__version__


def test_cli_no_args_exits_zero():
    assert main([]) == 0
