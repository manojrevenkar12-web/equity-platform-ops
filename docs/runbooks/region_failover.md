# Runbook: losing a region

Zurich (europe-west6) is primary for the API; Frankfurt (europe-west3) runs workers all the time and the API warm
at two pods.

## Workers

Nothing to do. Both regions poll the same Temporal task queue; activities that were running in the lost region
time out and are retried in the other one, and the idempotency keys make the retry write nothing twice. Check
the Temporal UI for runs with retries in the last hour.

## API

1. Confirm the region is down, not the load balancer: GCP status page, `gcloud container clusters list`.
2. Shift traffic: set the Zurich backend's weight to 0 in the global load balancer
   (`gcloud compute backend-services update`; the load balancer is not in this repository's Terraform yet, so
   record the change in the incident).
3. Scale Frankfurt: the HPA does this on CPU, but set `minReplicas: 3` in the overlay so it does not shrink.

## MongoDB

The Atlas cluster has two electable nodes in each region and a tiebreaker in europe-west1; losing a region keeps
a majority and elects a primary in Frankfurt within seconds. Nothing to do unless Atlas reports otherwise.

## Coming back

Move the weight back in steps (10%, 50%, 100%) once the region has been healthy for an hour, and put
`minReplicas` back.
