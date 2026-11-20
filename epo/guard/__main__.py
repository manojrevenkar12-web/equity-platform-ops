"""python -m epo.guard plan.json [--commit-messages FILE] [--json]

Reads `terraform show -json` output and the commit messages of the change (for the Co-Authored-By trailers that
mark it AI-written). Exit 0 apply, 2 review by a person, 3 block. The pull-request workflow posts the findings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from epo.config import load
from epo.guard.plan import analyse

EXIT = {"apply": 0, "review": 2, "block": 3}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m epo.guard")
    ap.add_argument("plan", type=Path)
    ap.add_argument("--commit-messages", type=Path, help="git log --format=%%B of the change")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    plan = json.loads(a.plan.read_text())
    if a.commit_messages:
        plan["commit_trailers"] = [ln.strip() for ln in a.commit_messages.read_text().splitlines() if ln.strip().startswith("Co-Authored-By")]
    v = analyse(plan, load("guard"))
    if a.json:
        print(json.dumps({"decision": v.decision, "risk": v.risk, "ai": v.ai, "findings": [f.__dict__ for f in v.findings]}, indent=1))
    else:
        print(f"decision: {v.decision}  risk {v.risk:g}{'  (AI-written)' if v.ai else ''}")
        for f in v.findings:
            print(f"  {f.level:6} {f.rule:28} {f.address}: {f.detail}")
    return EXIT[v.decision]


if __name__ == "__main__":
    sys.exit(main())
