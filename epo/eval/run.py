"""Every design on every org, then a summary with paired bootstrap intervals over (org, week) blocks."""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from epo.config import load, world_config
from epo.keyed import rng
from epo.sim.designs import BY_NAME, DESIGNS
from epo.sim.engine import run_changes, run_ci, run_jobs, run_paging
from epo.world.changes import ChangesWorld
from epo.world.ci import CIWorld
from epo.world.jobs import JobsWorld
from epo.world.oncall import OncallWorld


def run_seed(args) -> dict:
    cfg, seed, names = args
    p, g = load("platform"), load("guard")
    ci, oc, ch = CIWorld(cfg, seed), OncallWorld(cfg, seed), ChangesWorld(cfg, seed)
    jobs = JobsWorld(cfg, seed, [(i.start, i.end, i.kind) for i in oc.incidents])
    truth = oc.page_worthy(p["slo"], tuple(p["slo"]["page_share"]))
    out = {"seed": seed, "weeks": cfg["weeks"], "incidents": len(truth), "page_worthy": sum(ok for _, ok in truth),
           "designs": {}}
    cache: dict = {}
    for n in names:
        d = BY_NAME[n]
        key = {"ci": (d.selection, d.lpt_shards, d.quarantine, d.main_full_run),
               "paging": (d.paging, d.grouping, d.symptoms_page), "changes": (d.changes, d.ai_tier),
               "jobs": (d.jobs, d.idempotent, d.regions)}
        res = {}
        for area, fn in (("ci", lambda: run_ci(ci, d, p, cfg["weeks"])), ("paging", lambda: run_paging(oc, d, p, truth)),
                         ("changes", lambda: run_changes(ch, d, p, g)), ("jobs", lambda: run_jobs(jobs, d, p, cfg["weeks"]))):
            k = (area, key[area])
            if k not in cache:
                cache[k] = fn()
            res[area] = cache[k]
        res["regions"] = d.regions
        out["designs"][n] = res
    return out


def run_all(heldout: bool = False, names: list[str] | None = None, weeks: int | None = None,
            seeds: list[int] | None = None, workers: int | None = None) -> list[dict]:
    cfg = world_config(heldout)
    if weeks:
        cfg["weeks"] = weeks
    seeds = seeds or cfg["seeds"]
    names = names or [d.name for d in DESIGNS]
    args = [(cfg, s, names) for s in seeds]
    workers = workers or min(len(seeds), os.cpu_count() or 1)
    if workers == 1:
        return [run_seed(a) for a in args]
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(run_seed, args))


def _week_rows(r: dict, n: str, v: dict, world: dict) -> list[dict]:
    d = r["designs"][n]
    rows = []
    standby = world["regions"]["primary_node_month_eur"] * world["regions"]["secondary_share"] if d["regions"] == 2 else 0.0
    for w in range(r["weeks"]):
        ci, pg, ch, jb = d["ci"][w], d["paging"][w], d["changes"][w], d["jobs"][w]
        parts = {
            "waiting_for_ci": sum(ci["feedback"]) * v["wait_cost_share"] / 60,
            "flaky_reds": ci["flaky_red"] * v["minutes_per_red_build"] / 60,
            "broken_main": ci["main_broken_hours"] * v["engineers_blocked_by_broken_main"],
            "pages": pg["pages"] * v["hours_per_page"] + pg["after_hours_pages"] * v["extra_hours_after_hours_page"],
            "change_review": ch["review_hours"] + ch["false_blocks"] * v["hours_per_false_block"],
            "job_repairs": jb["manual_hours"],
        }
        eng = sum(parts.values())
        rows.append({
            "feedback": ci["feedback"], "flaky_red": ci["flaky_red"], "escaped": ci["escaped"],
            "main_broken_hours": ci["main_broken_hours"], "runner_eur": ci["runner_minutes"] * world["ci"]["runner_cost_per_minute_eur"],
            "defects": ci["defects"], "quarantined": ci["quarantined"], "quarantined_truly_flaky": ci["quarantined_truly_flaky"],
            "pages": pg["pages"], "false_pages": pg["false_pages"], "after_hours_pages": pg["after_hours_pages"],
            "worthy": pg["worthy"], "detected": pg["detected"], "minutes_to_page": pg["minutes_to_page"],
            "harmful": ch["harmful"], "harmful_applied": ch["harmful_applied"], "review_hours": ch["review_hours"],
            "hours_to_apply": ch["hours_to_apply"], "false_blocks": ch["false_blocks"], "changes": ch["changes"],
            "duplicates": jb["duplicates"], "late": jb["late"], "down_minutes": jb["down_minutes"], "manual_hours": jb["manual_hours"], "runs": jb["runs"],
            "engineer_hours": eng, "parts": parts, "standby_eur_week": standby * 12 / 52,
        })
    return rows


def summarize(runs: list[dict], heldout: bool = False, n_boot: int = 2000) -> dict:
    v, world = load("value"), world_config(heldout)
    names = list(runs[0]["designs"])
    per = {n: [row for r in runs for row in _week_rows(r, n, v, world)] for n in names}
    blocks = len(per[names[0]])
    idx = rng("bootstrap", blocks).integers(0, blocks, size=(n_boot, blocks))
    base = np.array([x["engineer_hours"] for x in per["as_found"]])
    out = {}
    for n in names:
        rows = per[n]
        a = {k: np.array([x[k] for x in rows], dtype=float) for k in
             ("flaky_red", "escaped", "main_broken_hours", "runner_eur", "pages", "false_pages", "after_hours_pages",
              "worthy", "detected", "harmful", "harmful_applied", "review_hours", "false_blocks", "duplicates", "late",
              "manual_hours", "engineer_hours", "standby_eur_week", "defects", "runs", "down_minutes")}
        fb = np.concatenate([x["feedback"] for x in rows])
        hta = np.concatenate([x["hours_to_apply"] for x in rows])
        mtp = [m for x in rows for m in x["minutes_to_page"]]
        diff = a["engineer_hours"] - base
        out[n] = {
            "label": BY_NAME[n].label,
            "feedback_p50": float(np.percentile(fb, 50)), "feedback_p90": float(np.percentile(fb, 90)),
            "flaky_red_per_week": float(a["flaky_red"].mean()),
            "flaky_red_ci": [float(x) for x in np.percentile(a["flaky_red"][idx].mean(axis=1), [2.5, 97.5])],
            "escaped_per_week": float(a["escaped"].mean()), "escaped_share": float(a["escaped"].sum() / max(a["defects"].sum(), 1)),
            "main_broken_hours_per_week": float(a["main_broken_hours"].mean()),
            "runner_eur_per_month": float(a["runner_eur"].mean() * 52 / 12),
            "pages_per_week": float(a["pages"].mean()),
            "pages_ci": [float(x) for x in np.percentile(a["pages"][idx].mean(axis=1), [2.5, 97.5])],
            "false_pages_per_week": float(a["false_pages"].mean()), "after_hours_pages_per_week": float(a["after_hours_pages"].mean()),
            "detected_share": float(a["detected"].sum() / max(a["worthy"].sum(), 1)), "page_worthy": int(a["worthy"].sum()),
            "minutes_to_page": float(np.mean(mtp)) if mtp else None,
            "harmful": int(a["harmful"].sum()), "harmful_applied": int(a["harmful_applied"].sum()),
            "harmful_applied_per_month": float(a["harmful_applied"].mean() * 52 / 12),
            "review_hours_per_week": float(a["review_hours"].mean()), "hours_to_apply_median": float(np.median(hta)),
            "false_blocks_per_week": float(a["false_blocks"].mean()),
            "duplicate_grants": int(a["duplicates"].sum()), "late_runs": int(a["late"].sum()), "job_runs": int(a["runs"].sum()),
            "manual_hours_per_month": float(a["manual_hours"].mean() * 52 / 12),
            "standby_eur_per_month": float(a["standby_eur_week"].mean() * 52 / 12),
            "down_minutes_per_month": float(a["down_minutes"].mean() * 52 / 12),
            "engineer_hours_per_week": float(a["engineer_hours"].mean()),
            "engineer_hours_vs_as_found": float(diff.mean()),
            "engineer_hours_vs_as_found_ci": [float(x) for x in np.percentile(diff[idx].mean(axis=1), [2.5, 97.5])],
            "quarantined": int(np.mean([x["quarantined"] for x in rows])),
            "hours_parts": {k: float(np.mean([x["parts"][k] for x in rows])) for k in rows[0]["parts"]},
        }
    w = world
    return {"designs": out, "world": {"orgs": len(runs), "seeds": [r["seed"] for r in runs], "weeks": w["weeks"],
                                      "prs": int(sum(len(x["feedback"]) for x in per["as_found"])),
                                      "incidents": int(sum(r["incidents"] for r in runs)),
                                      "page_worthy": int(sum(r["page_worthy"] for r in runs)),
                                      "changes": int(sum(x["changes"] for x in per["as_found"])),
                                      "job_runs": int(sum(x["runs"] for x in per["as_found"]))}}
