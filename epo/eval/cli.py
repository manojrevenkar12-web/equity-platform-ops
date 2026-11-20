"""python -m epo.eval.cli evaluate | heldout | gate [--dev] | readme [--check] | rules [--check] | quick"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime

from epo.config import CONFIG, ROOT, load
from epo.eval import report
from epo.eval.gate import gate
from epo.eval.run import run_all, summarize
from epo.sim.designs import ORDER
from epo.slo import rules as R

LOCK = CONFIG / "heldout.lock"
GENERATED = {"ops/prometheus/rules.yml": lambda s: R.dump(R.rules(s)),
             "ops/alertmanager/routes.yml": lambda s: R.dump(R.alertmanager_routes()),
             "ops/grafana/slo-dashboard.json": lambda s: R.dump_json(R.grafana(s))}


def _hash() -> str:
    h = hashlib.sha256()
    for n in ("world", "heldout", "platform", "guard", "value", "gate"):
        h.update((CONFIG / f"{n}.yaml").read_bytes())
    return h.hexdigest()[:16]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="epo.eval.cli")
    ap.add_argument("cmd", choices=["evaluate", "heldout", "gate", "readme", "rules", "quick"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "rules":
        slo, stale = load("slo"), []
        for rel, make in GENERATED.items():
            p = ROOT / rel
            text = make(slo)
            if not p.exists() or p.read_text() != text:
                stale.append(rel)
                if not a.check:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(text)
        if a.check and stale:
            print("out of date:", ", ".join(stale), "- run python -m epo.eval.cli rules", file=sys.stderr)
            return 1
        return 0
    if a.cmd == "quick":
        s = summarize(run_all(False, names=["as_found", "platform"], weeks=3, seeds=[3101], workers=1), n_boot=200)["designs"]
        print(json.dumps({n: {k: round(x[k], 2) for k in ("feedback_p90", "pages_per_week", "engineer_hours_per_week")}
                          for n, x in s.items()}, indent=1))
        ok = s["platform"]["engineer_hours_per_week"] < s["as_found"]["engineer_hours_per_week"]
        print("platform loses fewer engineering hours than as found:", ok)
        return 0 if ok else 1
    if a.cmd == "evaluate":
        dev = summarize(run_all(False))
        report.write("dev", dev)
        report.charts(dev, ORDER)
        report.readme(ORDER)
        print(json.dumps({n: [round(x["feedback_p90"], 1), round(x["pages_per_week"], 1), x["harmful_applied"],
                              x["duplicate_grants"], round(x["engineer_hours_per_week"], 1)] for n, x in dev["designs"].items()}))
        return 0
    if a.cmd == "heldout":
        if LOCK.exists():
            print(f"held-out already run: {LOCK.read_text().strip()}", file=sys.stderr)
            return 1
        s = summarize(run_all(True), heldout=True)
        report.write("heldout", s)
        LOCK.write_text(json.dumps({"ran_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "config_sha": _hash(),
                                    "seeds": s["world"]["seeds"]}) + "\n")
        report.readme(ORDER)
        print("held-out:", gate(s) or "gate passed")
        return 0
    if a.cmd == "gate":
        held = report.REPORTS / "heldout.json"
        path = held if held.exists() and not a.dev else report.REPORTS / "dev.json"
        fails = gate(json.loads(path.read_text()))
        print(f"{path.name}: " + ("; ".join(fails) if fails else "gate passed"))
        return 1 if fails else 0
    if a.cmd == "readme":
        changed = report.readme(ORDER, check=a.check)
        if a.check and changed:
            print("README results block is out of date: run python -m epo.eval.cli readme", file=sys.stderr)
            return 1
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
