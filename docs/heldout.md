# The held-out run

Run once on 20 November 2026 (`config/heldout.lock`: seeds 3201–3203, config hash `68717800974d3468`), after
the development evaluation passed its gate and nothing in `config/` or the code was changed afterwards.

**Gate: passed.** Against the org as found, on the held-out orgs:

| | As found | Platform |
|---|---:|---:|
| PR feedback p90 (minutes) | 51.0 | 8.1 |
| Flaky red builds a week | 71.8 | 0.9 |
| Hours main is broken a week | 0 | 3.9 |
| Pages a week | 51.5 | 1.6 |
| Page-worthy incidents paged for | 100% of 35 | 97% of 35 |
| Harmful infrastructure changes applied | 25 of 71 | 5 of 71 |
| Duplicate grant records | 7,550 | 0 |
| Engineering hours lost a week | 191.4 | 21.7 |

## What was worse than on the development orgs

- **Harmful changes applied: 5 of 71** against 1 of 62 on the development orgs. These are the subtle kinds the
  rules do not describe (the world's `subtle_harmful_share`); the AI tier caught two more than the rules alone
  (7 of 71). The guard is a floor, not a review replacement for access changes.
- **One page-worthy incident in 35 was not paged** (97%): a slow burn that stayed under the six-hour threshold
  and opened a ticket instead.
- Pages arrive later than threshold alerts would send them (about 21 minutes from the start of an incident against
  4), as on the development orgs.

## Changes after the run

None so far. Anything changed from here on is listed here, and the held-out numbers are not re-run.
