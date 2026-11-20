# 0002: Run the tests a change can reach, quarantine flaky tests by a sequential test, run everything hourly on main

**Status:** accepted

**Decision.**
- On a PR, run the tests of the changed packages and of every package that depends on them (reverse
  dependency closure), in shards balanced by recorded duration (longest first).
- A test that fails and then passes on retry is evidence of flakiness. A Wald sequential probability ratio
  test per test (failure rate 0.1% against 3%, α 1%, β 5%) decides when it is flaky; it is quarantined: it still
  runs, but its failures do not fail the build, and it goes to its owner's queue.
- Main runs the full suite every hour, because selection by dependency misses breaks through runtime coupling.

**Ablations.** Every test on every PR: feedback p90 11 minutes instead of 8 and 5 more hours a week. Fixed
shards: 29 minutes. Full run nightly only: main stays broken 40 hours a week. No quarantine: 18 flaky reds a week.

**Trade-off accepted.** Main is broken about 5 hours a week on the platform against 0 when every PR runs
everything; the hourly run bounds it.
