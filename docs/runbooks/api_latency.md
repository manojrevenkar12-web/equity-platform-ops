# Runbook: API latency budget burn

**Pages when** requests slower than one second (`trpc_requests_slow_total`) burn 2% of the 99% latency SLO's
budget in an hour, or 5% in six hours.

## First five minutes

1. Grafana "SLO: api_latency": which procedure? `sum by (path) (rate(trpc_requests_slow_total[5m]))`.
2. Is it the database? Atlas performance advisor and the slow query log for the last hour; a missing index after a
   new query shape is the usual cause.
3. Is it CPU? `kubectl -n equity top pods`; the HPA's target is 65% CPU and its ceiling 12 pods. At the ceiling,
   raise `maxReplicas` in the overlay for the incident and record it.

## By cause

| What you see | Do |
|---|---|
| One slow query | Add the index through a migration (reviewed, not by hand in Atlas); short term, kill the long operations. |
| Slow everywhere after a release | Roll back. |
| Slow calls to Temporal | Temporal Cloud status page; `runStatus` waits on Temporal's describe, so it is slow while Temporal is. |
| Replication lag tickets at the same time | Reads are on the primary, so lag does not slow the API; it means a secondary is struggling, check Atlas. |
