# SKILLS.md

Repeatable tasks, each with the command and how to know it worked.

## Evaluate after a change

`python -m epo.eval.cli evaluate`, then `python -m epo.eval.cli gate --dev`. Commit `reports/` and the README
together. CI fails if they do not match a fresh run.

## Add an ablation

1. Add a `Design` in `epo/sim/designs.py` that switches one thing off, and put it in `ORDER`.
2. Add its short name in `web/src/shared/format.ts` and, if it belongs to an area, to that area's list in
   `web/src/features/areas/AreaView.tsx`.
3. Evaluate; the README table and the dashboard pick it up.

## Change an SLO or an alert window

Edit `config/slo.yaml` or the burn windows in `config/platform.yaml`, run `python -m epo.eval.cli rules`, then
`promtool check rules ops/prometheus/rules.yml && promtool test rules ops/prometheus/rules_test.yml`. If the
outage or blip test changes outcome, that is the point of the test: decide, do not edit the test to pass.

## Add a guard rule

1. Write the rule in `epo/guard/plan.py` with its level (block, review, info) and a test in `tests/test_guard.py`
   with a plan that triggers it and a lookalike that must not.
2. If the world should contain the case, add the harmful kind to `epo/world/changes.py` (the world decides it is
   harmful; the guard never sees that flag).
3. Evaluate: harmful applied should fall without false blocks rising.

## Check a Terraform plan

`terraform show -json plan.tfplan > plan.json && python -m epo.guard plan.json --commit-messages <(git log --format=%B main..)`
Exit 0 apply, 2 review, 3 block.

## Run the worker locally

MongoDB (or FerretDB) on 27017 and `temporal server start-dev`, then in `apps/equity-worker`: `pnpm build`,
`pnpm worker` and `pnpm api`. `curl localhost:3000/metrics` shows the SLO counters.

## Refresh the dashboard screenshots

Start `uvicorn epo.service.api:app --port 8098`, open each view and save to `docs/screenshots/`.
