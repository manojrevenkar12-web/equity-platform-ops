"""Equity jobs that must run exactly once: monthly vesting runs and reporting deadlines, with the faults that
interrupt them. Hidden: when a worker dies, whether its last write had landed, and when a region goes down."""
from __future__ import annotations

from dataclasses import dataclass

from epo.keyed import rng


@dataclass(frozen=True)
class Job:
    id: str
    kind: str              # vesting | report
    start: int             # scheduled minute
    deadline: int          # must be finished by this minute
    batches: int           # activities of 50 grants (vesting) or 1 (report)
    minutes: int           # run time without faults
    crash: bool            # a worker dies during the run
    crash_at: float        # share of the run done when it dies
    landed: bool           # the batch in flight had been written before the crash


class JobsWorld:
    def __init__(self, cfg: dict, seed: int, outages: list[tuple[int, int, str]]):
        """`outages`: (start, end, kind) from the on-call world; region outages take the primary region down."""
        self.cfg, self.seed, self.weeks = cfg["jobs"], seed, cfg["weeks"]
        self.region_down = [(s, e) for s, e, k in outages if k == "region_outage"]

    def jobs(self) -> list[Job]:
        j = self.cfg
        r = rng(self.seed, "jobs")
        out = []
        for cycle in range(0, self.weeks, 4):
            start = cycle * 7 * 1440 + 2 * 60          # 02:00 on the first day of the cycle
            for c in range(j["companies"]):
                grants = int(r.integers(*j["grants_per_company"]))
                batches = max(1, grants // 50)
                crash = bool(r.random() < j["worker_crash_per_run"])
                out.append(Job(f"vest-{cycle}-{c}", "vesting", start, start + 7 * 60, batches, 2 + batches,
                               crash, float(r.uniform(0.05, 0.95)), bool(r.random() < j["activity_crash_after_write"])))
        for week in range(self.weeks):
            for i in range(j["report_deadlines_per_week"]):
                start = week * 7 * 1440 + int(r.integers(0, 5)) * 1440 + int(r.integers(6 * 60, 20 * 60))
                crash = bool(r.random() < j["worker_crash_per_run"])
                out.append(Job(f"report-{week}-{i}", "report", start, start + 4 * 60, 1, int(r.integers(10, 60)),
                               crash, float(r.uniform(0.05, 0.95)), bool(r.random() < j["activity_crash_after_write"])))
        return out

    def down(self, minute: float) -> tuple[bool, int]:
        """Is the primary region down at this minute, and until when."""
        for s, e in self.region_down:
            if s <= minute < e:
                return True, e
        return False, 0

    def manual_fix_minutes(self, job: Job) -> int:
        r = rng(self.seed, "manual", job.id)
        return int(r.uniform(*self.cfg["manual_fix_hours"]) * 60)
