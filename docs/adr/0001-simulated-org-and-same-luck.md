# 0001: Measure the platform on a simulated engineering org, with the same luck for every design

**Status:** accepted

**Context.** The questions (which tests to run on a PR, what pages, which infrastructure changes a person must
see, cron or durable jobs) are all trade-offs between engineering hours and risk. Arguing them from opinion is
how platform teams end up with every test on every PR and every alert paging.

**Decision.** A simulated org (`epo/world`) with hidden truth: which tests are flaky, which PRs carry a defect and
which tests it breaks, which incidents burn enough budget to deserve a page, which infrastructure changes are
harmful, when workers crash. Every design runs on the same draws (`epo/keyed.py`), so differences are the
design's. Development seeds for tuning, held-out seeds run once. The headline is engineering hours lost per
week, priced in `config/value.yaml`; harmful changes and duplicate records are reported beside it, not priced,
because a breach or a wrong cap table is not a number of hours.

**Consequences.** Every number is about the simulated org, and the README says so. The world's rates are
assumptions; the ablations show which parts of the platform carry the result, which is the transferable part.
