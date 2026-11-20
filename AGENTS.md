# AGENTS.md

How to work in this repository, for people and for coding agents.

## Fast feedback

- `python -m pytest`: the simulation, CI selection and flake detection, burn alerts, the plan guard, the service
  and the invariants, in seconds.
- `python -m epo.eval.cli quick`: two designs, one org, three weeks.
- `ruff check .`; in `web/` run `pnpm build`; in `apps/equity-worker` run `pnpm test` (needs MongoDB on
  `MONGO_URL` and a Temporal CLI on `TEMPORAL_CLI`, see that folder's notes in the README).
- `promtool test rules ops/prometheus/rules_test.yml`.
- `kustomize build deploy/k8s/overlays/zurich | kubeconform -strict -summary`.

## Invariants

1. **The truth stays in the world.**
   - `epo/world` holds the org: which tests are flaky, which PRs are defective, which incidents deserve a page,
     which changes are harmful, when workers crash.
   - The platform's components (`epo/ci`, `epo/slo`, `epo/guard`, `epo/service`) never import `epo.world` or
     `epo.sim`. They get what production would give them: test results, metrics, plans and commit messages.
     `tests/test_invariants.py` checks it.
2. **The world does not read the platform's settings.** It reads `config/world.yaml` (and the held-out overlay)
   only.
3. **Same luck for every design.** Every draw is keyed by what it is about (`epo/keyed.py`), so every design meets
   the same pull requests, incidents, changes and crashes.
4. **Settings in config.** Shard targets, SPRT parameters, SLOs, burn windows, guard rules, prices and gates live
   in `config/*.yaml`.
5. **Generated reports.**
   - `reports/`, the charts, the README results block, `ops/prometheus/rules.yml`, `ops/alertmanager/routes.yml`
     and `ops/grafana/slo-dashboard.json` are written by `epo.eval.cli`. Never edit them by hand.
   - CI re-runs the development evaluation and fails if the committed reports differ.
6. **Writes that can be retried carry an idempotency key.** In the worker, every write to MongoDB has a key behind
   a unique index; a retry inserts only what is missing.

## The held-out rule

- The held-out orgs (`config/heldout.yaml`) are run once with `python -m epo.eval.cli heldout`. The run writes
  `config/heldout.lock`, and the command refuses to run again.
- Tune on the development orgs only.
- A change made after the run is written up in `docs/heldout.md`; the held-out numbers are not re-run.
