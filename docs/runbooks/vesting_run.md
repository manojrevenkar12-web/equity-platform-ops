# Runbook: a vesting run failed or is late

Vesting runs are Temporal workflows `vest-<company>-<run date>`. A failed activity is retried ten times with
backoff; a run that still fails stays open in Temporal, it is not lost.

1. Find it: Temporal UI, workflow id `vest-<company>-<YYYY-MM-DD>`. The last failure is on the activity.
2. Fix the cause (data error in a grant, Atlas, a release), then **reset** the workflow to the failed activity
   or start it again with the same id from the API (`startVestingRun`). Both are safe: every tranche write has
   an idempotency key and a unique index, so batches that landed write nothing the second time.
3. Never insert vesting events by hand. If a correction is needed, it is a migration with its own key.
4. Check: `db.vesting_events.countDocuments({companyId, runDate})` equals the run's `due`; `vesting_runs` has the
   run record.
