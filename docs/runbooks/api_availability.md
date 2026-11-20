# Runbook: API availability budget burn

**Pages when** the API's 5xx and INTERNAL_SERVER_ERROR responses burn 2% of the 30-day error budget in an hour
(`ApiAvailabilityBudgetBurn60m`), or 5% in six hours (`ApiAvailabilityBudgetBurn360m`). The SLO is 99.9% of tRPC
requests (`config/slo.yaml`). Each alert also needs its short window (5 or 30 minutes) burning, so it clears
soon after the cause is gone.

## First five minutes

1. Open the Grafana dashboard "SLO: api_availability" (`ops/grafana/slo-dashboard.json`): which procedure and
   which region? `sum by (path, code) (rate(trpc_requests_total{code!="OK"}[5m]))`.
2. Was there a release in the last hour? `kubectl -n equity rollout history deploy/api`. If yes and the errors
   started with it: `kubectl -n equity rollout undo deploy/api` in both regions, then investigate.
3. Logs: `kubectl -n equity logs deploy/api --since=30m | grep -i error | sort | uniq -c | sort -rn | head`.

## By cause

| What you see | Do |
|---|---|
| Errors from one region only | Check the region's nodes and NAT (`kubectl get nodes`, Cloud NAT logs). If the region is down, follow [region_failover.md](region_failover.md). |
| `MongoServerSelectionError`, `NotWritablePrimary` | An Atlas election. It should settle within about 10 s; check the Atlas cluster's events. Longer: open an Atlas support case and check the egress IPs on the access list. |
| Temporal `Unavailable` on `startVestingRun` | Temporal Cloud status page; workers retry, but the API's start fails. Nothing to repair once it recovers: starting is idempotent by workflow id. |
| Errors on one procedure after a schema change | Roll back; a migration that a running pod cannot read is a release bug. |

## After

- Write the incident up within two working days; the budget left this month decides whether feature releases
  wait (see ADR 0003).
- If the alert fired and nobody needed to act, that is a false page: say so in the review, and the burn
  thresholds get looked at, not muted.
