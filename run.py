#!/usr/bin/env python3
"""Portfolio Market Pulse, one command.

    python run.py                      # full run: inventory, macro, segments, companies, score, render
    python run.py --companies Meatly,Dropz
    python run.py --reuse              # reuse today's saved worker outputs, only run what is missing
    python run.py --replay 2026-09-08  # no workers at all: re-score and re-render a saved run
    python run.py --dry-run            # print the worker plan, run nothing

Exit codes: 0 clean · 1 partial (some workers failed, output still rendered) · 2 fatal (inventory or auth).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import yaml

from pulse import prompts, schemas
from pulse.render import artifact_body, now_iso, render_html, render_markdown, slug
from pulse.scoring import score_portfolio
from pulse.workers import WorkerAuthError, WorkerResult, WorkerSpec, run_many, run_worker

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("pulse")


def load_env() -> None:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if v and k not in os.environ:
                    os.environ[k] = v


def save_result(run_dir: Path, res: WorkerResult) -> None:
    (run_dir / f"{res.name}.json").write_text(json.dumps(asdict(res), indent=1, ensure_ascii=False))


def load_result(run_dir: Path, name: str) -> WorkerResult | None:
    p = run_dir / f"{name}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return WorkerResult(**d)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--companies", help="comma-separated subset of company names")
    ap.add_argument("--reuse", action="store_true", help="reuse saved worker outputs in today's run dir")
    ap.add_argument("--replay", metavar="RUN_ID", help="re-score a saved run, no workers")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-workers", type=int, default=int(os.environ.get("PULSE_MAX_WORKERS", "8")))
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--skip-macro", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    load_env()
    if args.model:
        os.environ["PULSE_MODEL"] = args.model
    from pulse import workers as w  # re-read env-driven defaults
    w.DEFAULT_MODEL = os.environ.get("PULSE_MODEL", w.DEFAULT_MODEL)

    cfg = yaml.safe_load((ROOT / "config" / "segments.yaml").read_text())
    companies_cfg: dict = cfg["companies"]
    segments_cfg: dict = cfg["segments"]
    exclude_status = set(cfg.get("exclude_status", []))
    as_of = date.today()
    run_id = args.replay or as_of.isoformat()
    run_dir = ROOT / "data" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    mcp_config = ROOT / "config" / "mcp.json"
    live = not args.replay
    reuse = args.reuse or bool(args.replay)

    def get_or_run(spec: WorkerSpec) -> WorkerResult:
        if reuse:
            cached = load_result(run_dir, spec.name)
            if cached and cached.ok:
                log.info("reuse %s", spec.name)
                return cached
        if not live:
            return WorkerResult(spec.name, False, None, "replay: no saved output", "missing", 0, 0, 0)
        res = run_worker(spec, mcp_config, run_dir / "raw")
        save_result(run_dir, res)
        return res

    # 1. Inventory (fatal)
    inv_spec = WorkerSpec("inventory", prompts.inventory_prompt(as_of.isoformat()), schemas.INVENTORY,
                          ["mcp__jarvis__crm_list_portfolio", "mcp__jarvis__portfolio_risk_rank"], True,
                          max_turns=12, model=os.environ.get("PULSE_MODEL", w.DEFAULT_MODEL))
    if args.dry_run:
        print("PLAN: inventory worker, then:")
    else:
        inv_res = get_or_run(inv_spec)
        if not inv_res.ok:
            print(f"FATAL inventory worker failed ({inv_res.error_kind}): {inv_res.error}", file=sys.stderr)
            if inv_res.error_kind == "auth":
                print("Fix: run `claude login` on this machine (or set ANTHROPIC_API_KEY in .env), then log in to Jarvis once via `claude` → /mcp.", file=sys.stderr)
            return 2
        inventory = inv_res.data["companies"]

    if args.dry_run:
        inventory = [{"name": n, "org_id": None, "status": "active", "funds": [], "risk_band": None, "risk_score": None,
                      "days_since_contact": None, "attention_items": [], "coverage_notes": []} for n in companies_cfg]

    # 2. Scope
    wanted = {s.strip() for s in args.companies.split(",")} if args.companies else None
    scoped = []
    for inv in inventory:
        c = companies_cfg.get(inv["name"])
        if c is None:
            log.warning("company %s is in Jarvis but not in config/segments.yaml; skipped. Add it.", inv["name"])
            continue
        status = c.get("status_override") or inv.get("status")
        if status in exclude_status:
            log.info("skip %s (status %s)", inv["name"], status)
            continue
        if wanted and inv["name"] not in wanted:
            continue
        scoped.append(inv)
    seg_ids = sorted({companies_cfg[i["name"]]["segment"] for i in scoped})

    # 3. Research specs
    specs: list[WorkerSpec] = []
    model = os.environ.get("PULSE_MODEL", w.DEFAULT_MODEL)
    if not args.skip_macro:
        specs.append(WorkerSpec("macro", prompts.macro_prompt(as_of.isoformat()), schemas.MACRO, ["WebSearch", "WebFetch"], False, 18, model, timeout_s=600))
    for sid in seg_ids:
        ours = [n for n, c in companies_cfg.items() if c["segment"] == sid and not c.get("status_override")]
        specs.append(WorkerSpec(f"segment__{sid}", prompts.segment_prompt(as_of.isoformat(), sid, segments_cfg[sid], ours), schemas.SEGMENT,
                                ["WebSearch", "WebFetch", "mcp__jarvis__knowledge_search"], True, 30, model, timeout_s=900))
    for inv in scoped:
        c = companies_cfg[inv["name"]]
        specs.append(WorkerSpec(f"company__{slug(inv['name'])}",
                                prompts.company_prompt(as_of.isoformat(), inv["name"], inv.get("org_id"), c.get("one_liner", ""),
                                                       segments_cfg[c["segment"]]["label"], inv.get("attention_items", [])),
                                schemas.COMPANY,
                                ["mcp__jarvis__company_current_state", "mcp__jarvis__fund_kpis", "mcp__jarvis__knowledge_search", "WebSearch"],
                                True, 22, model, timeout_s=600))

    if args.dry_run:
        for s in specs:
            print(f"  {s.name:40s} tools={len(s.allowed_tools)} turns={s.max_turns} model={s.model}")
        print(f"{len(specs)} research workers + 1 inventory. Segments: {', '.join(seg_ids)}")
        return 0

    # 4. Run (reuse what is saved)
    results: dict[str, WorkerResult] = {}
    todo = []
    for s in specs:
        cached = load_result(run_dir, s.name) if reuse else None
        if cached and cached.ok:
            results[s.name] = cached
        elif live:
            todo.append(s)
        else:
            results[s.name] = WorkerResult(s.name, False, None, "replay: no saved output", "missing", 0, 0, 0)
    if todo:
        log.info("running %d workers (max %d parallel)", len(todo), args.max_workers)
        try:
            fresh = run_many(todo, mcp_config, run_dir / "raw", max_workers=args.max_workers)
        except WorkerAuthError as e:
            print(f"FATAL authentication failed mid-run: {e}", file=sys.stderr)
            return 2
        for r in fresh.values():
            save_result(run_dir, r)
        results.update(fresh)
    results["inventory"] = inv_res if not args.replay else (load_result(run_dir, "inventory") or inv_res)

    # 5. Score
    macro = results["macro"].data if "macro" in results and results["macro"].ok else None
    segment_data = {sid: (results[f"segment__{sid}"].data if results[f"segment__{sid}"].ok else None) for sid in seg_ids}
    company_data = {}
    for inv in scoped:
        r = results.get(f"company__{slug(inv['name'])}")
        company_data[inv["name"]] = r.data if r and r.ok else None
    pulse = score_portfolio(scoped, companies_cfg, segments_cfg, segment_data, company_data, macro, as_of)

    # 6. Render
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run_report = {
        "run_id": run_id, "generated_at": now_iso(),
        "workers": [{k: v for k, v in asdict(r).items() if k != "data"} for r in results.values()],
        "segment_data": segment_data,
    }
    page = render_html(pulse, run_report, segments_cfg)
    (out / "index.html").write_text(page)
    (out / "artifact.html").write_text(artifact_body(page))
    (out / "pulse.md").write_text(render_markdown(pulse, run_report, segments_cfg))
    (out / "pulse.json").write_text(json.dumps(pulse, indent=1, ensure_ascii=False, default=str))
    (out / "run_report.json").write_text(json.dumps({k: v for k, v in run_report.items() if k != "segment_data"}, indent=1, default=str))

    failed = [r for r in results.values() if not r.ok]
    cost = sum(r.cost_usd for r in results.values())
    print(f"done: {len(results) - len(failed)}/{len(results)} workers ok, cost {cost:.2f} USD, {len(pulse['companies'])} companies → {out / 'index.html'}")
    for r in failed:
        print(f"  FAILED {r.name}: {r.error_kind}: {(r.error or '')[:160]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
