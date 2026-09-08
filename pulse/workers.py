"""Headless research workers.

Each worker is one `claude -p` subprocess with a strict tool allowlist and a
JSON schema. This module owns the subprocess boundary: it turns every way the
subprocess can fail into a named exception, and never returns unvalidated data.

    ┌──────────┐   argv    ┌────────────┐  stdout json  ┌───────────┐  validate  ┌────────┐
    │ run_worker├──────────▶│ claude -p  ├──────────────▶│ parse     ├───────────▶│ Result │
    └──────────┘           └────────────┘               └───────────┘            └────────┘
                             │ timeout → WorkerTimeout    │ not json → SchemaError
                             │ is_error+auth → WorkerAuthError
                             │ is_error → WorkerError     │ schema fail → SchemaError
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import jsonschema

log = logging.getLogger("pulse.workers")

CLAUDE_BIN = os.environ.get("PULSE_CLAUDE_BIN", "claude")
DEFAULT_MODEL = os.environ.get("PULSE_MODEL", "claude-sonnet-5")
DEFAULT_TIMEOUT_S = int(os.environ.get("PULSE_WORKER_TIMEOUT_S", "420"))

# Tools a worker may ever be granted. Anything else is refused at spawn time.
# Every Jarvis tool here is read-only. The three write tools are never listed.
ALLOWED_TOOL_UNIVERSE = {
    "WebSearch", "WebFetch",
    "mcp__jarvis__crm_list_portfolio", "mcp__jarvis__portfolio_risk_rank",
    "mcp__jarvis__company_profile", "mcp__jarvis__company_current_state",
    "mcp__jarvis__fund_kpis", "mcp__jarvis__knowledge_search",
    "mcp__jarvis__crm_find_similar_companies", "mcp__jarvis__portfolio_valuations",
}


class WorkerError(Exception):
    """Subprocess ran but reported an error."""


class WorkerAuthError(WorkerError):
    """Claude CLI or Jarvis authentication failed. Fatal for the run."""


class WorkerQuotaError(WorkerError):
    """Spend or usage limit reached. Fatal for the run: every remaining worker would fail the same way."""


class WorkerTimeout(WorkerError):
    """Subprocess exceeded the wall-clock budget."""


class WorkerIncomplete(WorkerError):
    """Subprocess hit max turns before producing structured output."""


class SchemaError(WorkerError):
    """Output was not JSON, or did not validate against the schema."""


@dataclass
class WorkerSpec:
    name: str
    prompt: str
    schema: dict
    allowed_tools: list[str]
    use_jarvis: bool
    max_turns: int = 25
    model: str = DEFAULT_MODEL
    timeout_s: int = DEFAULT_TIMEOUT_S


@dataclass
class WorkerResult:
    name: str
    ok: bool
    data: dict | None
    error: str | None
    error_kind: str | None
    duration_s: float
    cost_usd: float
    turns: int
    raw_path: str | None = None
    meta: dict = field(default_factory=dict)


def _clean_env() -> dict[str, str]:
    """Environment for the subprocess.

    Nested Claude Code detection must be disabled or the child refuses to run.
    ANTHROPIC_BASE_URL is dropped so a proxy from the parent session never leaks.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in {"CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "ANTHROPIC_BASE_URL"}}
    return env


def build_argv(spec: WorkerSpec, mcp_config: Path | None) -> list[str]:
    bad = set(spec.allowed_tools) - ALLOWED_TOOL_UNIVERSE
    if bad:
        raise ValueError(f"{spec.name}: tools outside the read-only universe: {sorted(bad)}")
    argv = [
        CLAUDE_BIN, "-p", spec.prompt,
        "--output-format", "json",
        "--json-schema", json.dumps(spec.schema),
        "--max-turns", str(spec.max_turns),
        "--model", spec.model,
        "--strict-mcp-config",
        "--allowedTools", *spec.allowed_tools,
    ]
    if spec.use_jarvis:
        if mcp_config is None:
            raise ValueError(f"{spec.name}: use_jarvis=True but no mcp_config given")
        argv += ["--mcp-config", str(mcp_config)]
    return argv


def _denied(payload: dict) -> str:
    names = sorted({d.get("tool_name", "?") for d in payload.get("permission_denials") or []})
    return f" (denied tool calls: {', '.join(names)})" if names else ""


def _classify(payload: dict) -> tuple[str, str] | None:
    """Return (error_kind, message) if the CLI payload signals a failure."""
    max_turns = (payload.get("subtype") == "error_max_turns" or payload.get("terminal_reason") == "max_turns"
                 or payload.get("stop_reason") == "max_turns")
    if max_turns and payload.get("structured_output") is None:
        return "incomplete", f"max turns ({payload.get('num_turns')}) reached without structured output" + _denied(payload)
    if payload.get("is_error"):
        msg = str(payload.get("result") or "")[:500]
        low = msg.lower()
        if "authenticate" in low or "oauth" in low:
            return "auth", msg
        if "spend limit" in low or "usage limit" in low or "rate limit" in low or "quota" in low or "limit resets" in low:
            return "quota", msg
        errs = payload.get("errors")
        detail = msg or (json.dumps(errs)[:300] if errs else "") or f"subtype={payload.get('subtype')}"
        return "error", detail + _denied(payload)
    if payload.get("structured_output") is None:
        return "schema", "no structured_output in CLI payload" + _denied(payload)
    return None


def run_worker(spec: WorkerSpec, mcp_config: Path | None, raw_dir: Path | None = None,
               runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> WorkerResult:
    """Run one worker to completion. Never raises for worker failures; returns ok=False.

    Only programming errors (bad tool list, missing config) raise.
    """
    argv = build_argv(spec, mcp_config)
    t0 = time.monotonic()
    log.info("worker start name=%s model=%s tools=%d", spec.name, spec.model, len(spec.allowed_tools))
    try:
        proc = runner(argv, capture_output=True, text=True, timeout=spec.timeout_s, env=_clean_env())
    except subprocess.TimeoutExpired:
        dur = time.monotonic() - t0
        log.error("worker timeout name=%s after=%.0fs", spec.name, dur)
        return WorkerResult(spec.name, False, None, f"timeout after {spec.timeout_s}s", "timeout", dur, 0.0, 0)

    dur = time.monotonic() - t0
    stdout = proc.stdout or ""
    raw_path = None
    if raw_dir is not None:
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = str(raw_dir / f"{spec.name}.raw.json")
        Path(raw_path).write_text(stdout if stdout else (proc.stderr or ""))

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        log.error("worker non-json name=%s exit=%s stderr=%s", spec.name, proc.returncode, (proc.stderr or "")[:300])
        return WorkerResult(spec.name, False, None,
                            f"non-JSON output (exit {proc.returncode}): {(proc.stderr or stdout)[:300]}",
                            "schema", dur, 0.0, 0, raw_path)

    cost = float(payload.get("total_cost_usd") or 0.0)
    turns = int(payload.get("num_turns") or 0)
    failure = _classify(payload)
    if failure:
        kind, msg = failure
        log.error("worker failed name=%s kind=%s msg=%s", spec.name, kind, msg[:200])
        return WorkerResult(spec.name, False, None, msg, kind, dur, cost, turns, raw_path)

    data = payload["structured_output"]
    try:
        jsonschema.validate(data, spec.schema)
    except jsonschema.ValidationError as e:
        log.error("worker schema-invalid name=%s path=%s msg=%s", spec.name, list(e.absolute_path), e.message[:200])
        return WorkerResult(spec.name, False, None, f"schema: {e.message[:300]} at {list(e.absolute_path)}",
                            "schema", dur, cost, turns, raw_path)

    log.info("worker done name=%s turns=%d cost=%.3f dur=%.0fs", spec.name, turns, cost, dur)
    return WorkerResult(spec.name, True, data, None, None, dur, cost, turns, raw_path)


def run_many(specs: list[WorkerSpec], mcp_config: Path | None, raw_dir: Path | None,
             max_workers: int = 8, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run
             ) -> dict[str, WorkerResult]:
    """Run workers in parallel. Stops early on the first auth or quota failure, because every
    remaining worker would fail the same way. Results finished before the abort are returned
    on the exception (`partial`) so the caller can save them."""
    results: dict[str, WorkerResult] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(run_worker, s, mcp_config, raw_dir, runner): s.name for s in specs}
        for fut in as_completed(futures):
            res = fut.result()
            results[res.name] = res
            if res.error_kind in ("auth", "quota"):
                for f in futures:
                    f.cancel()
                exc = WorkerAuthError if res.error_kind == "auth" else WorkerQuotaError
                err = exc(res.error or res.error_kind)
                err.partial = {k: v for k, v in results.items() if v.ok}  # type: ignore[attr-defined]
                raise err
    return results
