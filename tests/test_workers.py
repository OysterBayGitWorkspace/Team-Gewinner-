import json
import subprocess

import pytest

from pulse import workers as W

SCHEMA = {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"], "additionalProperties": False}


def spec(**kw):
    base = dict(name="t", prompt="p", schema=SCHEMA, allowed_tools=["WebSearch"], use_jarvis=False, max_turns=2)
    base.update(kw)
    return W.WorkerSpec(**base)


def fake_runner(stdout: str, returncode: int = 0, stderr: str = ""):
    def _run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
    return _run


def cli_payload(**over):
    p = {"is_error": False, "structured_output": {"n": 1}, "total_cost_usd": 0.01, "num_turns": 2}
    p.update(over)
    return json.dumps(p)


def test_happy_path(tmp_path):
    r = W.run_worker(spec(), None, tmp_path, runner=fake_runner(cli_payload()))
    assert r.ok and r.data == {"n": 1} and r.cost_usd == 0.01 and r.turns == 2
    assert (tmp_path / "t.raw.json").exists()


def test_auth_error_is_classified():
    r = W.run_worker(spec(), None, None, runner=fake_runner(cli_payload(is_error=True, structured_output=None,
                                                                          result="Failed to authenticate: OAuth session expired")))
    assert not r.ok and r.error_kind == "auth"


def test_generic_error():
    r = W.run_worker(spec(), None, None, runner=fake_runner(cli_payload(is_error=True, structured_output=None, result="boom")))
    assert r.error_kind == "error" and "boom" in r.error


def test_max_turns_incomplete():
    r = W.run_worker(spec(), None, None, runner=fake_runner(cli_payload(structured_output=None, stop_reason="max_turns")))
    assert r.error_kind == "incomplete"


def test_max_turns_subtype_with_denials_is_incomplete_and_names_tools():
    payload = cli_payload(is_error=True, structured_output=None, subtype="error_max_turns", terminal_reason="max_turns",
                          result=None, num_turns=7,
                          permission_denials=[{"tool_name": "Bash"}, {"tool_name": "Write"}, {"tool_name": "Bash"}])
    r = W.run_worker(spec(), None, None, runner=fake_runner(payload))
    assert r.error_kind == "incomplete" and "Bash, Write" in r.error and "7" in r.error


def test_error_without_result_text_still_has_detail():
    r = W.run_worker(spec(), None, None, runner=fake_runner(cli_payload(is_error=True, structured_output=None, result=None, subtype="error_during_execution")))
    assert r.error_kind == "error" and "error_during_execution" in r.error


def test_no_structured_output_is_schema_error():
    r = W.run_worker(spec(), None, None, runner=fake_runner(cli_payload(structured_output=None)))
    assert r.error_kind == "schema"


def test_schema_violation():
    r = W.run_worker(spec(), None, None, runner=fake_runner(cli_payload(structured_output={"n": "one"})))
    assert r.error_kind == "schema" and "at ['n']" in r.error


def test_non_json_stdout():
    r = W.run_worker(spec(), None, None, runner=fake_runner("not json", returncode=1, stderr="crash"))
    assert r.error_kind == "schema" and "crash" in r.error


def test_timeout():
    def _run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
    r = W.run_worker(spec(timeout_s=1), None, None, runner=_run)
    assert r.error_kind == "timeout"


def test_tool_outside_universe_refused():
    with pytest.raises(ValueError):
        W.build_argv(spec(allowed_tools=["mcp__jarvis__affinity_update_field"]), None)


def test_jarvis_requires_mcp_config():
    with pytest.raises(ValueError):
        W.build_argv(spec(use_jarvis=True, allowed_tools=["mcp__jarvis__knowledge_search"]), None)


def test_argv_shape(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("{}")
    argv = W.build_argv(spec(use_jarvis=True, allowed_tools=["mcp__jarvis__knowledge_search", "WebSearch"]), cfg)
    assert argv[:2] == [W.CLAUDE_BIN, "-p"] and "--strict-mcp-config" in argv and "--mcp-config" in argv
    assert json.loads(argv[argv.index("--json-schema") + 1]) == SCHEMA


def test_run_many_aborts_on_auth():
    runner = fake_runner(cli_payload(is_error=True, structured_output=None, result="Failed to authenticate"))
    with pytest.raises(W.WorkerAuthError):
        W.run_many([spec(name="a"), spec(name="b")], None, None, max_workers=2, runner=runner)


def test_run_many_collects():
    res = W.run_many([spec(name="a"), spec(name="b")], None, None, max_workers=2, runner=fake_runner(cli_payload()))
    assert set(res) == {"a", "b"} and all(r.ok for r in res.values())


def test_clean_env_drops_nesting_and_proxy(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://proxy")
    env = W._clean_env()
    assert "CLAUDECODE" not in env and "ANTHROPIC_BASE_URL" not in env
