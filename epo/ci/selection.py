"""Which tests a pull request runs, how they are split across runners, and which flaky tests stop blocking.

- **Selection.** The tests of every package the PR touches and of every package that depends on one of them,
  transitively, from the build graph. A nightly full run catches what the graph misses.
- **Sharding.** Longest-processing-time first onto as many runners as it takes to reach a target duration, from
  each test's recorded duration.
- **Quarantine.** A test that fails and then passes on retry for the same commit has "flipped". A sequential
  probability ratio test on its flip rate (Wald) quarantines it once the evidence says it flips more than a
  healthy test would. Quarantined tests still run and report, but do not block the merge.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np


def reverse_closure(deps: list[list[int]]) -> list[set[int]]:
    direct: list[set[int]] = [set() for _ in deps]
    for i, ds in enumerate(deps):
        for d in ds:
            direct[d].add(i)
    out = []
    for p in range(len(deps)):
        seen, stack = {p}, [p]
        while stack:
            for q in direct[stack.pop()]:
                if q not in seen:
                    seen.add(q)
                    stack.append(q)
        out.append(seen)
    return out


@dataclass
class Selector:
    deps: list[list[int]]
    test_package: np.ndarray

    def __post_init__(self) -> None:
        self.rdeps = reverse_closure(self.deps)
        self.by_package: dict[int, np.ndarray] = {int(p): np.flatnonzero(self.test_package == p)
                                                  for p in np.unique(self.test_package)}

    def select(self, packages: tuple[int, ...]) -> np.ndarray:
        affected = set().union(*(self.rdeps[p] for p in packages)) if packages else set()
        parts = [self.by_package[p] for p in sorted(affected) if p in self.by_package]
        return np.concatenate(parts) if parts else np.array([], dtype=int)


def lpt_shards(seconds: np.ndarray, target_seconds: float, max_shards: int, min_shards: int = 1) -> list[float]:
    """Wall-clock seconds of each shard: longest test first onto the least loaded shard."""
    total = float(seconds.sum())
    k = int(min(max_shards, max(min_shards, math.ceil(total / target_seconds)))) if total else 1
    heap = [(0.0, i) for i in range(k)]
    for s in np.sort(seconds)[::-1]:
        load, i = heapq.heappop(heap)
        heapq.heappush(heap, (load + float(s), i))
    return [h[0] for h in heap]


def fixed_shards(seconds_by_package: list[float], shards: int) -> list[float]:
    """The as-found split: whole packages dealt to a fixed number of runners in order."""
    loads = [0.0] * shards
    for i, s in enumerate(seconds_by_package):
        loads[i % shards] += s
    return loads


@dataclass
class FlakeDetector:
    """Wald's SPRT per test: H0 flip rate p0 (healthy) against H1 p1 (flaky)."""

    p0: float = 0.001
    p1: float = 0.03
    alpha: float = 0.01                 # wrongly quarantining a healthy test
    beta: float = 0.05
    llr: dict[int, float] = field(default_factory=dict)
    quarantined: dict[int, int] = field(default_factory=dict)      # test -> week quarantined

    @property
    def upper(self) -> float:
        return math.log((1 - self.beta) / self.alpha)

    def observe(self, test: int, flipped: bool, week: int) -> None:
        if test in self.quarantined:
            return
        step = math.log(self.p1 / self.p0) if flipped else math.log((1 - self.p1) / (1 - self.p0))
        v = max(0.0, self.llr.get(test, 0.0) + step)       # floored: old good runs do not hide a new flake forever
        self.llr[test] = v
        if v >= self.upper:
            self.quarantined[test] = week

    def blocking(self, test: int) -> bool:
        return test not in self.quarantined
