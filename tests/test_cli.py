import io
import json
import math
import random
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

from quake_lens.__main__ import build_parser, cmd_catalog, cmd_recent, main

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _p2p_http_get(url):
    return (FIXTURE_DIR / "p2p_recent.json").read_bytes()


def _usgs_http_get(url):
    return (FIXTURE_DIR / "usgs_catalog.json").read_bytes()


@pytest.mark.parametrize("cmd", ["recent", "catalog", "bvalue", "omori"])
def test_subcommand_help_exits_zero(cmd, capsys):
    with pytest.raises(SystemExit) as exc:
        main([cmd, "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "usage" in out.lower()


def test_no_args_prints_help_and_exits_zero(capsys):
    rc = main([])
    assert rc == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_cmd_recent_with_fixture(capsys):
    parser = build_parser()
    args = parser.parse_args(["recent", "--format", "json"])
    rc = cmd_recent(args, http_get=_p2p_http_get)
    assert rc == 0
    out = capsys.readouterr().out
    events = json.loads(out)
    assert len(events) == 3
    assert events[0]["source"] == "p2p"


def test_cmd_recent_table_format(capsys):
    parser = build_parser()
    args = parser.parse_args(["recent"])
    rc = cmd_recent(args, http_get=_p2p_http_get)
    assert rc == 0
    out = capsys.readouterr().out
    assert "石川県能登地方" in out
    assert "p2p" in out


def test_cmd_catalog_with_fixture(capsys):
    parser = build_parser()
    args = parser.parse_args(["catalog", "--format", "json"])
    rc = cmd_catalog(args, http_get=_usgs_http_get)
    assert rc == 0
    events = json.loads(capsys.readouterr().out)
    assert len(events) == 3
    assert events[0]["source"] == "usgs"


def test_bvalue_requires_mc(tmp_path, capsys):
    input_file = tmp_path / "events.json"
    input_file.write_text("[]")
    rc = main(["bvalue", str(input_file)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--mc" in err


def test_bvalue_e2e_from_file(tmp_path, capsys):
    rng = random.Random(11)
    beta = 1.0 * math.log(10)
    mc = 2.0
    events = []
    for i in range(4000):
        m = mc - math.log(1 - rng.random()) / beta
        events.append(
            {
                "time": f"2024-01-01T00:{i // 60:02d}:{i % 60:02d}Z",
                "lat": 37.0,
                "lon": 140.0,
                "depth_km": 10.0,
                "mag": m,
                "place": "synthetic",
                "source": "usgs",
            }
        )
    input_file = tmp_path / "events.json"
    input_file.write_text(json.dumps(events))
    rc = main(["bvalue", str(input_file), "--mc", "2.0", "--format", "json"])
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert abs(result["b"] - 1.0) < 0.15


def test_omori_requires_mainshock(tmp_path, capsys):
    input_file = tmp_path / "events.json"
    input_file.write_text("[]")
    rc = main(["omori", str(input_file)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--mainshock" in err


def test_omori_e2e_from_file(tmp_path, capsys):
    from datetime import datetime, timedelta, timezone

    rng = random.Random(321)
    c_true, p_true, T = 0.02, 1.05, 5.0
    a = c_true ** (1 - p_true)
    b = (T + c_true) ** (1 - p_true)
    mainshock = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    events = []
    for _ in range(1500):
        u = rng.random()
        val = a + u * (b - a)
        t_days = val ** (1.0 / (1 - p_true)) - c_true
        when = mainshock + timedelta(seconds=t_days * 86400.0)
        events.append(
            {
                "time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lat": 37.0,
                "lon": 140.0,
                "depth_km": 10.0,
                "mag": 3.0,
                "place": "synth",
                "source": "usgs",
            }
        )
    input_file = tmp_path / "events.json"
    input_file.write_text(json.dumps(events))
    rc = main(
        [
            "omori",
            str(input_file),
            "--mainshock",
            "2024-01-01T00:00:00Z",
            "--format",
            "json",
        ]
    )
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert abs(result["p"] - p_true) < 0.15


def test_bvalue_stdin(capsys, monkeypatch):
    import sys as _sys

    events = [{"mag": 2.0}, {"mag": 2.5}, {"mag": 3.0}, {"mag": 3.5}]
    monkeypatch.setattr(_sys, "stdin", io.StringIO(json.dumps(events)))
    rc = main(["bvalue", "-", "--mc", "2.0", "--format", "json"])
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["n"] == 4
