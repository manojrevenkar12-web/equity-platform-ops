# 0003: Page on error-budget burn over two windows; symptoms are tickets

**Status:** accepted

**Decision.** Two SLOs on the API (99.9% availability, 99% of requests under a second). Page when 2% of the
30-day budget burns in an hour or 5% in six hours, each confirmed by a short window (5 and 30 minutes), using a
budget-per-minute recording rule over the last day. Group pages per service for 30 minutes. CPU, pod restarts
and replication lag open tickets. Rules, routes and the Grafana dashboard are generated from `config/slo.yaml`;
promtool tests that a 90-minute outage pages and a 2-minute blip does not.

**Result (development orgs).** 3 pages a week instead of 56, still paging for 98% of page-worthy incidents.

**Cost.** Pages arrive later: about 17 minutes after the start of an incident instead of 4. For a 99.9% SLO
that is a few percent of the monthly budget, which the six-hour window was sized to accept.
