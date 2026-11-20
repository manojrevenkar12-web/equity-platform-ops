"""The designs compared on the same simulated org. Each sets one choice per area; ablations change exactly one."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Design:
    name: str
    label: str
    # CI
    selection: bool = True            # graph-based test selection (else every test on every PR)
    lpt_shards: bool = True           # balanced shards sized to a target (else 8 fixed shards by package)
    quarantine: bool = True           # flaky tests stop blocking once the SPRT flags them
    main_full_run: str = "hourly"     # hourly | nightly: when every test runs on main, to catch what selection missed
    # paging
    paging: str = "burn"              # burn | threshold
    grouping: bool = True
    symptoms_page: bool = False       # CPU, restarts, lag page someone (else tickets)
    # changes
    changes: str = "guard"            # review_all | ai_on_green | guard
    ai_tier: bool = True              # stricter thresholds for AI-written changes
    # equity jobs
    jobs: str = "durable"             # cron | durable
    idempotent: bool = True
    regions: int = 2


AS_FOUND = Design("as_found", "As found: every test on 8 runners, threshold alerts, every change reviewed, cron jobs",
                  selection=False, lpt_shards=False, quarantine=False, main_full_run="nightly", paging="threshold", grouping=False,
                  symptoms_page=True, changes="review_all", ai_tier=False, jobs="cron", idempotent=False, regions=1)
PLATFORM = Design("platform", "Platform: selection and quarantine, budget burn with grouping, plan guard, durable "
                              "idempotent jobs in two regions")

DESIGNS = [
    AS_FOUND,
    replace(AS_FOUND, name="ai_on_green", label="As found, but AI-written changes merge on green CI", changes="ai_on_green"),
    replace(PLATFORM, name="platform_all_tests", label="Platform, every test on every PR", selection=False),
    replace(PLATFORM, name="platform_fixed_shards", label="Platform, 8 fixed shards", lpt_shards=False),
    replace(PLATFORM, name="platform_nightly_only", label="Platform, full run on main only at night", main_full_run="nightly"),
    replace(PLATFORM, name="platform_no_quarantine", label="Platform, no flaky-test quarantine", quarantine=False),
    replace(PLATFORM, name="platform_threshold_paging", label="Platform, threshold alerts on the SLO metrics", paging="threshold"),
    replace(PLATFORM, name="platform_no_grouping", label="Platform, no grouping of pages", grouping=False),
    replace(PLATFORM, name="platform_symptoms_page", label="Platform, symptoms page as before", symptoms_page=True),
    replace(PLATFORM, name="platform_rules_only", label="Platform, guard without the AI tier", ai_tier=False),
    replace(PLATFORM, name="platform_no_idempotency", label="Platform, durable jobs without idempotency keys", idempotent=False),
    replace(PLATFORM, name="platform_single_region", label="Platform, workers in one region", regions=1),
    PLATFORM,
]
BY_NAME = {d.name: d for d in DESIGNS}
ORDER = [d.name for d in DESIGNS]
