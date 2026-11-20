import numpy as np

from epo.slo.alerts import BudgetBurn, Grouper, ThresholdAlerts, edges, pagerduty_event
from epo.world.oncall import OncallWorld


def _traffic(minutes=4 * 1440, rate=600.0):
    total = np.full(minutes, rate)
    return total, np.full(minutes, rate * 0.0005)


def test_an_hour_long_outage_pages_and_a_short_blip_does_not():
    total, bad = _traffic()
    burn = BudgetBurn(0.999)
    blip = bad.copy()
    blip[3000:3002] += total[3000:3002] * 0.05
    assert not burn.fire(blip, total).any()
    out = bad.copy()
    out[3000:3060] += total[3000:3060] * 0.05
    f = burn.fire(out, total)
    assert f.any() and 3000 <= edges(f)[0] < 3030


def test_thresholds_fire_on_the_blip_the_budget_ignores():
    total, bad = _traffic()
    bad[3000:3004] += total[3000:3004] * 0.06
    assert ThresholdAlerts(0.01).fire(bad, total).any()


def test_grouping_folds_an_alert_storm_into_one_page():
    g = Grouper(30)
    for m in (100, 105, 110, 139, 200):
        g.alert(m)
    assert g.pages == [100, 200] and g.alerts == 5


def test_pagerduty_events_deduplicate_per_incident():
    e = pagerduty_event("api", "api_availability", 10, 14.4, "inc-1")
    assert e["dedup_key"] == "inc-1" and e["event_action"] == "trigger"


def test_page_worthy_judges_slow_requests_against_the_latency_budget(cfg, platform):
    w = OncallWorld(cfg, 3101)
    truth = w.page_worthy(platform["slo"], tuple(platform["slo"]["page_share"]))
    assert len(truth) == len(w.incidents) and any(ok for _, ok in truth)
    slow_only = [ok for inc, ok in truth if inc.kind == "slow_dependency"]
    assert not all(slow_only) or not slow_only
