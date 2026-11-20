"""Paging: error-budget burn alerts, grouped into incidents; symptom alerts become tickets.

- **Budget burn.** For each SLO, page when the bad requests in a long window and in a short window both exceed
  `burn x window x budget per minute`, with the SRE workbook's pairs (1 h and 5 min at 14.4; 6 h and 30 min at 6).
  The budget per minute comes from the last day's traffic, so a quiet night and a busy afternoon are judged in the
  same currency: budget spent.
- **Grouping.** A page within `group_minutes` of an open incident joins it instead of paging again.
- **Symptoms** (CPU, restarts, replication lag) open tickets, not pages.

`ThresholdAlerts` is the as-found setup: error and slow ratios over 5 minutes, and symptoms, each paging.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

WINDOWS = ((60, 5, 14.4), (360, 30, 6.0))


def _rolling(x: np.ndarray, w: int) -> np.ndarray:
    c = np.concatenate([[0.0], np.cumsum(x, dtype=float)])
    out = np.empty(len(x))
    idx = np.arange(len(x))
    out[:] = c[idx + 1] - c[np.maximum(idx + 1 - w, 0)]
    return out


@dataclass
class BudgetBurn:
    objective: float
    windows: tuple = WINDOWS
    lookback: int = 1440

    def fire(self, bad: np.ndarray, total: np.ndarray) -> np.ndarray:
        """Per minute: does any window pair fire?"""
        traffic = _rolling(total, self.lookback) / np.minimum(np.arange(1, len(total) + 1), self.lookback)
        per_minute = traffic * (1 - self.objective)
        out = np.zeros(len(bad), dtype=bool)
        for long, short, burn in self.windows:
            out |= (_rolling(bad, long) >= burn * long * per_minute) & (_rolling(bad, short) >= burn * short * per_minute)
        out[:1440] = False                                     # one day of history before paging
        return out


@dataclass
class ThresholdAlerts:
    ratio: float
    window: int = 5
    for_minutes: int = 5

    def fire(self, bad: np.ndarray, total: np.ndarray) -> np.ndarray:
        r = _rolling(bad, self.window) / np.maximum(_rolling(total, self.window), 1)
        hot = r > self.ratio
        run = _rolling(hot.astype(float), self.for_minutes) >= self.for_minutes
        return run


def edges(firing: np.ndarray) -> list[int]:
    """Minutes where an alert starts firing (a page each time it re-opens)."""
    f = firing.astype(int)
    return (np.flatnonzero(np.diff(np.concatenate([[0], f])) == 1)).tolist()


@dataclass
class Grouper:
    """Folds pages into incidents: one page per incident, and an incident stays open `group_minutes` after its
    last alert."""

    group_minutes: int = 30
    open_until: int = -1
    pages: list[int] = field(default_factory=list)
    alerts: int = 0

    def alert(self, minute: int) -> bool:
        self.alerts += 1
        if minute <= self.open_until:
            self.open_until = max(self.open_until, minute + self.group_minutes)
            return False
        self.pages.append(minute)
        self.open_until = minute + self.group_minutes
        return True


def pagerduty_event(service: str, slo: str, minute: int, burn: float, dedup: str) -> dict:
    """An Events API v2 trigger, deduplicated per incident so PagerDuty groups repeats."""
    return {"routing_key": "${PAGERDUTY_ROUTING_KEY}", "event_action": "trigger", "dedup_key": dedup,
            "payload": {"summary": f"{service}: {slo} error budget burning at {burn:g}x", "source": service,
                        "severity": "critical", "custom_details": {"slo": slo, "minute": minute,
                                                                   "runbook": f"docs/runbooks/{slo}.md"}}}
