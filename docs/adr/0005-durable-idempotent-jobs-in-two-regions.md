# 0005: Vesting runs as Temporal workflows with idempotency keys, workers in two regions

**Status:** accepted

**Context.** Cron jobs that die halfway are rerun by hand, and a rerun that writes again vests shares twice: a
wrong cap table, which customers and their lawyers read.

**Decision.**
- Each monthly run is a Temporal workflow with a deterministic id (`vest-<company>-<date>`), so it is started
  once; batches are activities, retried with backoff.
- Every tranche has an idempotency key (grant and date) behind a unique index; a retried batch inserts what is
  missing and counts duplicate-key errors as already written (`apps/equity-worker/src/activities.ts`).
- Workers poll in Zurich and Frankfurt; MongoDB Atlas spans both with a tiebreaker.

**Result (development orgs).** 0 duplicate records instead of 8,350; no late runs; the second region costs about
€910 a month and cuts API downtime in region outages from 97 to 4 minutes a month. Durable execution without
idempotency keys still writes 2,156 duplicates: the retry is what makes the key necessary.

**Checked for real.** The worker's tests run a workflow on a Temporal dev server against MongoDB, kill the
activity after its write landed, and count the records.
