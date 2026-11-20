"""The monorepo and its pull requests, with the truth about tests.

Visible to the platform: packages and their dependencies (the build graph), which package each test belongs to,
how long tests took in past runs, and the results of every run it makes. Hidden: which tests are flaky and how
often they fail, and which tests a PR's defect breaks.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from epo.keyed import rng, uniform

DAY_MIN = 1440


@dataclass(frozen=True)
class PR:
    id: str
    week: int
    day: int                     # 0..4, weekdays
    minute: int                  # minute of the day the push lands
    packages: tuple[int, ...]
    defect: bool
    broken: tuple[int, ...]      # tests the defect makes fail (truth)


class CIWorld:
    def __init__(self, cfg: dict, seed: int):
        self.cfg, self.seed = cfg["ci"], seed
        c = self.cfg
        r = rng(seed, "ci-repo")
        P, T = c["packages"], c["tests"]
        self.deps: list[list[int]] = [sorted(set(r.choice(i, size=min(i, int(r.integers(0, 4))), replace=False).tolist()))
                                      if i else [] for i in range(P)]
        weights = r.pareto(1.5, P) + 1
        self.test_package = r.choice(P, T, p=weights / weights.sum())
        self.seconds = np.exp(np.log(c["test_seconds_median"]) + r.normal(0, c["test_seconds_sigma"], T))
        self.flake = np.zeros(T)
        self.onset = np.full(T, 10_000)
        first = r.choice(T, int(c["flaky_share"] * T), replace=False)
        self.flake[first] = r.uniform(*c["flaky_rate"], len(first))
        self.onset[first] = 0
        weeks = cfg["weeks"]
        for w in range(1, weeks):
            new = r.choice(np.flatnonzero(self.flake == 0), c["new_flaky_per_week"], replace=False)
            self.flake[new] = r.uniform(*c["flaky_rate"], len(new))
            self.onset[new] = w
        self._rdeps = self._reverse()

    def _reverse(self) -> list[set[int]]:
        P = len(self.deps)
        direct: list[set[int]] = [set() for _ in range(P)]
        for i, ds in enumerate(self.deps):
            for d in ds:
                direct[d].add(i)
        out = []
        for p in range(P):
            seen, stack = {p}, [p]
            while stack:
                for q in direct[stack.pop()]:
                    if q not in seen:
                        seen.add(q)
                        stack.append(q)
            out.append(seen)
        return out

    def prs(self, week: int) -> list[PR]:
        c = self.cfg
        out = []
        for day in range(5):
            r = rng(self.seed, "prs", week, day)
            n = int(r.poisson(c["prs_per_weekday"]))
            minutes = np.sort(r.integers(8 * 60, 19 * 60, n))
            for i in range(n):
                k = int(r.integers(c["packages_per_pr"][0], c["packages_per_pr"][1] + 1))
                pk = tuple(sorted(set(r.choice(len(self.deps), k).tolist())))
                defect = bool(r.random() < c["defect_rate"])
                broken: tuple[int, ...] = ()
                if defect:
                    if r.random() < c["far_break_share"]:
                        pool = np.flatnonzero(self.test_package == int(r.integers(0, len(self.deps))))
                    else:
                        affected = set().union(*(self._rdeps[p] for p in pk))
                        pool = np.flatnonzero(np.isin(self.test_package, list(affected)))
                    if len(pool):
                        broken = tuple(sorted(r.choice(pool, min(len(pool), int(r.integers(1, 6))), replace=False).tolist()))
                    else:
                        defect = False
                out.append(PR(f"{week}-{day}-{i}", week, day, int(minutes[i]), pk, defect, broken))
        return out

    def result(self, pr: PR, test: int, attempt: int) -> bool:
        """True if the test passes on this run (keyed: the same run always has the same outcome)."""
        if test in pr.broken:
            return False
        if self.flake[test] > 0 and pr.week >= self.onset[test]:
            return uniform(self.seed, "run", pr.id, int(test), attempt) >= self.flake[test]
        return True

    def nightly_result(self, week: int, day: int, test: int, broken: set[int]) -> bool:
        if test in broken:
            return False
        if self.flake[test] > 0 and week >= self.onset[test]:
            return uniform(self.seed, "nightly", week, day, int(test)) >= self.flake[test]
        return True
