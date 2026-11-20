"""Runs each design's real components against the simulated org, week by week, and scores them on the truth."""
from __future__ import annotations

import numpy as np

from epo.ci.selection import FlakeDetector, Selector, fixed_shards, lpt_shards
from epo.guard.plan import analyse
from epo.keyed import rng, uniform
from epo.sim.designs import Design
from epo.slo.alerts import BudgetBurn, Grouper, ThresholdAlerts, edges
from epo.world.changes import ChangesWorld
from epo.world.ci import CIWorld
from epo.world.jobs import JobsWorld
from epo.world.oncall import WEEK_MIN, OncallWorld


# -- CI ---------------------------------------------------------------------------------------------------------
def run_ci(w: CIWorld, d: Design, p: dict, weeks: int) -> list[dict]:
    c = p["ci"]
    sel = Selector(w.deps, w.test_package)
    recorded = w.seconds * np.exp(rng(w.seed, "recorded").normal(0, 0.15, len(w.seconds)))   # what past runs measured
    det = FlakeDetector(c["sprt_p0"], c["sprt_p1"], c["sprt_alpha"], c["sprt_beta"])
    all_tests = np.arange(len(w.test_package))
    overhead = w.cfg["pipeline_overhead_min"]
    full_loads = lpt_shards(recorded, c["shard_target_seconds"], c["max_shards"])
    full_wall = overhead + max(full_loads) / 60
    full_cost = len(full_loads) * overhead + float(w.seconds.sum()) / 60
    out = []
    for week in range(weeks):
        m = {"week": week, "prs": 0, "feedback": [], "flaky_red": 0, "reruns": 0, "defects": 0, "caught": 0,
             "escaped": 0, "hidden_by_quarantine": 0, "main_broken_hours": 0.0, "runner_minutes": 0.0}
        active = np.flatnonzero((w.flake > 0) & (w.onset <= week))
        for pr in w.prs(week):
            m["prs"] += 1
            tests = sel.select(pr.packages) if d.selection else all_tests
            secs = recorded[tests]
            if d.lpt_shards:
                loads = lpt_shards(secs, c["shard_target_seconds"], c["max_shards"])
            else:
                by_pkg = np.bincount(w.test_package[tests], weights=secs, minlength=len(w.deps))
                loads = fixed_shards(by_pkg.tolist(), c["fixed_shards"])
            wall = overhead + max(loads) / 60
            run_cost = len(loads) * overhead + float(w.seconds[tests].sum()) / 60
            in_run = np.zeros(len(all_tests), dtype=bool)
            in_run[tests] = True
            cands = [int(t) for t in set(pr.broken) | set(active.tolist()) if in_run[t]]
            positive = [t for t in det.llr if det.llr[t] > 0 and in_run[t]]
            caught = False
            runs = 0
            for attempt in range(c["max_reruns"] + 1):
                runs += 1
                fails = [t for t in cands if not w.result(pr, t, 2 * attempt)]
                still = [t for t in fails if not w.result(pr, t, 2 * attempt + 1)]       # one retry per failing test
                flipped = set(fails) - set(still)
                if d.quarantine:
                    for t in flipped:
                        det.observe(t, True, week)
                    for t in positive:
                        if t not in fails:
                            det.observe(t, False, week)
                blocking = [t for t in still if not d.quarantine or det.blocking(t)]
                if not blocking:
                    break
                if any(t in pr.broken for t in blocking):
                    caught = True
                    break
                m["flaky_red"] += 1
            m["reruns"] += runs - 1
            m["feedback"].append(wall * runs)
            m["runner_minutes"] += run_cost * runs
            if pr.defect:
                m["defects"] += 1
                if caught:
                    m["caught"] += 1
                else:
                    m["escaped"] += 1
                    if d.quarantine and any(in_run[t] and not det.blocking(t) for t in pr.broken):
                        m["hidden_by_quarantine"] += 1
                    merged = pr.day * 1440 + pr.minute + wall * runs
                    if d.main_full_run == "hourly" and merged % 1440 < 19 * 60:
                        found = (merged // 60 + 1) * 60 + full_wall          # the next hourly run on main finishes
                    else:
                        found = (pr.day + 1) * 1440 + 2 * 60 + full_wall     # the nightly run
                    m["main_broken_hours"] += (found - merged) / 60 + c["fix_hours"]
        m["runner_minutes"] += full_cost * (5 * 11 if d.main_full_run == "hourly" else 5)   # main runs, 08:00-19:00
        m["quarantined"] = len(det.quarantined)
        m["flaky_active"] = len(active)
        m["quarantined_truly_flaky"] = sum(1 for t in det.quarantined if w.flake[t] > 0)
        out.append(m)
    return out


# -- paging -----------------------------------------------------------------------------------------------------
def run_paging(w: OncallWorld, d: Design, p: dict, truth: list) -> list[dict]:
    s = p["slo"]
    alerts: list[int] = []
    if d.paging == "burn":
        alerts += edges(BudgetBurn(s["availability"]).fire(w.errors, w.requests))
        alerts += edges(BudgetBurn(s["latency"]).fire(w.slow, w.requests))
    else:
        t = p["thresholds"]
        alerts += edges(ThresholdAlerts(t["error_ratio"]).fire(w.errors, w.requests))
        alerts += edges(ThresholdAlerts(t["slow_ratio"]).fire(w.slow, w.requests))
    if d.symptoms_page:
        alerts += [m for m, _ in w.symptoms]
    alerts = sorted(a for a in alerts if a >= 1440)
    if d.grouping:
        g = Grouper(p["paging"]["group_minutes"])
        for a in alerts:
            g.alert(a)
        pages = g.pages
    else:
        pages = alerts
    worthy = [inc for inc, ok in truth if ok]
    slack = p["paging"]["match_minutes"]
    out = []
    for week in range(w.weeks):
        lo, hi = week * WEEK_MIN, (week + 1) * WEEK_MIN
        wp = [x for x in pages if lo <= x < hi]
        incs = [i for i in worthy if lo <= i.start < hi and i.start >= 1440]
        det = []
        for inc in incs:
            hit = [a for a in alerts if inc.start - 2 <= a <= inc.end + slack]
            det.append(hit[0] - inc.start if hit else None)
        false = [x for x in wp if not any(i.start - slack <= x <= i.end + slack for i in worthy)]
        after = [x for x in wp if (x % 1440) < 8 * 60 or (x % 1440) >= 19 * 60 or (x // 1440) % 7 >= 5]
        out.append({"week": week, "pages": len(wp), "false_pages": len(false), "after_hours_pages": len(after),
                    "alerts": len([a for a in alerts if lo <= a < hi]), "worthy": len(incs),
                    "detected": sum(x is not None for x in det),
                    "minutes_to_page": [max(0, x) for x in det if x is not None]})
    return out


# -- changes ----------------------------------------------------------------------------------------------------
def run_changes(w: ChangesWorld, d: Design, p: dict, guard_cfg: dict) -> list[dict]:
    c = w.cfg
    g = dict(guard_cfg)
    if not d.ai_tier:
        g["ai_trailer_names"] = []
    out = []
    for week in range(w.weeks):
        ch = sorted(w.week(week), key=lambda x: (x.day, x.hour))
        m = {"week": week, "changes": len(ch), "harmful": 0, "harmful_applied": 0, "reviews": 0, "review_hours": 0.0,
             "hours_to_apply": [], "false_blocks": 0, "auto_applied": 0, "ai": 0}
        per_day: dict[int, int] = {}
        reviewers = p["changes"]["reviewers"]
        for x in ch:
            m["harmful"] += x.harmful
            m["ai"] += x.ai
            flagged = False
            if d.changes == "review_all":
                decision = "review"
            elif d.changes == "ai_on_green":
                decision = "apply" if x.ai else "review"
            else:
                v = analyse(x.plan, g)
                decision, flagged = v.decision, bool(v.findings)
            if decision == "block":
                if not x.harmful:
                    m["false_blocks"] += 1
                    decision = "review"            # the author explains and a person looks at it
                else:
                    m["hours_to_apply"].append(p["changes"]["fix_hours"])
                    continue
            if decision == "apply":
                m["auto_applied"] += 1
                m["harmful_applied"] += x.harmful
                m["hours_to_apply"].append(p["changes"]["ci_hours"])
                continue
            n = per_day.get(x.day, 0)
            per_day[x.day] = n + 1
            load = n / reviewers                    # reviews each reviewer has already done that day
            catch = c["reviewer_catch"] - c["fatigue_per_review"] * load * c["reviews_per_engineer_day"]
            catch += c["flagged_review_boost"] if flagged else 0.0
            caught = uniform(w.seed, "review", x.id) < min(max(catch, 0.05), 0.98)
            m["reviews"] += 1
            m["review_hours"] += c["review_minutes"] / 60
            wait = rng(w.seed, "wait", x.id).uniform(*c["review_wait_hours"]) * (0.5 + load)
            m["hours_to_apply"].append(wait + p["changes"]["ci_hours"])
            if x.harmful and not caught:
                m["harmful_applied"] += 1
        out.append(m)
    return out


# -- equity jobs ------------------------------------------------------------------------------------------------
def run_jobs(w: JobsWorld, d: Design, p: dict, weeks: int) -> list[dict]:
    j = p["jobs"]
    out = {k: {"week": k, "runs": 0, "duplicates": 0, "late": 0, "late_hours": 0.0, "manual_hours": 0.0, "down_minutes": 0.0}
           for k in range(weeks)}
    for s, e in w.region_down:      # customer-facing: the API in the lost region, until traffic moves (or the region returns)
        wk = min(s // WEEK_MIN, weeks - 1)
        out[wk]["down_minutes"] += min(e - s, j["failover_minutes"]) * 0.5 if d.regions == 2 else (e - s)
    for job in w.jobs():
        wk = min(job.start // WEEK_MIN, weeks - 1)
        m = out[wk]
        m["runs"] += 1
        t = float(job.start)
        down, until = w.down(t)
        if down:
            if d.jobs == "cron":                               # the cron fired into a dead region: noticed next morning
                t = _next_morning(until)
                m["manual_hours"] += j["manual_rerun_hours"]
            else:
                t = t + j["failover_minutes"] if d.regions == 2 else until
        finish = t + job.minutes
        if job.crash:
            crash_t = t + job.crash_at * job.minutes
            done = int(job.crash_at * job.batches)
            if d.jobs == "cron":
                finish = crash_t + w.manual_fix_minutes(job) + job.minutes
                m["manual_hours"] += j["manual_rerun_hours"]
                m["duplicates"] += done * j["grants_per_batch"] if job.kind == "vesting" else 0
            else:
                finish = crash_t + j["retry_minutes"] + (1 - job.crash_at) * job.minutes
                if job.landed and not d.idempotent:
                    m["duplicates"] += j["grants_per_batch"] if job.kind == "vesting" else 1
        down, until = w.down(finish - job.minutes / 2)
        if down and d.jobs != "cron" and d.regions == 1:
            finish = max(finish, until + job.minutes / 2)
        if finish > job.deadline:
            m["late"] += 1
            m["late_hours"] += (finish - job.deadline) / 60
    return list(out.values())


def _next_morning(minute: float) -> float:
    day = int(minute // 1440)
    nine = day * 1440 + 9 * 60
    return nine if minute < nine else nine + 1440
