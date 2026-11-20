# Runbook: an infrastructure change

1. Change Terraform in `infra/terraform`, open a pull request. AI-written commits carry the assistant's
   `Co-Authored-By` trailer; that is how the guard tells them apart.
2. The `infra-guard` workflow runs a speculative plan in Terraform Cloud and passes its JSON through
   `python -m epo.guard`:
   - **block** (public principals, owner to people, the internet on database/SSH/Temporal ports, deleting or
     replacing a stateful resource, cluster-admin for a default account): the check fails. Change the plan.
     If the delete is truly wanted (a cluster migration), it is a planned change with its own ticket and two
     approvers from the platform team, and the guard's finding is quoted in it.
   - **review**: a person from the platform team approves (CODEOWNERS on `infra/`). Broad roles to people,
     protection switched off, IAM changes written with an AI assistant, or a high risk score land here.
   - **apply**: merges on green CI and Terraform Cloud applies.
3. Try a plan locally: `terraform show -json plan.tfplan > plan.json && python -m epo.guard plan.json`.
