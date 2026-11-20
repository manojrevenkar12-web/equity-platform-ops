"""The held-out gate, used by the CLI, the README and the dashboard."""
from __future__ import annotations

from epo.config import load


def gate(summary: dict) -> list[str]:
    g = load("gate")["platform"]
    d = summary["designs"]
    p, a = d["platform"], d["as_found"]
    fails = []
    if p["feedback_p90"] > g["max_feedback_p90_share"] * a["feedback_p90"]:
        fails.append(f"PR feedback p90 {p['feedback_p90']:.1f} min against {a['feedback_p90']:.1f}")
    if p["flaky_red_per_week"] > g["max_flaky_red_share"] * a["flaky_red_per_week"]:
        fails.append(f"{p['flaky_red_per_week']:.1f} flaky red builds a week against {a['flaky_red_per_week']:.1f}")
    if p["main_broken_hours_per_week"] > g["max_main_broken_hours_per_week"]:
        fails.append(f"main broken {p['main_broken_hours_per_week']:.1f} hours a week")
    if p["pages_per_week"] > g["max_pages_share"] * a["pages_per_week"]:
        fails.append(f"{p['pages_per_week']:.1f} pages a week against {a['pages_per_week']:.1f}")
    if p["detected_share"] < g["min_detected_share"]:
        fails.append(f"paged for {p['detected_share']:.0%} of page-worthy incidents")
    if p["harmful_applied"] > g["max_harmful_applied_share"] * a["harmful_applied"]:
        fails.append(f"{p['harmful_applied']} harmful changes applied against {a['harmful_applied']}")
    if p["duplicate_grants"] > g["max_duplicate_grants"]:
        fails.append(f"{p['duplicate_grants']} duplicate grant records")
    return fails
