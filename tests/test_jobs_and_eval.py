from epo.eval.run import run_all, summarize
from epo.sim.designs import BY_NAME
from epo.sim.engine import run_jobs
from epo.world.jobs import JobsWorld


def test_durable_idempotent_jobs_never_duplicate_and_cron_does(cfg, platform):
    w = JobsWorld(cfg, 3101, [])
    plat = run_jobs(w, BY_NAME["platform"], platform, cfg["weeks"])
    cron = run_jobs(w, BY_NAME["as_found"], platform, cfg["weeks"])
    retry = run_jobs(w, BY_NAME["platform_no_idempotency"], platform, cfg["weeks"])
    assert sum(x["duplicates"] for x in plat) == 0
    assert sum(x["duplicates"] for x in cron) > sum(x["duplicates"] for x in retry) > 0


def test_a_second_region_shortens_an_outage(cfg, platform):
    w = JobsWorld(cfg, 3101, [(2000, 2090, "region_outage")])
    one = run_jobs(w, BY_NAME["platform_single_region"], platform, cfg["weeks"])
    two = run_jobs(w, BY_NAME["platform"], platform, cfg["weeks"])
    assert sum(x["down_minutes"] for x in one) == 90 and sum(x["down_minutes"] for x in two) < 5


def test_every_design_meets_the_same_org_and_the_summary_is_paired():
    runs = run_all(False, names=["as_found", "platform"], weeks=2, seeds=[3101], workers=1)
    s = summarize(runs, n_boot=50)
    a, p = s["designs"]["as_found"], s["designs"]["platform"]
    assert a["job_runs"] == p["job_runs"] and a["harmful"] == p["harmful"] and a["page_worthy"] == p["page_worthy"]
    assert p["engineer_hours_per_week"] < a["engineer_hours_per_week"]
