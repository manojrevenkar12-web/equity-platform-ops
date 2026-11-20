"""The dashboard's API: the generated reports, and the plan guard to try on a plan.

- `GET /health`
- `GET /api/results`: the development report, the held-out report (once it has been run) and the gate on each.
- `GET /api/guard/examples`: the example plans in infra/guard-examples.
- `POST /api/guard`: a `terraform show -json` plan and its commit messages; the guard's decision and findings.
The built dashboard (web/dist) is served at `/`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from epo.config import ROOT, load
from epo.eval.gate import gate
from epo.guard.plan import analyse

REPORTS = ROOT / "reports"
EXAMPLES = ROOT / "infra" / "guard-examples"

app = FastAPI(title="equity-platform-ops", version="1.0.0")


def _report(name: str) -> dict | None:
    p = REPORTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


@app.get("/health")
def health() -> dict:
    return {"ok": True, "reports": sorted(p.stem for p in REPORTS.glob("*.json"))}


@app.get("/api/results")
def results() -> dict:
    dev, held = _report("dev"), _report("heldout")
    if dev is None:
        raise HTTPException(503, "No report yet: run python -m epo.eval.cli evaluate.")
    return {"dev": dev, "heldout": held, "gate": {"dev": gate(dev), "heldout": gate(held) if held else None}}


@app.get("/api/guard/examples")
def examples() -> list[dict]:
    out = []
    for p in sorted(EXAMPLES.glob("*.json")):
        msgs = p.with_suffix(".commits.txt")
        out.append({"name": p.stem, "plan": json.loads(p.read_text()), "commits": msgs.read_text() if msgs.exists() else ""})
    return out


class GuardRequest(BaseModel):
    plan: dict
    commits: str = Field(default="", max_length=20_000)


@app.post("/api/guard")
def guard(req: GuardRequest) -> dict:
    if not isinstance(req.plan.get("resource_changes"), list):
        raise HTTPException(422, "The plan has no resource_changes: pass the output of terraform show -json.")
    plan = dict(req.plan)
    plan["commit_trailers"] = [ln.strip() for ln in req.commits.splitlines() if ln.strip().startswith("Co-Authored-By")]
    v = analyse(plan, load("guard"))
    return {"decision": v.decision, "risk": v.risk, "ai": v.ai, "findings": [f.__dict__ for f in v.findings],
            "resources": len(plan["resource_changes"])}


_dist = Path(os.environ.get("EPO_WEB_DIST", ROOT / "web" / "dist"))
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
