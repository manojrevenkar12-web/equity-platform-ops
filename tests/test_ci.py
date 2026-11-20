import numpy as np

from epo.ci.selection import FlakeDetector, Selector, fixed_shards, lpt_shards, reverse_closure
from epo.world.ci import CIWorld


def test_selection_covers_every_dependent_package():
    deps = [[], [0], [1], [], [3]]
    rd = reverse_closure(deps)
    assert rd[0] == {0, 1, 2} and rd[3] == {3, 4}
    s = Selector(deps, np.array([0, 1, 2, 3, 4, 2]))
    assert sorted(s.select((0,)).tolist()) == [0, 1, 2, 5]


def test_selection_runs_what_the_build_graph_says_a_defect_can_break(cfg):
    w = CIWorld(cfg, 3101)
    s = Selector(w.deps, w.test_package)
    near = [pr for pr in w.prs(0) if pr.defect]
    caught = [bool(set(pr.broken) & set(s.select(pr.packages).tolist())) for pr in near]
    assert np.mean(caught) > 0.8          # far breaks are what the hourly full run on main is for


def test_lpt_balances_better_than_fixed_shards():
    r = np.random.default_rng(1)
    secs = np.exp(r.normal(0.5, 1.0, 2000))
    lpt = lpt_shards(secs, 300, 8, min_shards=8)
    per_pkg = np.bincount(r.integers(0, 40, 2000), weights=secs, minlength=40)
    fixed = fixed_shards(per_pkg.tolist(), 8)
    assert max(lpt) < max(fixed) and abs(sum(lpt) - secs.sum()) < 1e-6


def test_sprt_quarantines_a_flaky_test_and_not_a_healthy_one():
    d = FlakeDetector()
    for i in range(400):
        d.observe(1, flipped=(i % 20 == 0), week=0)       # flips 5% of runs
        d.observe(2, flipped=False, week=0)
    assert 1 in d.quarantined and 2 not in d.quarantined
    assert not d.blocking(1) and d.blocking(2)


def test_the_same_run_always_has_the_same_outcome(cfg):
    w = CIWorld(cfg, 3101)
    pr = w.prs(1)[3]
    flaky = np.flatnonzero(w.flake > 0)[:20]
    assert [w.result(pr, int(t), 0) for t in flaky] == [CIWorld(cfg, 3101).result(pr, int(t), 0) for t in flaky]
