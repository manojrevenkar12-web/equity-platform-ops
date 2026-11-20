"""Production traffic, incidents and the noise around them, minute by minute.

The platform sees request counts, errors and slow requests per minute (what Prometheus scrapes), and symptom
signals (CPU, restarts, replication lag). Hidden: which minutes belong to which incident, and how much of the
error budget each incident really spent.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from epo.keyed import rng

WEEK_MIN = 7 * 1440


@dataclass(frozen=True)
class Incident:
    start: int
    end: int
    kind: str
    error: float               # extra share of requests that fail
    slow: float                # extra share that are slow
    share: float               # share of traffic affected (a region is half)


class OncallWorld:
    def __init__(self, cfg: dict, seed: int):
        self.cfg, self.seed = cfg["oncall"], seed
        self.weeks = cfg["weeks"]
        self.minutes = self.weeks * WEEK_MIN
        o = self.cfg
        t = np.arange(self.minutes)
        day, mod = t // 1440, t % 1440
        weekday = day % 7 < 5
        hour = mod / 60
        busy = np.clip(np.sin((hour - 6) / 14 * np.pi), 0, None)          # 06:00-20:00 European business day
        self.rate = o["requests_per_minute"] * (0.06 + 0.94 * busy * np.where(weekday, 1.0, 0.25))
        self.incidents = self._incidents()
        err = np.full(self.minutes, o["baseline_error"])
        slow = np.full(self.minutes, o["baseline_slow"])
        self.true_err = np.zeros(self.minutes)
        self.true_slow = np.zeros(self.minutes)
        for inc in self.incidents:
            self.true_err[inc.start:inc.end] += inc.error * inc.share
            self.true_slow[inc.start:inc.end] += inc.slow * inc.share
        r = rng(seed, "blips")
        for d in range(self.weeks * 7):
            for _ in range(int(r.poisson(o["blips_per_day"]))):
                s = d * 1440 + int(r.integers(0, 1440))
                self.true_err[s:s + int(r.integers(*o["blip_minutes"]))] += r.uniform(*o["blip_error"])
        r = rng(seed, "traffic")
        n = r.poisson(self.rate)
        self.requests = n
        self.errors = r.binomial(n, np.clip(err + self.true_err, 0, 1))
        self.slow = r.binomial(n, np.clip(slow + self.true_slow, 0, 1))
        self.symptoms = self._symptoms()

    def _incidents(self) -> list[Incident]:
        o = self.cfg
        kinds = list(o["incident_kinds"])
        w = np.array([o["incident_kinds"][k][0] for k in kinds])
        r = rng(self.seed, "incidents")
        out = []
        for week in range(self.weeks):
            for _ in range(int(r.poisson(o["incidents_per_week"]))):
                k = kinds[int(r.choice(len(kinds), p=w / w.sum()))]
                _, dur, er, sl = o["incident_kinds"][k]
                s = week * WEEK_MIN + int(r.integers(0, WEEK_MIN))
                out.append(Incident(s, min(self.minutes, s + int(r.integers(*dur))), k, float(r.uniform(*er)),
                                    float(r.uniform(*sl)), 0.5 if k == "region_outage" else 1.0))
        return sorted(out, key=lambda i: i.start)

    def _symptoms(self) -> list[tuple[int, str]]:
        """Minutes where a symptom alert (CPU, restarts, lag) would fire. Most are noise; incidents add some."""
        r = rng(self.seed, "symptoms")
        out = []
        for d in range(self.weeks * 7):
            for _ in range(int(r.poisson(self.cfg["noise_symptoms_per_day"]))):
                out.append((d * 1440 + int(r.integers(0, 1440)), str(r.choice(["cpu", "restarts", "replication_lag"]))))
        for inc in self.incidents:
            for _ in range(int(r.integers(1, 4))):
                out.append((inc.start + int(r.integers(0, max(1, inc.end - inc.start))), "restarts"))
        return sorted(out)

    def page_worthy(self, slo: dict, page_share: tuple[float, float]) -> list[tuple[Incident, bool]]:
        """Truth for scoring: an incident deserves a page if its own bad requests spent `page_share[0]` of an SLO's
        monthly budget within any hour, or `page_share[1]` within any six hours (the same pace the alert windows
        use), judging errors against the availability budget and slow requests against the latency budget."""
        month = float(self.rate.mean()) * 43200
        out = []
        for inc in self.incidents:
            ok = False
            for series, objective in ((self.true_err, slo["availability"]), (self.true_slow, slo["latency"])):
                budget = month * (1 - objective)
                excess = np.zeros(self.minutes)
                excess[inc.start:inc.end] = self.rate[inc.start:inc.end] * (inc.error if series is self.true_err else inc.slow) * inc.share
                c = np.concatenate([[0], np.cumsum(excess)])
                for w, share in ((60, page_share[0]), (360, page_share[1])):
                    lo, hi = max(0, inc.start - w), min(self.minutes, inc.end + w)
                    best = max((c[min(i + w, self.minutes)] - c[i]) for i in range(lo, hi))
                    ok = ok or best >= share * budget
            out.append((inc, ok))
        return out
